import type {
  CommunityReport,
  CommunityReportCreate,
  DashboardSummary,
  HealthResponse,
  Incident,
  IncidentStatus,
  SensorReading,
  UnderpassEvaluationMetrics,
  UnderpassEventRecord,
  UnderpassHotspot,
  UnderpassRiskResponse,
} from "../types/api";
import {
  MOCK_COMMUNITY_REPORTS,
  MOCK_EVENTS,
  MOCK_HOTSPOTS_RISK,
  MOCK_INCIDENTS,
  MOCK_METRICS,
  MOCK_READINGS,
  MOCK_SUMMARY,
} from "./mockData";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);

  if (!response.ok) {
    let detail = `API request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        detail = errorJson.detail;
      }
    } catch {
      // fallback
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  try {
    return await request<HealthResponse>("/health", { signal });
  } catch {
    return { status: "offline_demo", service: "hydrosense-api", version: "0.2.0" };
  }
}

export async function getDashboardSummary(signal?: AbortSignal): Promise<DashboardSummary> {
  try {
    return await request<DashboardSummary>("/api/v1/dashboard/summary", { signal });
  } catch (err) {
    console.warn("Using demo summary fallback:", err);
    return MOCK_SUMMARY;
  }
}

export async function getLatestReadings(signal?: AbortSignal): Promise<SensorReading[]> {
  try {
    return await request<SensorReading[]>("/api/v1/readings/latest?limit=8", { signal });
  } catch (err) {
    console.warn("Using demo readings fallback:", err);
    return MOCK_READINGS;
  }
}

export async function createReading(reading: SensorReading): Promise<SensorReading> {
  try {
    return await request<SensorReading>("/api/v1/readings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reading),
    });
  } catch (err) {
    console.warn("Offline reading injection fallback:", err);
    return reading;
  }
}

export async function getIncidents(signal?: AbortSignal): Promise<Incident[]> {
  try {
    return await request<Incident[]>("/api/v1/incidents", { signal });
  } catch (err) {
    console.warn("Using demo incidents fallback:", err);
    return MOCK_INCIDENTS;
  }
}

export async function updateIncidentStatus(
  incidentId: string,
  status: IncidentStatus,
): Promise<Incident> {
  try {
    return await request<Incident>(`/api/v1/incidents/${incidentId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  } catch (err) {
    console.warn("Offline status update fallback:", err);
    const existing = MOCK_INCIDENTS.find((i) => i.incident_id === incidentId) ?? MOCK_INCIDENTS[0];
    return { ...existing, status, updated_at: new Date().toISOString() };
  }
}

export async function getUnderpassRisk(
  signal?: AbortSignal,
  forceRefresh: boolean = false,
): Promise<UnderpassRiskResponse> {
  const query = forceRefresh ? "?force_refresh=true" : "";
  try {
    return await request<UnderpassRiskResponse>(`/api/v1/risk${query}`, { signal });
  } catch (err) {
    console.warn("Using demo underpass risk fallback:", err);
    return MOCK_HOTSPOTS_RISK;
  }
}

export async function getUnderpassHotspots(signal?: AbortSignal): Promise<UnderpassHotspot[]> {
  try {
    return await request<UnderpassHotspot[]>("/api/v1/underpass/hotspots", { signal });
  } catch (err) {
    console.warn("Using demo hotspots fallback:", err);
    return MOCK_HOTSPOTS_RISK.hotspots.map((h) => ({
      id: h.id,
      name: h.name,
      lat: h.lat,
      lon: h.lon,
      coord_status: "approximate",
    }));
  }
}

export async function getUnderpassMetrics(
  signal?: AbortSignal,
): Promise<UnderpassEvaluationMetrics> {
  try {
    return await request<UnderpassEvaluationMetrics>("/api/v1/underpass/metrics", { signal });
  } catch (err) {
    console.warn("Using demo metrics fallback:", err);
    return MOCK_METRICS;
  }
}

export async function getUnderpassEvents(
  params?: { outcome?: string; hotspot_id?: string; date?: string },
  signal?: AbortSignal,
): Promise<UnderpassEventRecord[]> {
  const search = new URLSearchParams();
  if (params?.outcome) search.set("outcome", params.outcome);
  if (params?.hotspot_id) search.set("hotspot_id", params.hotspot_id);
  if (params?.date) search.set("date", params.date);
  const query = search.toString() ? `?${search.toString()}` : "";
  try {
    return await request<UnderpassEventRecord[]>(`/api/v1/underpass/events${query}`, { signal });
  } catch (err) {
    console.warn("Using demo events fallback:", err);
    return MOCK_EVENTS;
  }
}

export async function getCommunityReports(
  hotspotId?: string,
  signal?: AbortSignal,
): Promise<CommunityReport[]> {
  const query = hotspotId ? `?hotspot_id=${encodeURIComponent(hotspotId)}` : "";
  try {
    return await request<CommunityReport[]>(`/api/v1/underpass/reports${query}`, { signal });
  } catch (err) {
    console.warn("Using demo community reports fallback:", err);
    return hotspotId ? MOCK_COMMUNITY_REPORTS.filter((r) => r.hotspot_id === hotspotId) : MOCK_COMMUNITY_REPORTS;
  }
}

export async function submitCommunityReport(
  payload: CommunityReportCreate,
): Promise<CommunityReport> {
  try {
    return await request<CommunityReport>("/api/v1/underpass/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("Offline report creation fallback:", err);
    const isFlooded = payload.status === "flooded";
    const isStanding = payload.status === "passable";
    const aiAssessment = payload.image_url
      ? {
          model_id: "anthropic.claude-3-haiku-20240307-v1:0 (Amazon Bedrock)",
          provider: "amazon_bedrock_multimodal",
          visible_waterlogging: isFlooded
            ? "confirmed_deep_ponding"
            : isStanding
            ? "partial_standing_water"
            : "surface_runoff_passable",
          visual_evidence: isFlooded
            ? "High reflectance pooled water covering roadway carriageway; partial wheel submergence visible."
            : isStanding
            ? "Water accumulation along curbs and side drainage gutters; center lanes remain traversable."
            : "Damp road surface with minor runoff; no structural ponding observed.",
          estimated_visual_depth_cm: isFlooded ? "30-50 cm" : isStanding ? "12-25 cm" : "< 5 cm",
          confidence: isFlooded ? 0.93 : 0.86,
          limitations: "Camera perspective, wet asphalt specular glare, vehicle spray.",
          needs_human_review: !isFlooded,
          analyzed_at: new Date().toISOString(),
        }
      : null;

    const newReport: CommunityReport = {
      report_id: "demo-" + Date.now(),
      hotspot_id: payload.hotspot_id,
      status: payload.status,
      timestamp: new Date().toISOString(),
      notes: payload.notes,
      image_url: payload.image_url,
      is_active: true,
      source: "community_report",
      ai_assessment: aiAssessment,
    };
    MOCK_COMMUNITY_REPORTS.unshift(newReport);
    return newReport;
  }
}
