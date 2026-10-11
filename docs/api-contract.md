# HydroSense API Contract

Base path for application endpoints: `/api/v1`. Liveness is at `/health`; dependency readiness is at `/ready`. JSON field names use `snake_case`; timestamps are timezone-aware ISO-8601 values and producers should send UTC with `Z`.

The backend Pydantic models in `backend/app/schemas/contracts.py` are the validation source of truth. Frontend interfaces in `frontend/src/types/api.ts` mirror their serialized JSON.

## Shared enums

- Source: `esp32`, `arduino`, `simulated_sensor`, `simulated_leak`, `public_dataset`, `operator_report`, `community_report`, `forecast`
- Incident status: `open`, `assigned`, `verified`, `resolved`, `dismissed`
- Severity: `low`, `moderate`, `high`, `very_high`
- Hazard type: `high_water_level`, `flood_risk`, `suspected_leak`
- Underpass Risk Tier: `green`, `yellow`, `orange`, `red`, `unknown`
- Forecast status: `live`, `cached`, `stale`, `unavailable`
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

Depth and distance must be non-negative. Source must be `arduino`, `esp32`, or `simulated_sensor`. The server rejects readings older than the configured age limit or too far in the future.

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
  "latitude": 28.66,
  "longitude": 77.143,
  "status": "flooded",
  "timestamp": "2026-10-10T11:00:00Z",
  "notes": "Underpass submerged near railway line, traffic halted",
  "image_url": null,
  "is_active": true,
  "source": "community_report"
}
```

Creation requires a client-generated UUID plus coordinates. A retry with the same UUID and identical payload returns the existing report with HTTP 200; reusing that UUID for a different payload returns HTTP 409. Known installed hotspots are canonicalized to their dataset coordinates. Reports remain active for 45 minutes; expired reports are filtered immediately by the backend API.

The request contract accepts neither images nor AI assessment fields. `image_url` and `ai_assessment` are nullable legacy response fields and remain empty unless a future server-side upload and model integration is implemented and verified.

## Underpass Risk Forecast

```json
{
  "generated_at": "2026-10-10T11:00:00+05:30",
  "forecast_model_used": "ecmwf_ifs",
  "forecast_status": "live",
  "forecast_age_seconds": 0,
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

When forecast data is missing, incomplete, malformed, or older than the bounded stale-cache window, `forecast_status` is `unavailable`, rainfall maxima are `null`, and affected tiers are `unknown`. Missing hotspot thresholds also produce `unknown`; absence is never interpreted as zero rainfall or green risk.

## Endpoint agreement

| Method | Path | Request | Response | Description |
|---|---|---|---|---|
| `GET` | `/health` | None | `HealthResponse` | System health check |
| `GET` | `/ready` | None | `ReadinessResponse` | Storage readiness plus separate optional dataset availability |
| `GET` | `/api/v1/dashboard/summary` | None | `DashboardSummary` | Aggregate telemetry, open incidents, flood alerts |
| `GET` | `/api/v1/readings/latest` | `limit` (1-100) | `SensorReading[]` | Historical ultrasonic sensor readings |
| `POST` | `/api/v1/readings` | `SensorReading` | `SensorReading`, `201` | Ingest new sensor telemetry; JWT required when hosted |
| `GET` | `/api/v1/incidents` | Optional `hazard_type`, `status` | `Incident[]` | List water incidents |
| `GET` | `/api/v1/incidents/{incident_id}` | None | `Incident` | Get single incident |
| `PATCH` | `/api/v1/incidents/{incident_id}` | `IncidentStatusUpdate` | `Incident` | Transition incident lifecycle; JWT required when hosted |
| `GET` | `/api/v1/risk` | Optional `force_refresh` | `UnderpassRiskResponse` | Underpass flood risk when the reviewed dataset is installed |
| `GET` | `/api/v1/underpass/hotspots` | None | `UnderpassHotspot[]` | Installed underpass metadata |
| `GET` | `/api/v1/underpass/metrics` | None | `UnderpassEvaluationMetrics` | Evaluation metrics supplied by the installed dataset |
| `GET` | `/api/v1/underpass/events` | Optional `outcome`, `hotspot_id`, `date` | `UnderpassEventRecord[]` | Reviewed historical events supplied by the installed dataset |
| `GET` | `/api/v1/underpass/reports` | Optional `hotspot_id`, `active_only` | `CommunityReport[]` | Active ground community observations (45m freshness) |
| `POST` | `/api/v1/underpass/reports` | `CommunityReportCreate` | `CommunityReport`, `201` or `200` retry | Submit an idempotent community observation; JWT required when hosted |

The risk, hotspot, metric, and event endpoints return HTTP `503` when their required dataset files are not installed. The frontend displays that state explicitly and does not substitute mock risk, event, or evaluation data.

Dataset availability requires all four reviewed artifacts under `UNDERPASS_DATA_DIR`: `hotspots.json` with a `hotspots` array matching `UnderpassHotspot`, `thresholds.json` with `pooled` and optional `hotspots` objects, `metrics.json` matching `UnderpassEvaluationMetrics`, and a nonempty `events.csv` matching `UnderpassEventRecord`. Event outcomes are limited to `flooded` or `clear`; both metric summaries require all six nonnegative confusion-matrix/count fields. A malformed required artifact fails the module closed. Optional `features.csv` may supply historical flooded `rain3h_mm` values and does not determine availability.

`/health` is process liveness and intentionally does not contact dependencies. `/ready` returns HTTP 503 with a generic detail when persistent storage is unavailable. An absent optional underpass dataset does not make the core API unready; it is reported as `underpass_dataset: "unavailable"`.

`DashboardSummary.active_flood_alerts` is nullable. `underpass_dataset` and `flood_risk_status` make unavailable risk explicit rather than converting it to a numeric zero.

## Local persistence

HydroSense uses a JSON-file repository at `backend/data/hydrosense.json` for local persistence (readings, incidents, community reports). The domain services depend on a `StorageRepository` protocol, allowing a DynamoDB adapter to replace local storage without modifying business logic.
