import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Protocol
from uuid import UUID

from app.schemas import Incident, IncidentStatus, SensorReading


class StorageRepository(Protocol):
    def add_reading(self, reading: SensorReading) -> None: ...

    def list_readings(self, limit: int) -> list[SensorReading]: ...

    def add_incident(self, incident: Incident) -> None: ...

    def list_incidents(self) -> list[Incident]: ...

    def get_incident(self, incident_id: UUID) -> Incident | None: ...

    def update_incident_status(
        self, incident_id: UUID, status: IncidentStatus, updated_at: datetime
    ) -> Incident | None: ...


class MemoryRepository:
    def __init__(self) -> None:
        self.readings: list[SensorReading] = []
        self.incidents: list[Incident] = []

    def add_reading(self, reading: SensorReading) -> None:
        self.readings.append(reading)

    def list_readings(self, limit: int) -> list[SensorReading]:
        return sorted(self.readings, key=lambda item: item.timestamp, reverse=True)[:limit]

    def add_incident(self, incident: Incident) -> None:
        self.incidents.append(incident)

    def list_incidents(self) -> list[Incident]:
        return sorted(self.incidents, key=lambda item: item.created_at, reverse=True)

    def get_incident(self, incident_id: UUID) -> Incident | None:
        return next(
            (item for item in self.incidents if item.incident_id == incident_id), None
        )

    def update_incident_status(
        self, incident_id: UUID, status: IncidentStatus, updated_at: datetime
    ) -> Incident | None:
        incident = self.get_incident(incident_id)
        if incident is None:
            return None
        updated = incident.model_copy(update={"status": status, "updated_at": updated_at})
        self.incidents = [
            updated if item.incident_id == incident_id else item for item in self.incidents
        ]
        return updated


class JsonFileRepository(MemoryRepository):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self._lock = Lock()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.readings = [SensorReading.model_validate(item) for item in payload["readings"]]
        self.incidents = [Incident.model_validate(item) for item in payload["incidents"]]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "readings": [item.model_dump(mode="json") for item in self.readings],
            "incidents": [item.model_dump(mode="json") for item in self.incidents],
        }
        temporary_path = self.path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary_path.replace(self.path)

    def add_reading(self, reading: SensorReading) -> None:
        with self._lock:
            super().add_reading(reading)
            self._save()

    def add_incident(self, incident: Incident) -> None:
        with self._lock:
            super().add_incident(incident)
            self._save()

    def update_incident_status(
        self, incident_id: UUID, status: IncidentStatus, updated_at: datetime
    ) -> Incident | None:
        with self._lock:
            incident = super().update_incident_status(incident_id, status, updated_at)
            if incident is not None:
                self._save()
            return incident
