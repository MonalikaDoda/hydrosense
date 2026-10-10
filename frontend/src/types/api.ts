export type SourceLabel =
  | "esp32"
  | "simulated_sensor"
  | "simulated_leak"
  | "public_dataset"
  | "operator_report";

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

export interface SensorReading {
  device_id: string;
  location_id: string;
  water_depth_cm: number;
  distance_cm: number;
  timestamp: string;
  source: "esp32" | "simulated_sensor";
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
  assignee?: string | null;
}

export interface DashboardSummary {
  total_incidents: number;
  open_incidents: number;
  high_priority_incidents: number;
  incidents_by_hazard: Partial<Record<HazardType, number>>;
  incidents_by_status: Partial<Record<IncidentStatus, number>>;
  latest_reading_at: string | null;
  generated_at: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}
