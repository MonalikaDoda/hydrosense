from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories import JsonFileRepository, MemoryRepository
from app.schemas import SensorReading
from app.services import WaterReadingService


def reading_payload(depth: float, timestamp: datetime) -> dict[str, object]:
    return {
        "device_id": "hydrosense-simulator-01",
        "location_id": "demo-zone-01",
        "water_depth_cm": depth,
        "distance_cm": 30 - depth,
        "timestamp": timestamp.isoformat(),
        "source": "simulated_sensor",
    }


def test_ingestion_stores_reading_without_incident_below_threshold() -> None:
    client = TestClient(create_app(MemoryRepository()))

    response = client.post(
        "/api/v1/readings", json=reading_payload(20, datetime.now(UTC))
    )

    assert response.status_code == 201
    assert client.get("/api/v1/readings/latest").json()[0]["water_depth_cm"] == 20
    assert client.get("/api/v1/incidents").json() == []


def test_water_threshold_is_configurable() -> None:
    repository = MemoryRepository()
    service = WaterReadingService(
        repository, Settings(water_alert_threshold_cm=10)
    )

    service.ingest(SensorReading.model_validate(reading_payload(11, datetime.now(UTC))))

    assert len(repository.list_incidents()) == 1


def test_threshold_crossing_creates_incident_and_suppresses_duplicate() -> None:
    client = TestClient(create_app(MemoryRepository()))
    timestamp = datetime.now(UTC)

    first = client.post("/api/v1/readings", json=reading_payload(25, timestamp))
    second = client.post(
        "/api/v1/readings", json=reading_payload(26, timestamp + timedelta(seconds=30))
    )
    incidents = client.get("/api/v1/incidents").json()

    assert first.status_code == 201
    assert second.status_code == 201
    assert len(incidents) == 1
    assert incidents[0]["evidence"]["threshold_cm"] == 24
    assert incidents[0]["source"] == "simulated_sensor"


def test_new_incident_is_allowed_after_cooldown() -> None:
    client = TestClient(create_app(MemoryRepository()))
    timestamp = datetime.now(UTC)

    client.post("/api/v1/readings", json=reading_payload(25, timestamp))
    client.post(
        "/api/v1/readings", json=reading_payload(25, timestamp + timedelta(minutes=6))
    )

    assert len(client.get("/api/v1/incidents").json()) == 2


def test_incident_detail_and_status_transitions() -> None:
    client = TestClient(create_app(MemoryRepository()))
    client.post("/api/v1/readings", json=reading_payload(25, datetime.now(UTC)))
    incident = client.get("/api/v1/incidents").json()[0]
    incident_url = f"/api/v1/incidents/{incident['incident_id']}"

    assert client.get(incident_url).status_code == 200
    assert client.patch(incident_url, json={"status": "verified"}).status_code == 200
    resolved = client.patch(incident_url, json={"status": "resolved"})
    invalid = client.patch(incident_url, json={"status": "open"})

    assert resolved.json()["status"] == "resolved"
    assert invalid.status_code == 409


def test_missing_incident_returns_not_found() -> None:
    client = TestClient(create_app(MemoryRepository()))

    response = client.get("/api/v1/incidents/9ad4a91b-9cce-4bb0-84c0-d5bd15cf5655")

    assert response.status_code == 404


def test_json_repository_persists_readings_and_incidents(tmp_path) -> None:
    storage_path = tmp_path / "hydrosense.json"
    repository = JsonFileRepository(storage_path)
    client = TestClient(create_app(repository))
    client.post("/api/v1/readings", json=reading_payload(25, datetime.now(UTC)))

    reloaded = JsonFileRepository(storage_path)

    assert len(reloaded.list_readings(10)) == 1
    assert len(reloaded.list_incidents()) == 1