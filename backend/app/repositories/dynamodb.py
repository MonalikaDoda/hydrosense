import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

import boto3

from app.schemas import Incident, IncidentStatus, SensorReading


class DynamoDbTable(Protocol):
    def put_item(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_item(self, **kwargs: Any) -> dict[str, Any]: ...

    def scan(self, **kwargs: Any) -> dict[str, Any]: ...


def _dynamodb_item(model: SensorReading | Incident) -> dict[str, Any]:
    payload = model.model_dump(mode="json")
    return json.loads(json.dumps(payload), parse_float=Decimal)


class DynamoDbRepository:
    def __init__(
        self,
        readings_table_name: str,
        incidents_table_name: str,
        region_name: str,
        *,
        readings_table: DynamoDbTable | None = None,
        incidents_table: DynamoDbTable | None = None,
    ) -> None:
        if readings_table is None or incidents_table is None:
            resource = boto3.resource("dynamodb", region_name=region_name)
            readings_table = readings_table or resource.Table(readings_table_name)
            incidents_table = incidents_table or resource.Table(incidents_table_name)
        self.readings_table = readings_table
        self.incidents_table = incidents_table

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