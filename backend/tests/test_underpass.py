import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories import MemoryRepository
from app.services import UnderpassRiskService


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
                    "n_flooded_rows": 137,
                    "n_clear_rows": 63,
                },
                "pooled_only_baseline": {},
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
    assert len(data) == 200

    filtered = client.get("/api/v1/underpass/events?outcome=clear")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 63


def test_community_reports_flow(client: TestClient) -> None:
    # Submit report
    payload = {
        "hotspot_id": "zakhira",
        "status": "flooded",
        "notes": "Water accumulating under railway bridge",
    }
    create_resp = client.post("/api/v1/underpass/reports", json=payload)
    assert create_resp.status_code == 201
    report = create_resp.json()
    assert report["hotspot_id"] == "zakhira"
    assert report["status"] == "flooded"
    assert report["is_active"] is True
    assert "report_id" in report

    # Query reports
    list_resp = client.get("/api/v1/underpass/reports?hotspot_id=zakhira")
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert any(r["report_id"] == report["report_id"] for r in reports)

    # Invalid hotspot
    invalid = client.post(
        "/api/v1/underpass/reports",
        json={"hotspot_id": "nonexistent_spot", "status": "passable"},
    )
    assert invalid.status_code == 400


def test_dashboard_summary_includes_underpass_stats(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hotspots"] == 16
    assert "active_flood_alerts" in data
    assert "active_community_reports" in data
