from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_underpass_hotspots() -> None:
    response = client.get("/api/v1/underpass/hotspots")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 16
    hotspot_ids = {h["id"] for h in data}
    assert "minto_bridge" in hotspot_ids
    assert "zakhira" in hotspot_ids


def test_underpass_risk_endpoint() -> None:
    response = client.get("/api/v1/risk")
    assert response.status_code == 200
    data = response.json()
    assert "hotspots" in data
    assert len(data["hotspots"]) == 16
    assert data["lookahead_hours"] == 24
    assert "disclaimer" in data
    assert any(h["id"] == "minto_bridge" for h in data["hotspots"])


def test_underpass_metrics() -> None:
    response = client.get("/api/v1/underpass/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["n_rows"] == 200
    assert data["n_storm_days"] == 21
    assert "per_hotspot_thresholds" in data
    assert data["per_hotspot_thresholds"]["n_flooded_rows"] == 137
    assert data["per_hotspot_thresholds"]["n_clear_rows"] == 63


def test_underpass_events() -> None:
    response = client.get("/api/v1/underpass/events")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 200

    filtered = client.get("/api/v1/underpass/events?outcome=clear")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 63


def test_community_reports_flow() -> None:
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


def test_dashboard_summary_includes_underpass_stats() -> None:
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hotspots"] == 16
    assert "active_flood_alerts" in data
    assert "active_community_reports" in data
