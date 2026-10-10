from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.repositories import StorageRepository
from app.schemas import (
    DashboardSummary,
    HazardType,
    Incident,
    IncidentStatus,
    IncidentStatusUpdate,
    SensorReading,
)
from app.services import InvalidStatusTransition, WaterReadingService

router = APIRouter(prefix="/api/v1")


def get_repository(request: Request) -> StorageRepository:
    return request.app.state.repository


def get_reading_service(request: Request) -> WaterReadingService:
    return request.app.state.reading_service


@router.post("/readings", response_model=SensorReading, status_code=status.HTTP_201_CREATED)
def create_reading(
    reading: SensorReading,
    service: WaterReadingService = Depends(get_reading_service),
) -> SensorReading:
    return service.ingest(reading)


@router.get("/readings/latest", response_model=list[SensorReading])
def latest_readings(
    limit: int = Query(default=10, ge=1, le=100),
    repository: StorageRepository = Depends(get_repository),
) -> list[SensorReading]:
    return repository.list_readings(limit)


@router.get("/incidents", response_model=list[Incident])
def list_incidents(
    hazard_type: HazardType | None = None,
    incident_status: IncidentStatus | None = Query(default=None, alias="status"),
    repository: StorageRepository = Depends(get_repository),
) -> list[Incident]:
    incidents = repository.list_incidents()
    if hazard_type is not None:
        incidents = [item for item in incidents if item.hazard_type == hazard_type]
    if incident_status is not None:
        incidents = [item for item in incidents if item.status == incident_status]
    return incidents


@router.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(
    incident_id: UUID,
    repository: StorageRepository = Depends(get_repository),
) -> Incident:
    incident = repository.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/incidents/{incident_id}", response_model=Incident)
def update_incident(
    incident_id: UUID,
    update: IncidentStatusUpdate,
    service: WaterReadingService = Depends(get_reading_service),
) -> Incident:
    try:
        incident = service.update_status(incident_id, update.status)
    except InvalidStatusTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    repository: StorageRepository = Depends(get_repository),
) -> DashboardSummary:
    incidents = repository.list_incidents()
    readings = repository.list_readings(1)
    return DashboardSummary(
        total_incidents=len(incidents),
        open_incidents=sum(item.status == IncidentStatus.OPEN for item in incidents),
        high_priority_incidents=sum(
            item.severity.value in {"high", "very_high"} for item in incidents
        ),
        incidents_by_hazard={
            hazard: sum(item.hazard_type == hazard for item in incidents)
            for hazard in HazardType
        },
        incidents_by_status={
            incident_status: sum(item.status == incident_status for item in incidents)
            for incident_status in IncidentStatus
        },
        latest_reading_at=readings[0].timestamp if readings else None,
        generated_at=datetime.now(UTC),
    )
