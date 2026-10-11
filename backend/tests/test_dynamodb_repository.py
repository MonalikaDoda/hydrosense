from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.repositories import DynamoDbRepository
from app.schemas import (
    CommunityReport,
    CommunityReportStatus,
    HazardType,
    Incident,
    IncidentStatus,
    SensorReading,
    Severity,
    SourceLabel,
)


class FakeTable:
    def __init__(self, key_name: str) -> None:
        self.key_name = key_name
        self.items: dict[object, dict[str, Any]] = {}

    def put_item(self, **kwargs: Any) -> dict[str, Any]:
        item = kwargs["Item"]
        self.items[item[self.key_name]] = item
        return {}

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        key = kwargs["Key"][self.key_name]
        item = self.items.get(key)
        return {"Item": item} if item is not None else {}

    def scan(self, **kwargs: Any) -> dict[str, Any]:
        return {"Items": list(self.items.values())}


def make_repository() -> tuple[DynamoDbRepository, FakeTable, FakeTable, FakeTable]:
    readings = FakeTable("device_id")
    incidents = FakeTable("incident_id")
    reports = FakeTable("report_id")
    repository = DynamoDbRepository(
        "readings",
        "incidents",
        "ap-south-1",
        readings_table=readings,
        incidents_table=incidents,
        reports_table=reports,
    )
    return repository, readings, incidents, reports


def test_reading_round_trips_with_decimal_storage() -> None:
    repository, readings_table, _, _ = make_repository()
    reading = SensorReading(
        device_id="hydrosense-simulator-01",
        location_id="demo-zone-01",
        water_depth_cm=26.5,
        distance_cm=3.5,
        timestamp=datetime.now(UTC),
        source=SourceLabel.SIMULATED_SENSOR,
    )

    repository.add_reading(reading)
    stored = next(iter(readings_table.items.values()))

    assert stored["water_depth_cm"] == Decimal("26.5")
    assert repository.list_readings(1)[0] == reading


def test_incident_status_update_persists() -> None:
    repository, _, _, _ = make_repository()
    timestamp = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid4(),
        hazard_type=HazardType.HIGH_WATER_LEVEL,
        title="Prototype water level threshold crossed",
        location_id="demo-zone-01",
        latitude=28.6139,
        longitude=77.209,
        severity=Severity.HIGH,
        confidence=0.9,
        status=IncidentStatus.OPEN,
        source=SourceLabel.SIMULATED_SENSOR,
        evidence={"water_depth_cm": 26.0, "threshold_cm": 24.0},
        created_at=timestamp,
        updated_at=timestamp,
    )
    repository.add_incident(incident)

    updated = repository.update_incident_status(
        incident.incident_id, IncidentStatus.VERIFIED, datetime.now(UTC)
    )

    assert updated is not None
    assert repository.get_incident(incident.incident_id).status == IncidentStatus.VERIFIED


def test_community_report_round_trips_with_ttl_metadata() -> None:
    repository, _, _, reports_table = make_repository()
    report = CommunityReport(
        report_id=uuid4(),
        hotspot_id="zakhira",
        status=CommunityReportStatus.FLOODED,
        timestamp=datetime.now(UTC),
        notes="Water accumulating",
    )

    repository.add_community_report(report)
    stored = next(iter(reports_table.items.values()))

    assert stored["expires_at"] > int(report.timestamp.timestamp())
    assert repository.list_community_reports(hotspot_id="zakhira") == [report]