# HydroSense API Contract

Base path for application endpoints: `/api/v1`. System health remains at `/health`. JSON field names use `snake_case`; timestamps are timezone-aware ISO-8601 values and producers should send UTC with `Z`.

The backend Pydantic models in `backend/app/schemas/contracts.py` are the validation source of truth. Frontend interfaces in `frontend/src/types/api.ts` mirror their serialized JSON.

## Shared enums

- Source: `esp32`, `simulated_sensor`, `simulated_leak`, `public_dataset`, `operator_report`, `community_report`, `forecast`
- Incident status: `open`, `assigned`, `verified`, `resolved`, `dismissed`
- Severity: `low`, `moderate`, `high`, `very_high`
- Hazard type: `high_water_level`, `flood_risk`, `suspected_leak`
- Underpass Risk Tier: `green`, `yellow`, `orange`, `red`, `unknown`
- Community Report Status: `flooded`, `passable`, `not_flooded`

## Sensor reading

```json
{
  "device_id": "hydrosense-demo-01",
  "location_id": "demo-zone-01",
  "water_depth_cm": 22.0,
  "distance_cm": 8.0,
  "timestamp": "2026-10-10T10:30:00Z",
  "source": "simulated_sensor"
}
```

Depth and distance must be non-negative. Source must be `esp32` or `simulated_sensor`.

## Incident

```json
{
  "incident_id": "cc064ff5-bf2e-42b2-96c8-e6be75fc1f44",
  "hazard_type": "high_water_level",
  "title": "Prototype water level threshold crossed",
  "location_id": "demo-zone-01",
  "latitude": 28.6139,
  "longitude": 77.209,
  "severity": "high",
  "confidence": 0.9,
  "status": "open",
  "source": "simulated_sensor",
  "evidence": {"water_depth_cm": 25.0, "threshold_cm": 24.0},
  "created_at": "2026-10-10T10:30:00Z",
  "updated_at": "2026-10-10T10:30:00Z"
}
```

## Community Flood Report

```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "hotspot_id": "zakhira",
  "status": "flooded",
  "timestamp": "2026-10-10T11:00:00Z",
  "notes": "Underpass submerged near railway line, traffic halted",
  "image_url": null,
  "is_active": true,
  "source": "community_report"
}
```

Reports remain active for 45 minutes; expired reports are filtered immediately by the backend API.
The request contract does not accept AI assessment fields. `ai_assessment` is nullable in stored responses and remains empty unless a future server-side integration performs and validates a real model invocation.

## Underpass Risk Forecast

```json
{
  "generated_at": "2026-10-10T11:00:00+05:30",
  "forecast_model_used": "ecmwf_ifs",
  "lookahead_hours": 24,
  "disclaimer": "Prototype. Estimated risk, not an official warning.",
  "credit": "Weather data by Open-Meteo.com",
  "hotspots": [
    {
      "id": "zakhira",
      "name": "Zakhira underpass",
      "lat": 28.66,
      "lon": 77.143,
      "tier": "green",
      "ratio": 0.12,
      "limit": {"rain1h_mm": 2.2, "rain3h_mm": 4.4},
      "limit_is_own": true,
      "evidence": "based on 13 recorded floods",
      "why": "Forecast rain for next 24 h is well below limit.",
      "forecast": {"max_1h_mm": 0.0, "max_3h_mm": 0.0, "window_start": null, "window_end": null}
    }
  ]
}
```

## Endpoint agreement

| Method | Path | Request | Response | Description |
|---|---|---|---|---|
| `GET` | `/health` | None | `HealthResponse` | System health check |
| `GET` | `/api/v1/dashboard/summary` | None | `DashboardSummary` | Aggregate telemetry, open incidents, flood alerts |
| `GET` | `/api/v1/readings/latest` | `limit` (1-100) | `SensorReading[]` | Historical ultrasonic sensor readings |
| `POST` | `/api/v1/readings` | `SensorReading` | `SensorReading`, `201` | Ingest new sensor telemetry |
| `GET` | `/api/v1/incidents` | Optional `hazard_type`, `status` | `Incident[]` | List water incidents |
| `GET` | `/api/v1/incidents/{incident_id}` | None | `Incident` | Get single incident |
| `PATCH` | `/api/v1/incidents/{incident_id}` | `IncidentStatusUpdate` | `Incident` | Transition incident lifecycle |
| `GET` | `/api/v1/risk` | Optional `force_refresh` | `UnderpassRiskResponse` | Underpass flood risk when the reviewed dataset is installed |
| `GET` | `/api/v1/underpass/hotspots` | None | `UnderpassHotspot[]` | Installed underpass metadata |
| `GET` | `/api/v1/underpass/metrics` | None | `UnderpassEvaluationMetrics` | Evaluation metrics supplied by the installed dataset |
| `GET` | `/api/v1/underpass/events` | Optional `outcome`, `hotspot_id`, `date` | `UnderpassEventRecord[]` | Reviewed historical events supplied by the installed dataset |
| `GET` | `/api/v1/underpass/reports` | Optional `hotspot_id`, `active_only` | `CommunityReport[]` | Active ground community observations (45m freshness) |
| `POST` | `/api/v1/underpass/reports` | `CommunityReportCreate` | `CommunityReport`, `201` | Submit community observation |

The risk, hotspot, metric, and event endpoints return HTTP `503` when their required dataset files are not installed. The frontend displays that state explicitly and does not substitute mock risk, event, or evaluation data.

## Local persistence

HydroSense uses a JSON-file repository at `backend/data/hydrosense.json` for local persistence (readings, incidents, community reports). The domain services depend on a `StorageRepository` protocol, allowing a DynamoDB adapter to replace local storage without modifying business logic.
