from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from types import SimpleNamespace
from uuid import uuid4

import pytest
from boto3.dynamodb.types import TypeDeserializer

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


class ConditionalCheckFailedException(Exception):
    pass


class TransactionCanceledException(Exception):
    def __init__(self, reasons: list[dict[str, str]]) -> None:
        super().__init__("Transaction cancelled")
        self.response = {"CancellationReasons": reasons}


class FakeTable:
    def __init__(self, name: str, key_name: str) -> None:
        self.name = name
        self.key_name = key_name
        self.items: dict[object, dict[str, Any]] = {}
        self.last_get_kwargs: dict[str, Any] | None = None
        self.meta = SimpleNamespace(
            client=SimpleNamespace(
                exceptions=SimpleNamespace(
                    ConditionalCheckFailedException=ConditionalCheckFailedException
                )
            )
        )

    def put_item(self, **kwargs: Any) -> dict[str, Any]:
        item = kwargs["Item"]
        if "ConditionExpression" in kwargs and item[self.key_name] in self.items:
            raise self.meta.client.exceptions.ConditionalCheckFailedException()
        self.items[item[self.key_name]] = item
        return {}

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        self.last_get_kwargs = kwargs
        key = kwargs["Key"][self.key_name]
        item = self.items.get(key)
        return {"Item": item} if item is not None else {}

    def scan(self, **_: Any) -> dict[str, Any]:
        return {"Items": list(self.items.values())}


class FakeDynamoDbClient:
    def __init__(self, incidents_table: FakeTable) -> None:
        self.incidents_table = incidents_table
        self.exceptions = SimpleNamespace(
            TransactionCanceledException=TransactionCanceledException
        )
        self.next_cancellation_reasons: list[dict[str, str]] | None = None

    def transact_write_items(self, **kwargs: Any) -> dict[str, Any]:
        if self.next_cancellation_reasons is not None:
            reasons = self.next_cancellation_reasons
            self.next_cancellation_reasons = None
            raise TransactionCanceledException(reasons)
        update = kwargs["TransactItems"][0]["Update"]
        put = kwargs["TransactItems"][1]["Put"]
        marker_id = update["Key"]["incident_id"]["S"]
        values = update["ExpressionAttributeValues"]
        marker = self.incidents_table.items.get(marker_id)
        cooldown_start = int(values[":cooldown_start"]["N"])
        if marker and marker["last_incident_at"] >= cooldown_start:
            raise TransactionCanceledException(
                [{"Code": "ConditionalCheckFailed"}, {"Code": "None"}]
            )
        deserializer = TypeDeserializer()
        incident_item = {
            key: deserializer.deserialize(value) for key, value in put["Item"].items()
        }
        incident_id = incident_item["incident_id"]
        if incident_id in self.incidents_table.items:
            raise TransactionCanceledException(
                [{"Code": "None"}, {"Code": "ConditionalCheckFailed"}]
            )
        self.incidents_table.items[marker_id] = {
            "incident_id": marker_id,
            "record_type": values[":type"]["S"],
            "last_incident_at": int(values[":at"]["N"]),
        }
        self.incidents_table.items[incident_id] = incident_item
        return {}


def make_repository() -> tuple[DynamoDbRepository, FakeTable, FakeTable, FakeTable]:
    readings = FakeTable("readings", "device_id")
    incidents = FakeTable("incidents", "incident_id")
    reports = FakeTable("reports", "report_id")
    repository = DynamoDbRepository(
        "readings",
        "incidents",
        "ap-south-1",
        readings_table=readings,
        incidents_table=incidents,
        reports_table=reports,
        dynamodb_client=FakeDynamoDbClient(incidents),
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


def test_incident_deduplication_uses_atomic_transaction() -> None:
    repository, _, incidents_table, _ = make_repository()
    timestamp = datetime.now(UTC)

    def incident_at(created_at: datetime) -> Incident:
        return Incident(
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
            created_at=created_at,
            updated_at=created_at,
        )

    assert repository.add_incident_if_not_recent(
        incident_at(timestamp), timestamp - timedelta(minutes=5)
    )
    assert not repository.add_incident_if_not_recent(
        incident_at(timestamp + timedelta(seconds=30)), timestamp - timedelta(minutes=4, seconds=30)
    )
    assert repository.add_incident_if_not_recent(
        incident_at(timestamp + timedelta(minutes=6)), timestamp + timedelta(minutes=1)
    )
    assert len(repository.list_incidents()) == 2
    assert len(incidents_table.items) == 3

    assert repository.list_incidents(limit=1)[0].created_at == timestamp + timedelta(minutes=6)


def test_incident_transaction_operational_failure_is_not_a_duplicate() -> None:
    repository, _, _, _ = make_repository()
    client = repository.dynamodb_client
    client.next_cancellation_reasons = [
        {"Code": "TransactionConflict"},
        {"Code": "None"},
    ]
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
        evidence={},
        created_at=timestamp,
        updated_at=timestamp,
    )

    with pytest.raises(TransactionCanceledException):
        repository.add_incident_if_not_recent(
            incident, timestamp - timedelta(minutes=5)
        )


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
    assert repository.get_community_report(report.report_id) == report
    assert reports_table.last_get_kwargs is not None
    assert reports_table.last_get_kwargs["ConsistentRead"] is True
    assert repository.list_community_reports(hotspot_id="zakhira") == [report]

    assert repository.add_community_report(report) is False
    assert len(reports_table.items) == 1


def test_report_limit_is_applied_after_freshness_filter() -> None:
    repository, _, _, reports_table = make_repository()
    stale = CommunityReport(
        report_id=uuid4(),
        hotspot_id="zakhira",
        status=CommunityReportStatus.PASSABLE,
        timestamp=datetime.now(UTC) - timedelta(hours=2),
    )
    fresh = stale.model_copy(
        update={"report_id": uuid4(), "timestamp": datetime.now(UTC)}
    )
    reports_table.items[str(stale.report_id)] = {
        **stale.model_dump(mode="json"),
        "expires_at": int(stale.timestamp.timestamp()),
    }
    reports_table.items[str(fresh.report_id)] = {
        **fresh.model_dump(mode="json"),
        "expires_at": int(fresh.timestamp.timestamp()) + 2700,
    }

    assert repository.list_community_reports(active_only=True, limit=1) == [fresh]


def test_report_limit_is_applied_after_newest_first_sort() -> None:
    repository, _, _, reports_table = make_repository()
    older = CommunityReport(
        report_id=uuid4(),
        hotspot_id="zakhira",
        status=CommunityReportStatus.PASSABLE,
        timestamp=datetime.now(UTC) - timedelta(minutes=10),
    )
    newer = older.model_copy(
        update={"report_id": uuid4(), "timestamp": datetime.now(UTC)}
    )
    for report in (older, newer):
        reports_table.items[str(report.report_id)] = {
            **report.model_dump(mode="json"),
            "expires_at": int(report.timestamp.timestamp()) + 2700,
        }

    assert repository.list_community_reports(active_only=True, limit=1) == [newer]