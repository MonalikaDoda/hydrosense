export type SourceLabel =
  | "esp32"
  | "arduino"
  | "simulated_sensor"
  | "simulated_leak"
  | "public_dataset"
  | "operator_report"
  | "community_report"
  | "forecast";

export type IncidentStatus =
  | "open"
  | "assigned"
  | "verified"
  | "resolved"
  | "dismissed";

export type Severity = "low" | "moderate" | "high" | "very_high";

export type HazardType =
  | "high_water_level"
  | "flood_risk"
  | "suspected_leak";

export type RiskTier = "green" | "yellow" | "orange" | "red" | "unknown";

export type CommunityReportStatus = "flooded" | "passable" | "not_flooded";

export interface SensorReading {
  device_id: string;
  location_id: string;
  water_depth_cm: number;
  distance_cm: number;
  timestamp: string;
  source: "esp32" | "arduino" | "simulated_sensor";
}

export interface LeakMeasurement {
  location_id: string;
  pressure_kpa: number;
  flow_lpm: number;
  timestamp: string;
  source: "simulated_leak";
}

export interface Incident {
  incident_id: string;
  hazard_type: HazardType;
  title: string;
  location_id: string;
  latitude: number;
  longitude: number;
  severity: Severity;
  confidence: number;
  status: IncidentStatus;
  source: SourceLabel;
  evidence: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IncidentStatusUpdate {
  status: IncidentStatus;
}

export interface DashboardSummary {
  total_incidents: number;
  open_incidents: number;
  high_priority_incidents: number;
  incidents_by_hazard: Partial<Record<HazardType, number>>;
  incidents_by_status: Partial<Record<IncidentStatus, number>>;
  latest_reading_at: string | null;
  generated_at: string;
  active_flood_alerts?: number | null;
  total_hotspots?: number;
  active_community_reports?: number;
  underpass_dataset: "available" | "unavailable";
  flood_risk_status: "known" | "unknown";
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface UnderpassHotspot {
  id: string;
  name: string;
  lat: number;
  lon: number;
  coord_status?: string;
  fix_dates?: string[];
  bypass?: string | null;
}

export interface UnderpassRiskItem {
  id: string;
  name: string;
  lat: number;
  lon: number;
  tier: RiskTier;
  ratio: number | null;
  limit: {
    rain1h_mm?: number | null;
    rain3h_mm?: number | null;
  };
  limit_is_own: boolean;
  evidence: string;
  note: string;
  forecast: {
    max_1h_mm: number | null;
    max_3h_mm: number | null;
    window_start: string | null;
    window_end: string | null;
  };
  history: {
    recorded_floods: number;
    floods_with_at_least_this_rain_3h: number;
  } | null;
  why: string;
}

export interface UnderpassRiskResponse {
  generated_at: string;
  forecast_model_used: string;
  forecast_status: "live" | "cached" | "stale" | "unavailable";
  forecast_age_seconds: number | null;
  lookahead_hours: number;
  disclaimer: string;
  credit: string;
  hotspots: UnderpassRiskItem[];
}

export interface CommunityReportCreate {
  report_id: string;
  hotspot_id: string;
  latitude: number;
  longitude: number;
  status: CommunityReportStatus;
  notes?: string | null;
}

export interface CommunityReport {
  report_id: string;
  hotspot_id: string;
  latitude?: number | null;
  longitude?: number | null;
  status: CommunityReportStatus;
  timestamp: string;
  notes?: string | null;
  image_url?: string | null;
  image_key?: string | null;
  assessment_status: "not_requested" | "pending" | "completed" | "failed";
  is_active: boolean;
  source: SourceLabel;
  ai_assessment?: ImageAssessment | { error: string } | null;
}

export interface ImageAssessment {
  model_id: string;
  assessed_at: string;
  summary: string;
  disclaimer: string;
}

export interface ImageUploadUrlResponse {
  upload_url: string;
  fields: Record<string, string>;
  image_key: string;
  max_bytes: number;
}

export interface UnderpassEvaluationMetrics {
  n_rows: number;
  n_storm_days: number;
  per_hotspot_thresholds: {
    floods_caught: number;
    floods_missed: number;
    false_alarms: number;
    correct_clear: number;
    n_flooded_rows: number;
    n_clear_rows: number;
  };
  pooled_only_baseline: {
    floods_caught: number;
    floods_missed: number;
    false_alarms: number;
    correct_clear: number;
    n_flooded_rows: number;
    n_clear_rows: number;
  };
  per_storm_day: Array<{
    date: string;
    floods_caught: number;
    floods_missed: number;
    false_alarms: number;
    correct_clear: number;
    n_flooded_rows: number;
    n_clear_rows: number;
  }>;
  notes: string[];
}

export interface UnderpassEventRecord {
  event_id: string;
  date: string;
  hotspot_id: string;
  underpass_name_in_source: string;
  outcome: "flooded" | "clear";
  what_happened: string;
  time_text?: string | null;
  time_confidence?: string | null;
  rain_reported_in_article?: string | null;
  notes?: string | null;
  source_url?: string | null;
  source_publisher?: string | null;
}
