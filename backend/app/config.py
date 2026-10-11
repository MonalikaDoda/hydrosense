from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:5173"
    storage_backend: Literal["json", "dynamodb"] = "json"
    storage_path: Path = Path("data/hydrosense.json")
    aws_region: str = "ap-south-1"
    dynamodb_readings_table: str = "hydrosense-readings-dev"
    dynamodb_incidents_table: str = "hydrosense-incidents-dev"
    dynamodb_reports_table: str = "hydrosense-reports-dev"
    dynamodb_max_scan_items: int = Field(default=1000, ge=1, le=10_000)
    water_alert_threshold_cm: float = Field(default=24, ge=0, le=1000)
    alert_cooldown_seconds: int = Field(default=300, ge=0, le=86_400)
    max_reading_age_seconds: int = Field(default=900, ge=0, le=86_400)
    max_reading_future_skew_seconds: int = Field(default=600, ge=0, le=3600)
    forecast_request_timeout_seconds: float = Field(default=3, gt=0, le=5)
    forecast_cache_seconds: int = Field(default=600, ge=0, le=3600)
    forecast_stale_cache_seconds: int = Field(default=1800, ge=0, le=86_400)
    underpass_data_dir: Path | None = None
    demo_latitude: float = 28.6139
    demo_longitude: float = 77.2090

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
