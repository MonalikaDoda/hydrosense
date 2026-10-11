import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.types import TypeSerializer

from app.schemas import AssessmentStatus, CommunityReport, Incident, IncidentStatus, SensorReading


class DynamoDbTable(Protocol):
    name: str
    meta: Any

    def put_item(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_item(self, **kwargs: Any) -> dict[str, Any]: ...

    def scan(self, **kwargs: Any) -> dict[str, Any]: ...


class DynamoDbClient(Protocol):
    exceptions: Any

    def transact_write_items(self, **kwargs: Any) -> dict[str, Any]: ...


def _dynamodb_item(model: SensorReading | Incident | CommunityReport) -> dict[str, Any]:
    payload = model.model_dump(mode="json")
    item = json.loads(json.dumps(payload), parse_float=Decimal)
    if isinstance(model, CommunityReport):
        item["expires_at"] = int((model.timestamp + timedelta(minutes=45)).timestamp())
    return item


def _client_item(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    serializer = TypeSerializer()
    return {key: serializer.serialize(value) for key, value in item.items()}


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
        dynamodb_client: DynamoDbClient | None = None,
        max_scan_items: int = 1000,
    ) -> None:
        resource = None
        if readings_table is None or incidents_table is None or reports_table is None:
            resource = boto3.resource("dynamodb", region_name=region_name)
            readings_table = readings_table or resource.Table(readings_table_name)
            incidents_table = incidents_table or resource.Table(incidents_table_name)
            reports_table = reports_table or resource.Table(reports_table_name)
        self.readings_table = readings_table
        self.incidents_table = incidents_table
        self.reports_table = reports_table
        self.dynamodb_client = dynamodb_client or (
            resource.meta.client if resource is not None else incidents_table.meta.client
        )
        self.max_scan_items = max_scan_items

    def check_health(self) -> None:
        for table in (self.readings_table, self.incidents_table, self.reports_table):
            response = table.meta.client.describe_table(TableName=table.name)
            if response["Table"]["TableStatus"] != "ACTIVE":
                raise RuntimeError(f"DynamoDB table {table.name} is not active")

    def add_reading(self, reading: SensorReading) -> None:
        self.readings_table.put_item(Item=_dynamodb_item(reading))

    def list_readings(self, limit: int) -> list[SensorReading]:
        readings = [
            SensorReading.model_validate(item)
            for item in self._scan_all(self.readings_table, self.max_scan_items)
        ]
        return sorted(readings, key=lambda item: item.timestamp, reverse=True)[:limit]

    def add_incident(self, incident: Incident) -> None:
        self.incidents_table.put_item(Item=_dynamodb_item(incident))

    def add_incident_if_not_recent(
        self, incident: Incident, cooldown_start: datetime
    ) -> bool:
        marker_id = f"dedupe#{incident.hazard_type.value}#{incident.location_id}"
        incident_at_epoch = int(incident.created_at.astimezone(UTC).timestamp())
        cooldown_start_epoch = int(cooldown_start.astimezone(UTC).timestamp())
        try:
            self.dynamodb_client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self.incidents_table.name,
                            "Key": {"incident_id": {"S": marker_id}},
                            "UpdateExpression": "SET record_type = :type, last_incident_at = :at",
                            "ConditionExpression": (
                                "attribute_not_exists(last_incident_at) "
                                "OR last_incident_at < :cooldown_start"
                            ),
                            "ExpressionAttributeValues": {
                                ":type": {"S": "dedup_marker"},
                                ":at": {"N": str(incident_at_epoch)},
                                ":cooldown_start": {"N": str(cooldown_start_epoch)},
                            },
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.incidents_table.name,
                            "Item": _client_item(_dynamodb_item(incident)),
                            "ConditionExpression": "attribute_not_exists(incident_id)",
                        }
                    },
                ]
            )
        except self.dynamodb_client.exceptions.TransactionCanceledException as error:
            reasons = getattr(error, "response", {}).get("CancellationReasons", [])
            marker_failed = (
                len(reasons) == 2
                and reasons[0].get("Code") == "ConditionalCheckFailed"
                and reasons[1].get("Code") in {None, "None"}
            )
            if marker_failed:
                return False
            raise
        return True

    def list_incidents(self, limit: int = 1000) -> list[Incident]:
        incidents = [
            Incident.model_validate(item)
            for item in self._scan_all(
                self.incidents_table, self.max_scan_items
            )
            if "hazard_type" in item
        ]
        return sorted(incidents, key=lambda item: item.created_at, reverse=True)[:limit]

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

    def add_community_report(self, report: CommunityReport) -> bool:
        try:
            self.reports_table.put_item(
                Item=_dynamodb_item(report),
                ConditionExpression=Attr("report_id").not_exists(),
            )
        except self.reports_table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
        return True

    def get_community_report(self, report_id: UUID) -> CommunityReport | None:
        response = self.reports_table.get_item(
            Key={"report_id": str(report_id)}, ConsistentRead=True
        )
        item = response.get("Item")
        if item is None:
            return None
        payload = {key: value for key, value in item.items() if key != "expires_at"}
        return CommunityReport.model_validate(payload)

    def list_community_reports(
        self,
        hotspot_id: str | None = None,
        active_only: bool = True,
        max_age_minutes: int = 45,
        limit: int = 1000,
    ) -> list[CommunityReport]:
        cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        reports: list[CommunityReport] = []
        for item in self._scan_all(
            self.reports_table, self.max_scan_items
        ):
            payload = {key: value for key, value in item.items() if key != "expires_at"}
            report = CommunityReport.model_validate(payload)
            if hotspot_id and report.hotspot_id != hotspot_id:
                continue
            is_fresh = report.timestamp >= cutoff
            if active_only and not is_fresh:
                continue
            reports.append(report.model_copy(update={"is_active": is_fresh}))
        return sorted(reports, key=lambda item: item.timestamp, reverse=True)[:limit]

    def update_report_assessment(
        self,
        report_id: UUID,
        *,
        image_key: str | None,
        assessment_status: AssessmentStatus,
        ai_assessment: dict[str, Any] | None,
    ) -> CommunityReport | None:
        existing = self.get_community_report(report_id)
        if existing is None:
            return None
        updated = existing.model_copy(
            update={
                "image_key": image_key,
                "assessment_status": assessment_status,
                "ai_assessment": ai_assessment,
            }
        )
        self.reports_table.put_item(Item=_dynamodb_item(updated))
        return updated

    @staticmethod
    def _scan_all(table: DynamoDbTable, max_items: int) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        request: dict[str, Any] = {"Limit": min(max_items, 100)}
        while True:
            response = table.scan(**request)
            items.extend(response.get("Items", []))
            if len(items) >= max_items:
                return items[:max_items]
            last_key = response.get("LastEvaluatedKey")
            if last_key is None:
                return items
            request["ExclusiveStartKey"] = last_key
            request["Limit"] = min(max_items - len(items), 100)