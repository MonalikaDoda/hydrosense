from typing import cast
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import app, create_app
from app.repositories import MemoryRepository
from app.services import UnderpassRiskService


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "hydrosense-api",
        "version": "0.2.0",
    }


def test_health_allows_configured_frontend_origin() -> None:
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_allows_loopback_frontend_origin() -> None:
    response = client.get(
        "/health",
        headers={"Origin": "http://127.0.0.1:5173"},
    )

    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_readiness_reports_optional_dataset_separately() -> None:
    underpass_service = cast(UnderpassRiskService, Mock(is_available=False))
    readiness_client = TestClient(
        create_app(MemoryRepository(), underpass_service=underpass_service)
    )

    response = readiness_client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "storage": "available",
        "underpass_dataset": "unavailable",
    }


def test_readiness_fails_safely_when_storage_is_unavailable() -> None:
    repository = MemoryRepository()
    repository.check_health = Mock(side_effect=RuntimeError("sensitive dependency detail"))
    readiness_client = TestClient(create_app(repository))

    assert readiness_client.get("/health").status_code == 200

    response = readiness_client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Persistent storage is unavailable."}