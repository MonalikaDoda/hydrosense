from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:5173"
    storage_backend: Literal["json", "dynamodb"] = "json"
    storage_path: Path = Path("data/hydrosense.json")
    aws_region: str = "ap-south-1"
    dynamodb_readings_table: str = "hydrosense-readings-dev"
    dynamodb_incidents_table: str = "hydrosense-incidents-dev"
    dynamodb_reports_table: str = "hydrosense-reports-dev"
    water_alert_threshold_cm: float = 24
    alert_cooldown_seconds: int = 300
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
