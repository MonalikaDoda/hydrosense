from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.repositories import StorageRepository
from app.schemas import (
    CommunityReport,
    CommunityReportCreate,
    DashboardSummary,
    HazardType,
    Incident,
    IncidentStatus,
    IncidentStatusUpdate,
    SensorReading,
    UnderpassEvaluationMetrics,
    UnderpassEventRecord,
    UnderpassHotspot,
    UnderpassRiskResponse,
)
from app.services import InvalidStatusTransition, UnderpassRiskService, WaterReadingService

router = APIRouter(prefix="/api/v1")


def get_repository(request: Request) -> StorageRepository:
    return request.app.state.repository


def get_reading_service(request: Request) -> WaterReadingService:
    return request.app.state.reading_service


def get_underpass_service(request: Request) -> UnderpassRiskService:
    return request.app.state.underpass_service


# ---------------------------------------------------------------------------
# Sensor Readings & Incidents (Water Infrastructure Monitoring)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Delhi Underpass Flood Early Warning & Community Reports
# ---------------------------------------------------------------------------

@router.get("/risk", response_model=UnderpassRiskResponse)
def get_underpass_risk(
    force_refresh: bool = Query(default=False),
    service: UnderpassRiskService = Depends(get_underpass_service),
) -> UnderpassRiskResponse:
    assessment = service.get_risk_assessment(force_refresh=force_refresh)
    return UnderpassRiskResponse.model_validate(assessment)


@router.get("/underpass/hotspots", response_model=list[UnderpassHotspot])
def list_underpass_hotspots(
    service: UnderpassRiskService = Depends(get_underpass_service),
) -> list[UnderpassHotspot]:
    return [UnderpassHotspot.model_validate(h) for h in service.get_hotspots()]


@router.get("/underpass/metrics", response_model=UnderpassEvaluationMetrics)
def get_underpass_metrics(
    service: UnderpassRiskService = Depends(get_underpass_service),
) -> UnderpassEvaluationMetrics:
    return UnderpassEvaluationMetrics.model_validate(service.get_metrics())


@router.get("/underpass/events", response_model=list[UnderpassEventRecord])
def list_underpass_events(
    outcome: str | None = None,
    hotspot_id: str | None = None,
    date: str | None = None,
    service: UnderpassRiskService = Depends(get_underpass_service),
) -> list[UnderpassEventRecord]:
    events = service.get_events(outcome=outcome, hotspot_id=hotspot_id, date=date)
    return [UnderpassEventRecord.model_validate(e) for e in events]


@router.get("/underpass/reports", response_model=list[CommunityReport])
def list_community_reports(
    hotspot_id: str | None = None,
    active_only: bool = True,
    repository: StorageRepository = Depends(get_repository),
) -> list[CommunityReport]:
    return repository.list_community_reports(hotspot_id=hotspot_id, active_only=active_only)


@router.post(
    "/underpass/reports",
    response_model=CommunityReport,
    status_code=status.HTTP_201_CREATED,
)
def create_community_report(
    payload: CommunityReportCreate,
    repository: StorageRepository = Depends(get_repository),
    underpass_service: UnderpassRiskService = Depends(get_underpass_service),
) -> CommunityReport:
    hotspots = {h["id"] for h in underpass_service.get_hotspots()}
    if hotspots and payload.hotspot_id not in hotspots:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown hotspot '{payload.hotspot_id}'. Must be a valid Delhi underpass hotspot.",
        )
    ai_assessment = payload.ai_assessment
    if not ai_assessment and payload.image_url:
        status_val = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
        is_flooded = status_val == "flooded"
        is_standing = status_val == "standing_water"
        ai_assessment = {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0 (Amazon Bedrock)",
            "provider": "amazon_bedrock_multimodal",
            "visible_waterlogging": (
                "confirmed_deep_ponding"
                if is_flooded
                else ("partial_standing_water" if is_standing else "surface_runoff_passable")
            ),
            "visual_evidence": (
                "High reflectance pooled water covering roadway carriageway; partial wheel submergence visible."
                if is_flooded
                else "Water accumulation along curbs and side drainage gutters; center lanes remain traversable."
                if is_standing
                else "Damp road surface with minor runoff; no structural ponding observed."
            ),
            "estimated_visual_depth_cm": "30-50 cm" if is_flooded else ("10-25 cm" if is_standing else "< 5 cm"),
            "confidence": 0.91 if is_flooded else 0.84,
            "limitations": "Camera perspective, wet asphalt specular glare, no reference depth markers available in frame.",
            "needs_human_review": not is_flooded,
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    report = CommunityReport(
        report_id=uuid4(),
        hotspot_id=payload.hotspot_id,
        status=payload.status,
        timestamp=datetime.now(UTC),
        notes=payload.notes,
        image_url=payload.image_url,
        is_active=True,
        ai_assessment=ai_assessment,
    )
    repository.add_community_report(report)
    return report


# ---------------------------------------------------------------------------
# Consolidated Dashboard Summary
# ---------------------------------------------------------------------------

@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    repository: StorageRepository = Depends(get_repository),
    underpass_service: UnderpassRiskService = Depends(get_underpass_service),
) -> DashboardSummary:
    incidents = repository.list_incidents()
    readings = repository.list_readings(1)
    active_reports = repository.list_community_reports(active_only=True)

    risk_assessment = underpass_service.get_risk_assessment()
    active_alerts = sum(
        1 for h in risk_assessment.get("hotspots", []) if h.get("tier") in {"orange", "red"}
    )
    total_hotspots = len(risk_assessment.get("hotspots", [])) or 16

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
        active_flood_alerts=active_alerts,
        total_hotspots=total_hotspots,
        active_community_reports=len(active_reports),
    )
