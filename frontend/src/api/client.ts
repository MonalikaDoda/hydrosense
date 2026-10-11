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
import { authConfigured, getAccessToken } from "../auth";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
if (!configuredApiBaseUrl && import.meta.env.PROD) {
  throw new Error("VITE_API_BASE_URL is required for production builds");
}
const apiBaseUrl = configuredApiBaseUrl ?? "http://127.0.0.1:8000";

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

async function mutationRequest<T>(path: string, init: RequestInit): Promise<T> {
  const accessToken = await getAccessToken();
  if (authConfigured && !accessToken) {
    throw new Error("Sign in is required for this action.");
  }
  const headers = new Headers(init.headers);
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return request<T>(path, { ...init, headers });
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { signal });
}

export async function getDashboardSummary(signal?: AbortSignal): Promise<DashboardSummary> {
  return request<DashboardSummary>("/api/v1/dashboard/summary", { signal });
}

export async function getLatestReadings(signal?: AbortSignal): Promise<SensorReading[]> {
  return request<SensorReading[]>("/api/v1/readings/latest?limit=8", { signal });
}

export async function createReading(reading: SensorReading): Promise<SensorReading> {
  return mutationRequest<SensorReading>("/api/v1/readings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reading),
  });
}

export async function getIncidents(signal?: AbortSignal): Promise<Incident[]> {
  return request<Incident[]>("/api/v1/incidents", { signal });
}

export async function updateIncidentStatus(
  incidentId: string,
  status: IncidentStatus,
): Promise<Incident> {
  return mutationRequest<Incident>(`/api/v1/incidents/${incidentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export async function getUnderpassRisk(
  signal?: AbortSignal,
  forceRefresh: boolean = false,
): Promise<UnderpassRiskResponse> {
  const query = forceRefresh ? "?force_refresh=true" : "";
  return request<UnderpassRiskResponse>(`/api/v1/risk${query}`, { signal });
}

export async function getUnderpassHotspots(signal?: AbortSignal): Promise<UnderpassHotspot[]> {
  return request<UnderpassHotspot[]>("/api/v1/underpass/hotspots", { signal });
}

export async function getUnderpassMetrics(
  signal?: AbortSignal,
): Promise<UnderpassEvaluationMetrics> {
  return request<UnderpassEvaluationMetrics>("/api/v1/underpass/metrics", { signal });
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
  return request<UnderpassEventRecord[]>(`/api/v1/underpass/events${query}`, { signal });
}

export async function getCommunityReports(
  hotspotId?: string,
  signal?: AbortSignal,
): Promise<CommunityReport[]> {
  const query = hotspotId ? `?hotspot_id=${encodeURIComponent(hotspotId)}` : "";
  return request<CommunityReport[]>(`/api/v1/underpass/reports${query}`, { signal });
}

export async function submitCommunityReport(
  payload: CommunityReportCreate,
): Promise<CommunityReport> {
  return mutationRequest<CommunityReport>("/api/v1/underpass/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
