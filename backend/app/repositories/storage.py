import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.schemas import AssessmentStatus, CommunityReport, Incident, IncidentStatus, SensorReading


class StorageRepository(Protocol):
    def check_health(self) -> None: ...

    def add_reading(self, reading: SensorReading) -> None: ...

    def list_readings(self, limit: int) -> list[SensorReading]: ...

    def add_incident(self, incident: Incident) -> None: ...

    def add_incident_if_not_recent(
        self, incident: Incident, cooldown_start: datetime
    ) -> bool: ...

    def list_incidents(self, limit: int = 1000) -> list[Incident]: ...

    def get_incident(self, incident_id: UUID) -> Incident | None: ...

    def update_incident_status(
        self, incident_id: UUID, status: IncidentStatus, updated_at: datetime
    ) -> Incident | None: ...

    def add_community_report(self, report: CommunityReport) -> bool: ...

    def get_community_report(self, report_id: UUID) -> CommunityReport | None: ...

    def list_community_reports(
        self,
        hotspot_id: str | None = None,
        active_only: bool = True,
        max_age_minutes: int = 45,
        limit: int = 1000,
    ) -> list[CommunityReport]: ...

    def update_report_assessment(
        self,
        report_id: UUID,
        *,
        image_key: str | None,
        assessment_status: AssessmentStatus,
        ai_assessment: dict[str, object] | None,
    ) -> CommunityReport | None: ...


class MemoryRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.readings: list[SensorReading] = []
        self.incidents: list[Incident] = []
        self.reports: list[CommunityReport] = []

    def check_health(self) -> None:
        return None

    def add_reading(self, reading: SensorReading) -> None:
        self.readings.append(reading)

    def list_readings(self, limit: int) -> list[SensorReading]:
        return sorted(self.readings, key=lambda item: item.timestamp, reverse=True)[:limit]

    def add_incident(self, incident: Incident) -> None:
        self.incidents.append(incident)

    def add_incident_if_not_recent(
        self, incident: Incident, cooldown_start: datetime
    ) -> bool:
        with self._lock:
            duplicate = any(
                item.hazard_type == incident.hazard_type
                and item.location_id == incident.location_id
                and cooldown_start <= item.created_at <= incident.created_at
                for item in self.incidents
            )
            if duplicate:
                return False
            self.incidents.append(incident)
            return True

    def list_incidents(self, limit: int = 1000) -> list[Incident]:
        return sorted(self.incidents, key=lambda item: item.created_at, reverse=True)[:limit]

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

    def add_community_report(self, report: CommunityReport) -> bool:
        if self.get_community_report(report.report_id) is not None:
            return False
        self.reports.append(report)
        return True

    def get_community_report(self, report_id: UUID) -> CommunityReport | None:
        return next((item for item in self.reports if item.report_id == report_id), None)

    def list_community_reports(
        self,
        hotspot_id: str | None = None,
        active_only: bool = True,
        max_age_minutes: int = 45,
        limit: int = 1000,
    ) -> list[CommunityReport]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=max_age_minutes)
        out: list[CommunityReport] = []
        for r in sorted(self.reports, key=lambda item: item.timestamp, reverse=True):
            if hotspot_id and r.hotspot_id != hotspot_id:
                continue
            is_fresh = r.timestamp >= cutoff
            if active_only and not is_fresh:
                continue
            out.append(r.model_copy(update={"is_active": is_fresh}))
            if len(out) >= limit:
                break
        return out

    def update_report_assessment(
        self,
        report_id: UUID,
        *,
        image_key: str | None,
        assessment_status: AssessmentStatus,
        ai_assessment: dict[str, object] | None,
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
        self.reports = [updated if item.report_id == report_id else item for item in self.reports]
        return updated


class JsonFileRepository(MemoryRepository):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.readings = [SensorReading.model_validate(item) for item in payload.get("readings", [])]
        self.incidents = [Incident.model_validate(item) for item in payload.get("incidents", [])]
        self.reports = [
            CommunityReport.model_validate(item) for item in payload.get("reports", [])
        ]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "readings": [item.model_dump(mode="json") for item in self.readings],
            "incidents": [item.model_dump(mode="json") for item in self.incidents],
            "reports": [item.model_dump(mode="json") for item in self.reports],
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

    def add_incident_if_not_recent(
        self, incident: Incident, cooldown_start: datetime
    ) -> bool:
        with self._lock:
            created = super().add_incident_if_not_recent(incident, cooldown_start)
            if created:
                self._save()
            return created

    def update_incident_status(
        self, incident_id: UUID, status: IncidentStatus, updated_at: datetime
    ) -> Incident | None:
        with self._lock:
            incident = super().update_incident_status(incident_id, status, updated_at)
            if incident is not None:
                self._save()
            return incident

    def add_community_report(self, report: CommunityReport) -> bool:
        with self._lock:
            created = super().add_community_report(report)
            if created:
                self._save()
            return created

    def update_report_assessment(
        self,
        report_id: UUID,
        *,
        image_key: str | None,
        assessment_status: AssessmentStatus,
        ai_assessment: dict[str, object] | None,
    ) -> CommunityReport | None:
        with self._lock:
            updated = super().update_report_assessment(
                report_id,
                image_key=image_key,
                assessment_status=assessment_status,
                ai_assessment=ai_assessment,
            )
            if updated is not None:
                self._save()
            return updated
