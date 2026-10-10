from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceLabel(StrEnum):
    ESP32 = "esp32"
    ARDUINO = "arduino"
    SIMULATED_SENSOR = "simulated_sensor"
    SIMULATED_LEAK = "simulated_leak"
    PUBLIC_DATASET = "public_dataset"
    OPERATOR_REPORT = "operator_report"
    COMMUNITY_REPORT = "community_report"
    FORECAST = "forecast"


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


class RiskTier(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    UNKNOWN = "unknown"


class CommunityReportStatus(StrEnum):
    FLOODED = "flooded"
    PASSABLE = "passable"
    NOT_FLOODED = "not_flooded"


class SensorReading(ContractModel):
    device_id: str = Field(min_length=1, max_length=100)
    location_id: str = Field(min_length=1, max_length=100)
    water_depth_cm: float = Field(ge=0)
    distance_cm: float = Field(ge=0)
    timestamp: AwareDatetime
    source: SourceLabel

    @model_validator(mode="after")
    def require_sensor_source(self) -> "SensorReading":
        if self.source not in {SourceLabel.ESP32, SourceLabel.ARDUINO, SourceLabel.SIMULATED_SENSOR}:
            raise ValueError("sensor reading source must be arduino, esp32 or simulated_sensor")
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
    active_flood_alerts: int = Field(default=0, ge=0)
    total_hotspots: int = Field(default=16, ge=0)
    active_community_reports: int = Field(default=0, ge=0)


class HealthResponse(ContractModel):
    status: str
    service: str
    version: str


class UnderpassHotspot(ContractModel):
    id: str
    name: str
    lat: float
    lon: float
    coord_status: str = "approximate"
    fix_dates: list[str] = Field(default_factory=list)
    bypass: str | None = None


class ForecastWindow(ContractModel):
    max_1h_mm: float | None = None
    max_3h_mm: float | None = None
    window_start: str | None = None
    window_end: str | None = None


class UnderpassRiskItem(ContractModel):
    id: str
    name: str
    lat: float
    lon: float
    tier: RiskTier
    ratio: float | None = None
    limit: dict[str, float | None] = Field(default_factory=dict)
    limit_is_own: bool = False
    evidence: str = ""
    note: str = ""
    forecast: ForecastWindow
    history: dict[str, Any] | None = None
    why: str = ""


class UnderpassRiskResponse(ContractModel):
    generated_at: str
    forecast_model_used: str
    lookahead_hours: int
    disclaimer: str
    credit: str
    hotspots: list[UnderpassRiskItem]


class CommunityReportCreate(ContractModel):
    hotspot_id: str = Field(min_length=1, max_length=100)
    status: CommunityReportStatus
    notes: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=5_000_000)
    ai_assessment: dict[str, Any] | None = None


class CommunityReport(ContractModel):
    report_id: UUID
    hotspot_id: str
    status: CommunityReportStatus
    timestamp: AwareDatetime
    notes: str | None = None
    image_url: str | None = None
    is_active: bool = True
    source: SourceLabel = SourceLabel.COMMUNITY_REPORT
    ai_assessment: dict[str, Any] | None = None


class UnderpassEvaluationMetrics(ContractModel):
    n_rows: int
    n_storm_days: int
    per_hotspot_thresholds: dict[str, Any]
    pooled_only_baseline: dict[str, Any]
    per_storm_day: list[dict[str, Any]]
    notes: list[str]


class UnderpassEventRecord(ContractModel):
    event_id: str
    date: str
    hotspot_id: str
    underpass_name_in_source: str
    outcome: str
    what_happened: str
    time_text: str | None = None
    time_confidence: str | None = None
    rain_reported_in_article: str | None = None
    notes: str | None = None
    source_url: str | None = None
    source_publisher: str | None = None
