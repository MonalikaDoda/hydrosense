from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.config import Settings
from app.repositories import StorageRepository
from app.schemas import (
    HazardType,
    Incident,
    IncidentStatus,
    SensorReading,
    Severity,
)


class InvalidStatusTransition(ValueError):
    pass


ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.OPEN: {
        IncidentStatus.ASSIGNED,
        IncidentStatus.VERIFIED,
        IncidentStatus.DISMISSED,
    },
    IncidentStatus.ASSIGNED: {
        IncidentStatus.VERIFIED,
        IncidentStatus.RESOLVED,
        IncidentStatus.DISMISSED,
    },
    IncidentStatus.VERIFIED: {
        IncidentStatus.RESOLVED,
        IncidentStatus.DISMISSED,
    },
    IncidentStatus.RESOLVED: set(),
    IncidentStatus.DISMISSED: set(),
}


class WaterReadingService:
    def __init__(self, repository: StorageRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def ingest(self, reading: SensorReading) -> SensorReading:
        self.repository.add_reading(reading)
        if reading.water_depth_cm >= self.settings.water_alert_threshold_cm:
            self._create_incident_unless_duplicate(reading)
        return reading

    def _create_incident_unless_duplicate(self, reading: SensorReading) -> None:
        cooldown_start = reading.timestamp - timedelta(
            seconds=self.settings.alert_cooldown_seconds
        )
        duplicate = any(
            incident.hazard_type == HazardType.HIGH_WATER_LEVEL
            and incident.location_id == reading.location_id
            and incident.status
            in {IncidentStatus.OPEN, IncidentStatus.ASSIGNED, IncidentStatus.VERIFIED}
            and cooldown_start <= incident.created_at <= reading.timestamp
            for incident in self.repository.list_incidents()
        )
        if duplicate:
            return

        incident = Incident(
            incident_id=uuid4(),
            hazard_type=HazardType.HIGH_WATER_LEVEL,
            title="Prototype water level threshold crossed",
            location_id=reading.location_id,
            latitude=self.settings.demo_latitude,
            longitude=self.settings.demo_longitude,
            severity=self._severity(reading.water_depth_cm),
            confidence=0.9,
            status=IncidentStatus.OPEN,
            source=reading.source,
            evidence={
                "water_depth_cm": reading.water_depth_cm,
                "distance_cm": reading.distance_cm,
                "threshold_cm": self.settings.water_alert_threshold_cm,
                "label": "DEMO LOCATION",
            },
            created_at=reading.timestamp,
            updated_at=reading.timestamp,
        )
        self.repository.add_incident(incident)

    def _severity(self, depth_cm: float) -> Severity:
        if depth_cm >= self.settings.water_alert_threshold_cm + 10:
            return Severity.VERY_HIGH
        return Severity.HIGH

    def update_status(self, incident_id: UUID, status: IncidentStatus) -> Incident | None:
        incident = self.repository.get_incident(incident_id)
        if incident is None:
            return None
        if status == incident.status:
            return incident
        if status not in ALLOWED_TRANSITIONS[incident.status]:
            raise InvalidStatusTransition(
                f"cannot transition incident from {incident.status} to {status}"
            )
        return self.repository.update_incident_status(
            incident_id, status, datetime.now(UTC)
        )
