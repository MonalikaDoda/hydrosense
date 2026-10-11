import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

import boto3

from app.schemas import CommunityReport, Incident, IncidentStatus, SensorReading


class DynamoDbTable(Protocol):
    def put_item(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_item(self, **kwargs: Any) -> dict[str, Any]: ...

    def scan(self, **kwargs: Any) -> dict[str, Any]: ...


def _dynamodb_item(model: SensorReading | Incident | CommunityReport) -> dict[str, Any]:
    payload = model.model_dump(mode="json")
    item = json.loads(json.dumps(payload), parse_float=Decimal)
    if isinstance(model, CommunityReport):
        item["expires_at"] = int((model.timestamp + timedelta(minutes=45)).timestamp())
    return item


class DynamoDbRepository:
    def __init__(
        self,
        readings_table_name: str,
        incidents_table_name: str,
        region_name: str,
        reports_table_name: str = "hydrosense-reports-dev",
        *,
        readings_table: DynamoDbTable | None = None,
        incidents_table: DynamoDbTable | None = None,
        reports_table: DynamoDbTable | None = None,
    ) -> None:
        if readings_table is None or incidents_table is None or reports_table is None:
            resource = boto3.resource("dynamodb", region_name=region_name)
            readings_table = readings_table or resource.Table(readings_table_name)
            incidents_table = incidents_table or resource.Table(incidents_table_name)
            reports_table = reports_table or resource.Table(reports_table_name)
        self.readings_table = readings_table
        self.incidents_table = incidents_table
        self.reports_table = reports_table

    def add_reading(self, reading: SensorReading) -> None:
        self.readings_table.put_item(Item=_dynamodb_item(reading))

    def list_readings(self, limit: int) -> list[SensorReading]:
        readings = [
            SensorReading.model_validate(item)
            for item in self._scan_all(self.readings_table)
        ]
        return sorted(readings, key=lambda item: item.timestamp, reverse=True)[:limit]

    def add_incident(self, incident: Incident) -> None:
        self.incidents_table.put_item(Item=_dynamodb_item(incident))

    def list_incidents(self) -> list[Incident]:
        incidents = [
            Incident.model_validate(item)
            for item in self._scan_all(self.incidents_table)
        ]
        return sorted(incidents, key=lambda item: item.created_at, reverse=True)

    def get_incident(self, incident_id: UUID) -> Incident | None:
        response = self.incidents_table.get_item(Key={"incident_id": str(incident_id)})
        item = response.get("Item")
        return Incident.model_validate(item) if item is not None else None

    def update_incident_status(
        self, incident_id: UUID, status: IncidentStatus, updated_at: datetime
    ) -> Incident | None:
        incident = self.get_incident(incident_id)
        if incident is None:
            return None
        updated = incident.model_copy(update={"status": status, "updated_at": updated_at})
        self.incidents_table.put_item(Item=_dynamodb_item(updated))
        return updated

    def add_community_report(self, report: CommunityReport) -> None:
        self.reports_table.put_item(Item=_dynamodb_item(report))

    def list_community_reports(
        self,
        hotspot_id: str | None = None,
        active_only: bool = True,
        max_age_minutes: int = 45,
    ) -> list[CommunityReport]:
        cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        reports: list[CommunityReport] = []
        for item in self._scan_all(self.reports_table):
            payload = {key: value for key, value in item.items() if key != "expires_at"}
            report = CommunityReport.model_validate(payload)
            if hotspot_id and report.hotspot_id != hotspot_id:
                continue
            is_fresh = report.timestamp >= cutoff
            if active_only and not is_fresh:
                continue
            reports.append(report.model_copy(update={"is_active": is_fresh}))
        return sorted(reports, key=lambda item: item.timestamp, reverse=True)

    @staticmethod
    def _scan_all(table: DynamoDbTable) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        request: dict[str, Any] = {}
        while True:
            response = table.scan(**request)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if last_key is None:
                return items
            request["ExclusiveStartKey"] = last_key