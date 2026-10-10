import type {
  DashboardSummary,
  HealthResponse,
  Incident,
  IncidentStatus,
  SensorReading,
} from "../types/api";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { signal });
}

export async function getDashboardSummary(signal?: AbortSignal) {
  return request<DashboardSummary>("/api/v1/dashboard/summary", { signal });
}

export async function getLatestReadings(signal?: AbortSignal) {
  return request<SensorReading[]>("/api/v1/readings/latest?limit=8", { signal });
}

export async function getIncidents(signal?: AbortSignal) {
  return request<Incident[]>("/api/v1/incidents", { signal });
}

export async function updateIncidentStatus(incidentId: string, status: IncidentStatus) {
  return request<Incident>(`/api/v1/incidents/${incidentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}
