from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.repositories import JsonFileRepository, StorageRepository
from app.schemas import HealthResponse
from app.services import UnderpassRiskService, WaterReadingService


def create_app(
    repository: StorageRepository | None = None,
    underpass_service: UnderpassRiskService | None = None,
) -> FastAPI:
    settings = get_settings()
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
    application.state.repository = repository or JsonFileRepository(settings.storage_path)
    application.state.reading_service = WaterReadingService(
        application.state.repository, settings
    )
    application.state.underpass_service = (
        underpass_service or UnderpassRiskService(settings)
    )
    application.include_router(router)

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok", service="hydrosense-api", version=application.version
        )

    return application


app = create_app()
