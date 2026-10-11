from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import Settings, get_settings
from app.repositories import DynamoDbRepository, JsonFileRepository, StorageRepository
from app.schemas import HealthResponse, ReadinessResponse
from app.services import (
    BedrockAssessmentService,
    EvidenceStorageService,
    UnderpassRiskService,
    WaterReadingService,
)


def create_repository(settings: Settings) -> StorageRepository:
    if settings.storage_backend == "dynamodb":
        return DynamoDbRepository(
            readings_table_name=settings.dynamodb_readings_table,
            incidents_table_name=settings.dynamodb_incidents_table,
            reports_table_name=settings.dynamodb_reports_table,
            region_name=settings.aws_region,
            max_scan_items=settings.dynamodb_max_scan_items,
        )
    return JsonFileRepository(settings.storage_path)


def create_app(
    repository: StorageRepository | None = None,
    underpass_service: UnderpassRiskService | None = None,
    settings: Settings | None = None,
    evidence_service: EvidenceStorageService | None = None,
    assessment_service: BedrockAssessmentService | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title="HydroSense API",
        version="0.2.0",
        description="Water-risk intelligence and urban flood decision-support platform.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(
            {settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"}
        ),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    application.state.repository = repository or create_repository(settings)
    application.state.reading_service = WaterReadingService(
        application.state.repository, settings
    )
    application.state.underpass_service = (
        underpass_service
        or UnderpassRiskService(settings, data_dir=settings.underpass_data_dir)
    )
    application.state.evidence_service = evidence_service or EvidenceStorageService(settings)
    application.state.assessment_service = assessment_service or BedrockAssessmentService(settings)
    application.include_router(router)

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok", service="hydrosense-api", version=application.version
        )

    @application.get("/ready", response_model=ReadinessResponse, tags=["system"])
    def readiness() -> ReadinessResponse:
        try:
            application.state.repository.check_health()
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Persistent storage is unavailable.",
            ) from error
        return ReadinessResponse(
            status="ready",
            storage="available",
            underpass_dataset=(
                "available" if application.state.underpass_service.is_available else "unavailable"
            ),
        )

    return application


app = create_app()
