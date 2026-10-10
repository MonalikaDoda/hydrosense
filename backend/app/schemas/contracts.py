from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceLabel(StrEnum):
    ESP32 = "esp32"
    SIMULATED_SENSOR = "simulated_sensor"
    SIMULATED_LEAK = "simulated_leak"
    PUBLIC_DATASET = "public_dataset"
    OPERATOR_REPORT = "operator_report"


class IncidentStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    VERIFIED = "verified"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Severity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class HazardType(StrEnum):
    HIGH_WATER_LEVEL = "high_water_level"
    FLOOD_RISK = "flood_risk"
    SUSPECTED_LEAK = "suspected_leak"


class SensorReading(ContractModel):
    device_id: str = Field(min_length=1, max_length=100)
    location_id: str = Field(min_length=1, max_length=100)
    water_depth_cm: float = Field(ge=0)
    distance_cm: float = Field(ge=0)
    timestamp: AwareDatetime
    source: SourceLabel

    @model_validator(mode="after")
    def require_sensor_source(self) -> "SensorReading":
        if self.source not in {SourceLabel.ESP32, SourceLabel.SIMULATED_SENSOR}:
            raise ValueError("sensor reading source must be esp32 or simulated_sensor")
        return self


class LeakMeasurement(ContractModel):
    location_id: str = Field(min_length=1, max_length=100)
    pressure_kpa: float = Field(ge=0)
    flow_lpm: float = Field(ge=0)
    timestamp: AwareDatetime
    source: SourceLabel

    @model_validator(mode="after")
    def require_leak_source(self) -> "LeakMeasurement":
        if self.source != SourceLabel.SIMULATED_LEAK:
            raise ValueError("leak measurement source must be simulated_leak")
        return self


class Incident(ContractModel):
    incident_id: UUID
    hazard_type: HazardType
    title: str = Field(min_length=1, max_length=200)
    location_id: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    status: IncidentStatus
    source: SourceLabel
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: AwareDatetime
    updated_at: AwareDatetime


class IncidentStatusUpdate(ContractModel):
    status: IncidentStatus
    assignee: str | None = Field(default=None, min_length=1, max_length=100)


class DashboardSummary(ContractModel):
    total_incidents: int = Field(ge=0)
    open_incidents: int = Field(ge=0)
    high_priority_incidents: int = Field(ge=0)
    incidents_by_hazard: dict[HazardType, int]
    incidents_by_status: dict[IncidentStatus, int]
    latest_reading_at: AwareDatetime | None = None
    generated_at: AwareDatetime


class HealthResponse(ContractModel):
    status: str
    service: str
    version: str
