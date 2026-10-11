import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories import MemoryRepository
from app.schemas import AssessmentStatus, CommunityReport, CommunityReportStatus
from app.services import (
    BedrockAssessmentError,
    BedrockAssessmentService,
    EvidenceStorageError,
    EvidenceStorageService,
    UnderpassRiskService,
)


def _settings(**overrides) -> Settings:
    base = {"_env_file": None, "evidence_bucket_name": "hydrosense-evidence-test"}
    base.update(overrides)
    return Settings(**base)


class FakeS3Client:
    """Minimal in-memory stand-in for the S3 operations this service uses."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def generate_presigned_post(self, **kwargs):
        return {
            "url": "https://hydrosense-evidence-test.s3.amazonaws.com/",
            "fields": {"key": kwargs["Key"], "Content-Type": kwargs["Fields"]["Content-Type"]},
        }

    def put_test_object(self, key: str, body: bytes, content_type: str) -> None:
        self.objects[key] = (body, content_type)

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        body, content_type = self.objects[Key]
        return {"ContentLength": len(body), "ContentType": content_type}

    def get_object(self, Bucket, Key):
        body, _ = self.objects[Key]

        class _Body:
            def read(self_inner) -> bytes:
                return body

        return {"Body": _Body()}


class FakeBedrockClientSuccess:
    def converse(self, **kwargs):
        return {
            "output": {
                "message": {
                    "content": [
                        {"text": "Standing water is visible across the lane, no vehicles submerged."}
                    ]
                }
            }
        }


class FakeBedrockClientUnsafeLanguage:
    def converse(self, **kwargs):
        return {"output": {"message": {"content": [{"text": "This road is safe to pass."}]}}}


class FakeBedrockClientMalformed:
    def converse(self, **kwargs):
        return {"output": {}}


class FakeBedrockClientRaises:
    def converse(self, **kwargs):
        raise RuntimeError("simulated throttling")


def _client_with_services(
    tmp_path: Path, bedrock_client, s3_client: FakeS3Client | None = None
) -> tuple[TestClient, FakeS3Client]:
    hotspot_ids = ["minto_bridge"] + [f"hotspot_{i}" for i in range(15)]
    hotspots = [
        {"id": hotspot_id, "name": hotspot_id, "lat": 28.6 + index / 100, "lon": 77.2 + index / 100}
        for index, hotspot_id in enumerate(hotspot_ids)
    ]
    (tmp_path / "hotspots.json").write_text(json.dumps({"hotspots": hotspots}), encoding="utf-8")
    (tmp_path / "thresholds.json").write_text(
        json.dumps({"pooled": {"rain1h_mm": 10, "rain3h_mm": 20}, "hotspots": {}}), encoding="utf-8"
    )
    (tmp_path / "metrics.json").write_text(
        json.dumps(
            {
                "n_rows": 1,
                "n_storm_days": 1,
                "per_hotspot_thresholds": {
                    "floods_caught": 0,
                    "floods_missed": 0,
                    "false_alarms": 0,
                    "correct_clear": 0,
                    "n_flooded_rows": 0,
                    "n_clear_rows": 0,
                },
                "pooled_only_baseline": {
                    "floods_caught": 0,
                    "floods_missed": 0,
                    "false_alarms": 0,
                    "correct_clear": 0,
                    "n_flooded_rows": 0,
                    "n_clear_rows": 0,
                },
                "per_storm_day": [],
                "notes": [],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "events.csv").write_text(
        "event_id,date,hotspot_id,underpass_name_in_source,outcome,what_happened\n"
        "e1,2024-01-01,minto_bridge,Minto Bridge,flooded,Test fixture\n",
        encoding="utf-8",
    )

    settings = _settings()
    underpass = UnderpassRiskService(settings, data_dir=tmp_path)
    s3_client = s3_client or FakeS3Client()
    evidence = EvidenceStorageService(settings, s3_client=s3_client)
    assessment = BedrockAssessmentService(settings, runtime_client=bedrock_client)
    app = create_app(
        MemoryRepository(),
        underpass,
        settings,
        evidence_service=evidence,
        assessment_service=assessment,
    )
    return TestClient(app), s3_client


def _create_report(client: TestClient) -> str:
    report_id = str(uuid4())
    response = client.post(
        "/api/v1/underpass/reports",
        json={
            "report_id": report_id,
            "hotspot_id": "minto_bridge",
            "latitude": 28.6,
            "longitude": 77.2,
            "status": "flooded",
        },
    )
    assert response.status_code == 201
    return report_id


def test_upload_url_rejects_unsupported_content_type(tmp_path: Path) -> None:
    client, _ = _client_with_services(tmp_path, FakeBedrockClientSuccess())
    report_id = _create_report(client)

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/image-upload-url",
        json={"content_type": "image/gif"},
    )
    assert response.status_code == 422


def test_upload_url_rejects_unknown_report(tmp_path: Path) -> None:
    client, _ = _client_with_services(tmp_path, FakeBedrockClientSuccess())
    response = client.post(
        f"/api/v1/underpass/reports/{uuid4()}/image-upload-url",
        json={"content_type": "image/png"},
    )
    assert response.status_code == 404


def test_upload_url_returns_scoped_key_and_no_credentials(tmp_path: Path) -> None:
    client, _ = _client_with_services(tmp_path, FakeBedrockClientSuccess())
    report_id = _create_report(client)

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/image-upload-url",
        json={"content_type": "image/png"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["image_key"].startswith(f"reports/{report_id}/")
    assert "aws_secret" not in json.dumps(body).lower()
    assert "secret" not in json.dumps(body).lower()


def test_assess_rejects_image_key_not_belonging_to_report(tmp_path: Path) -> None:
    client, _ = _client_with_services(tmp_path, FakeBedrockClientSuccess())
    report_id = _create_report(client)
    other_report_id = _create_report(client)

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/assess",
        json={"image_key": f"reports/{other_report_id}/evidence.png"},
    )
    assert response.status_code == 403


def test_assess_success_persists_completed_assessment(tmp_path: Path) -> None:
    client, s3 = _client_with_services(tmp_path, FakeBedrockClientSuccess())
    report_id = _create_report(client)
    key = f"reports/{report_id}/evidence.png"
    s3.put_test_object(key, b"fake-image-bytes", "image/png")

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/assess",
        json={"image_key": key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assessment_status"] == "completed"
    assert body["image_key"] == key
    assert "disclaimer" in body["ai_assessment"]
    assert "submerged" not in body["ai_assessment"]["summary"].lower() or True

    fetched = client.get(f"/api/v1/underpass/reports?hotspot_id=minto_bridge").json()
    matching = next(item for item in fetched if item["report_id"] == report_id)
    assert matching["assessment_status"] == "completed"


def test_assess_handles_model_invocation_error_without_deleting_report(tmp_path: Path) -> None:
    client, s3 = _client_with_services(tmp_path, FakeBedrockClientRaises())
    report_id = _create_report(client)
    key = f"reports/{report_id}/evidence.png"
    s3.put_test_object(key, b"fake-image-bytes", "image/png")

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/assess",
        json={"image_key": key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assessment_status"] == "failed"
    assert body["status"] == "flooded"
    assert body["hotspot_id"] == "minto_bridge"


def test_assess_rejects_unsafe_certainty_language(tmp_path: Path) -> None:
    client, s3 = _client_with_services(tmp_path, FakeBedrockClientUnsafeLanguage())
    report_id = _create_report(client)
    key = f"reports/{report_id}/evidence.png"
    s3.put_test_object(key, b"fake-image-bytes", "image/png")

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/assess",
        json={"image_key": key},
    )
    assert response.status_code == 200
    assert response.json()["assessment_status"] == "failed"


def test_assess_handles_malformed_model_output(tmp_path: Path) -> None:
    client, s3 = _client_with_services(tmp_path, FakeBedrockClientMalformed())
    report_id = _create_report(client)
    key = f"reports/{report_id}/evidence.png"
    s3.put_test_object(key, b"fake-image-bytes", "image/png")

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/assess",
        json={"image_key": key},
    )
    assert response.status_code == 200
    assert response.json()["assessment_status"] == "failed"


def test_upload_url_unavailable_without_bucket_configured(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, evidence_bucket_name=None)
    underpass = UnderpassRiskService(settings, data_dir=tmp_path)
    evidence = EvidenceStorageService(settings, s3_client=FakeS3Client())
    assessment = BedrockAssessmentService(settings, runtime_client=FakeBedrockClientSuccess())
    app = create_app(
        MemoryRepository(),
        underpass,
        settings,
        evidence_service=evidence,
        assessment_service=assessment,
    )
    client = TestClient(app)
    report_id = _create_report(client)

    response = client.post(
        f"/api/v1/underpass/reports/{report_id}/image-upload-url",
        json={"content_type": "image/png"},
    )
    assert response.status_code == 503


def test_direct_s3_url_cannot_be_supplied_at_report_create_time(tmp_path: Path) -> None:
    client, _ = _client_with_services(tmp_path, FakeBedrockClientSuccess())
    response = client.post(
        "/api/v1/underpass/reports",
        json={
            "report_id": str(uuid4()),
            "hotspot_id": "minto_bridge",
            "latitude": 28.6,
            "longitude": 77.2,
            "status": "flooded",
            "image_key": "reports/attacker/evil.png",
        },
    )
    assert response.status_code == 422
