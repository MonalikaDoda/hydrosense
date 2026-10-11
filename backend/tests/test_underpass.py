import csv
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories import MemoryRepository
from app.services import UnderpassRiskService
from app.services.underpass_risk import IST, assess_hotspot


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    hotspot_ids = ["minto_bridge", "zakhira"] + [f"hotspot_{i}" for i in range(14)]
    hotspots = [
        {
            "id": hotspot_id,
            "name": hotspot_id.replace("_", " ").title(),
            "lat": 28.5 + index / 100,
            "lon": 77.1 + index / 100,
        }
        for index, hotspot_id in enumerate(hotspot_ids)
    ]
    (tmp_path / "hotspots.json").write_text(
        json.dumps({"hotspots": hotspots}), encoding="utf-8"
    )
    (tmp_path / "thresholds.json").write_text(
        json.dumps(
            {
                "pooled": {"rain1h_mm": 10, "rain3h_mm": 20},
                "hotspots": {},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "metrics.json").write_text(
        json.dumps(
            {
                "n_rows": 200,
                "n_storm_days": 21,
                "per_hotspot_thresholds": {
                    "floods_caught": 120,
                    "floods_missed": 17,
                    "false_alarms": 10,
                    "correct_clear": 53,
                    "n_flooded_rows": 137,
                    "n_clear_rows": 63,
                },
                "pooled_only_baseline": {
                    "floods_caught": 100,
                    "floods_missed": 37,
                    "false_alarms": 20,
                    "correct_clear": 43,
                    "n_flooded_rows": 137,
                    "n_clear_rows": 63,
                },
                "per_storm_day": [],
                "notes": ["Deterministic API test fixture."],
            }
        ),
        encoding="utf-8",
    )
    with (tmp_path / "events.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "event_id",
                "date",
                "hotspot_id",
                "underpass_name_in_source",
                "outcome",
                "what_happened",
                "time_text",
                "time_confidence",
                "rain_reported_in_article",
                "notes",
                "source_url",
                "source_publisher",
            ],
        )
        writer.writeheader()
        for index in range(200):
            hotspot_id = hotspot_ids[index % len(hotspot_ids)]
            writer.writerow(
                {
                    "event_id": f"test-{index:03d}",
                    "date": f"2024-07-{index % 21 + 1:02d}",
                    "hotspot_id": hotspot_id,
                    "underpass_name_in_source": hotspot_id,
                    "outcome": "flooded" if index < 137 else "clear",
                    "what_happened": "Test fixture outcome",
                }
            )

    settings = Settings(_env_file=None)
    service = UnderpassRiskService(settings, data_dir=tmp_path)
    service._fetch_live_forecast = lambda: ([], "offline_test")  # type: ignore[method-assign]
    return TestClient(create_app(MemoryRepository(), service))


def test_underpass_hotspots(client: TestClient) -> None:
    response = client.get("/api/v1/underpass/hotspots")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 16
    hotspot_ids = {h["id"] for h in data}
    assert "minto_bridge" in hotspot_ids
    assert "zakhira" in hotspot_ids


def test_underpass_risk_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/risk")
    assert response.status_code == 200
    data = response.json()
    assert "hotspots" in data
    assert len(data["hotspots"]) == 16
    assert data["lookahead_hours"] == 24
    assert "disclaimer" in data
    assert any(h["id"] == "minto_bridge" for h in data["hotspots"])
    assert data["forecast_status"] == "unavailable"
    assert data["forecast_age_seconds"] is None
    assert {hotspot["tier"] for hotspot in data["hotspots"]} == {"unknown"}


def test_underpass_forecast_cache_is_bounded_and_labelled(client: TestClient) -> None:
    service = client.app.state.underpass_service
    now = datetime.now().replace(second=0, microsecond=0)
    results = [
        {
            "hourly": {
                "time": [(now + timedelta(hours=hour)).isoformat() for hour in range(-1, 25)],
                "precipitation": [1.0] * 26,
            }
        }
        for _ in service.hotspots
    ]
    service._cache["forecast"] = {
        "at": time.time() - service.settings.forecast_cache_seconds - 1,
        "results": results,
        "model_used": "test-model",
    }

    stale = client.get("/api/v1/risk?force_refresh=true")
    assert stale.status_code == 200
    assert stale.json()["forecast_status"] == "stale"
    assert stale.json()["forecast_age_seconds"] >= service.settings.forecast_cache_seconds

    service._cache["forecast"]["at"] = (
        time.time() - service.settings.forecast_stale_cache_seconds - 1
    )
    expired = client.get("/api/v1/risk?force_refresh=true")
    assert expired.status_code == 200
    assert expired.json()["forecast_status"] == "unavailable"
    assert {hotspot["tier"] for hotspot in expired.json()["hotspots"]} == {"unknown"}


def test_malformed_forecast_is_unavailable(client: TestClient) -> None:
    service = client.app.state.underpass_service
    service._fetch_live_forecast = lambda: ([{} for _ in service.hotspots], "test-model")

    response = client.get("/api/v1/risk?force_refresh=true")

    assert response.status_code == 200
    assert response.json()["forecast_status"] == "unavailable"


def test_partial_or_null_forecast_is_unavailable(client: TestClient) -> None:
    service = client.app.state.underpass_service
    now = datetime.now().replace(second=0, microsecond=0)
    valid = {
        "hourly": {
            "time": [(now + timedelta(hours=hour)).isoformat() for hour in range(-1, 25)],
            "precipitation": [1.0] * 26,
        }
    }
    all_null = {
        "hourly": {
            "time": valid["hourly"]["time"],
            "precipitation": [None] * 24,
        }
    }
    service._fetch_live_forecast = lambda: (  # type: ignore[method-assign]
        [valid for _ in service.hotspots[:-1]] + [all_null],
        "test-model",
    )

    response = client.get("/api/v1/risk?force_refresh=true")

    assert response.status_code == 200
    assert response.json()["forecast_status"] == "unavailable"
    assert {hotspot["tier"] for hotspot in response.json()["hotspots"]} == {"unknown"}


@pytest.mark.parametrize("invalid_value", [-1.0, float("nan"), float("inf")])
def test_invalid_forecast_precipitation_is_unavailable(
    client: TestClient, invalid_value: float
) -> None:
    service = client.app.state.underpass_service
    now = datetime.now().replace(second=0, microsecond=0)
    precipitation = [1.0] * 26
    precipitation[5] = invalid_value
    invalid = {
        "hourly": {
            "time": [(now + timedelta(hours=hour)).isoformat() for hour in range(-1, 25)],
            "precipitation": precipitation,
        }
    }
    service._fetch_live_forecast = lambda: (  # type: ignore[method-assign]
        [invalid for _ in service.hotspots],
        "test-model",
    )

    response = client.get("/api/v1/risk?force_refresh=true")

    assert response.status_code == 200
    assert response.json()["forecast_status"] == "unavailable"
    assert {hotspot["tier"] for hotspot in response.json()["hotspots"]} == {"unknown"}


def test_truncated_forecast_is_unavailable(client: TestClient) -> None:
    service = client.app.state.underpass_service
    now = datetime.now().replace(second=0, microsecond=0)
    truncated = {
        "hourly": {
            "time": [(now + timedelta(hours=hour)).isoformat() for hour in range(1, 24)],
            "precipitation": [0.0] * 23,
        }
    }
    service._fetch_live_forecast = lambda: (  # type: ignore[method-assign]
        [truncated for _ in service.hotspots],
        "test-model",
    )

    response = client.get("/api/v1/risk?force_refresh=true")

    assert response.status_code == 200
    assert response.json()["forecast_status"] == "unavailable"
    assert {hotspot["tier"] for hotspot in response.json()["hotspots"]} == {"unknown"}


def test_missing_matching_threshold_is_unknown() -> None:
    now = datetime.now().astimezone()
    result = assess_hotspot(
        {"id": "test", "name": "Test", "lat": 28.6, "lon": 77.2},
        {"pooled": {}},
        [(now + timedelta(hours=1), 1.0, None)],
        [],
    )

    assert result["tier"] == "unknown"
    assert result["ratio"] is None


def test_underpass_metrics(client: TestClient) -> None:
    response = client.get("/api/v1/underpass/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["n_rows"] == 200
    assert data["n_storm_days"] == 21
    assert "per_hotspot_thresholds" in data
    assert data["per_hotspot_thresholds"]["n_flooded_rows"] == 137
    assert data["per_hotspot_thresholds"]["n_clear_rows"] == 63


def test_underpass_events(client: TestClient) -> None:
    response = client.get("/api/v1/underpass/events")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 100

    all_events = client.get("/api/v1/underpass/events?limit=200")
    assert all_events.status_code == 200
    assert len(all_events.json()) == 200

    assert client.get("/api/v1/underpass/events?limit=201").status_code == 422

    filtered = client.get("/api/v1/underpass/events?outcome=clear")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 63


def test_community_reports_flow(client: TestClient) -> None:
    report_id = str(uuid4())
    payload = {
        "report_id": report_id,
        "hotspot_id": "zakhira",
        "latitude": 0,
        "longitude": 0,
        "status": "flooded",
        "notes": "Water accumulating under railway bridge",
    }
    create_resp = client.post("/api/v1/underpass/reports", json=payload)
    assert create_resp.status_code == 201
    report = create_resp.json()
    assert report["hotspot_id"] == "zakhira"
    assert report["status"] == "flooded"
    assert report["is_active"] is True
    assert report["report_id"] == report_id
    assert report["latitude"] == pytest.approx(28.51)
    assert report["longitude"] == pytest.approx(77.11)

    list_resp = client.get("/api/v1/underpass/reports?hotspot_id=zakhira")
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert any(r["report_id"] == report["report_id"] for r in reports)

    retry = client.post("/api/v1/underpass/reports", json=payload)
    assert retry.status_code == 200
    assert retry.json()["report_id"] == report_id
    assert len(client.get("/api/v1/underpass/reports").json()) == 1

    conflict = client.post(
        "/api/v1/underpass/reports", json={**payload, "notes": "Different payload"}
    )
    assert conflict.status_code == 409

    invalid = client.post(
        "/api/v1/underpass/reports",
        json={**payload, "report_id": str(uuid4()), "hotspot_id": "nonexistent_spot"},
    )
    assert invalid.status_code == 400

    unsafe_image = client.post(
        "/api/v1/underpass/reports",
        json={**payload, "report_id": str(uuid4()), "image_url": "data:image/png;base64,AAAA"},
    )
    assert unsafe_image.status_code == 422


def test_idempotent_report_retry_recalculates_expiry(client: TestClient) -> None:
    payload = {
        "report_id": str(uuid4()),
        "hotspot_id": "zakhira",
        "latitude": 0,
        "longitude": 0,
        "status": "flooded",
        "notes": "Water accumulating",
    }
    assert client.post("/api/v1/underpass/reports", json=payload).status_code == 201
    repository = client.app.state.repository
    repository.reports[0] = repository.reports[0].model_copy(
        update={"timestamp": datetime.now().astimezone() - timedelta(minutes=46)}
    )

    retry = client.post("/api/v1/underpass/reports", json=payload)

    assert retry.status_code == 200
    assert retry.json()["is_active"] is False


def test_community_report_does_not_require_underpass_dataset() -> None:
    service = UnderpassRiskService(Settings(_env_file=None), data_dir=Path("missing"))
    client = TestClient(create_app(MemoryRepository(), service))

    response = client.post(
        "/api/v1/underpass/reports",
        json={
            "report_id": str(uuid4()),
            "hotspot_id": "reported-location",
            "latitude": 28.6139,
            "longitude": 77.209,
            "status": "passable",
        },
    )

    assert response.status_code == 201
    assert response.json()["latitude"] == pytest.approx(28.6139)


def test_malformed_required_dataset_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "hotspots.json").write_text("{}", encoding="utf-8")
    (tmp_path / "thresholds.json").write_text("{}", encoding="utf-8")
    (tmp_path / "metrics.json").write_text("{}", encoding="utf-8")
    (tmp_path / "events.csv").write_text("event_id\ninvalid", encoding="utf-8")

    service = UnderpassRiskService(Settings(_env_file=None), data_dir=tmp_path)
    unavailable_client = TestClient(create_app(MemoryRepository(), service))

    assert service.is_available is False
    assert unavailable_client.get("/api/v1/underpass/metrics").status_code == 503


def test_dashboard_summary_includes_underpass_stats(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hotspots"] == 16
    assert data["active_flood_alerts"] is None
    assert data["underpass_dataset"] == "available"
    assert data["flood_risk_status"] == "unknown"
    assert "active_community_reports" in data


def test_dashboard_summary_does_not_treat_missing_dataset_as_zero_risk() -> None:
    service = UnderpassRiskService(Settings(_env_file=None), data_dir=Path("missing"))
    unavailable_client = TestClient(create_app(MemoryRepository(), service))

    response = unavailable_client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert response.json()["active_flood_alerts"] is None
    assert response.json()["underpass_dataset"] == "unavailable"
    assert response.json()["flood_risk_status"] == "unknown"


REAL_DATASET_DIR = Path("data/underpass")


def _real_dataset_service() -> UnderpassRiskService:
    return UnderpassRiskService(Settings(_env_file=None), data_dir=REAL_DATASET_DIR)


def test_real_recovered_dataset_loads_and_matches_documented_counts() -> None:
    service = _real_dataset_service()

    assert service.is_available is True
    assert len(service.get_hotspots()) == 16
    assert {h["id"] for h in service.get_hotspots()} >= {"minto_bridge", "pul_prahladpur", "zakhira"}

    metrics = service.get_metrics()
    assert metrics["n_rows"] == 46
    assert metrics["n_storm_days"] == 15
    assert metrics["per_hotspot_thresholds"]["n_flooded_rows"] == 37
    assert metrics["per_hotspot_thresholds"]["n_clear_rows"] == 9

    events = service.get_events()
    assert len(events) == 46
    assert {e["outcome"] for e in events} <= {"flooded", "clear"}


def test_real_dataset_risk_endpoint_is_unknown_without_usable_forecast() -> None:
    service = _real_dataset_service()
    service._fetch_live_forecast = lambda: ([], "offline_test")  # type: ignore[method-assign]
    client = TestClient(create_app(MemoryRepository(), service))

    response = client.get("/api/v1/risk")

    assert response.status_code == 200
    data = response.json()
    assert len(data["hotspots"]) == 16
    assert data["forecast_status"] == "unavailable"
    assert {hotspot["tier"] for hotspot in data["hotspots"]} == {"unknown"}
    for hotspot in data["hotspots"]:
        assert hotspot["ratio"] is None


def test_real_dataset_uses_own_hotspot_threshold_not_pooled_default() -> None:
    """Minto Bridge has its own 3.5mm/1h, 6.3mm/3h threshold in thresholds.json,
    distinct from the 2.2mm/4.4mm pooled default used by hotspots without evidence."""
    service = _real_dataset_service()
    hotspot_ids = [h["id"] for h in service.get_hotspots()]
    target_index = hotspot_ids.index("minto_bridge")

    now = datetime.now(IST)
    base = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    times = [base + timedelta(hours=offset) for offset in range(30)]
    time_strings = [t.replace(tzinfo=None).isoformat() for t in times]

    def build_result(rain_hours: set[int]) -> dict:
        precipitation = [2.2 if offset in rain_hours else 0.0 for offset in range(30)]
        return {"hourly": {"time": time_strings, "precipitation": precipitation}}

    rainy_offsets = {6, 7, 8}  # three consecutive hours -> 6.6mm/3h, above Minto Bridge's 6.3mm limit
    results = [
        build_result(rainy_offsets) if index == target_index else build_result(set())
        for index in range(len(hotspot_ids))
    ]
    service._fetch_live_forecast = lambda: (results, "offline_test")  # type: ignore[method-assign]
    client = TestClient(create_app(MemoryRepository(), service))

    response = client.get("/api/v1/risk")
    assert response.status_code == 200
    data = response.json()

    minto = next(h for h in data["hotspots"] if h["id"] == "minto_bridge")
    assert minto["limit"]["rain3h_mm"] == pytest.approx(6.3, abs=0.05)
    assert minto["limit_is_own"] is True
    assert minto["tier"] in {"orange", "red"}
    assert minto["forecast"]["max_3h_mm"] == pytest.approx(6.6, abs=0.05)

    others_still_green = [h for h in data["hotspots"] if h["id"] != "minto_bridge"]
    assert all(h["tier"] == "green" for h in others_still_green)
