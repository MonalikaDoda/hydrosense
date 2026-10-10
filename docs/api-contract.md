# HydroSense API Contract

Base path for application endpoints: `/api/v1`. System health remains at `/health`. JSON field names use `snake_case`; timestamps are timezone-aware ISO-8601 values and producers should send UTC with `Z`.

The backend Pydantic models in `backend/app/schemas/contracts.py` are the validation source of truth. Frontend interfaces in `frontend/src/types/api.ts` mirror their serialized JSON.

## Shared enums

- Source: `esp32`, `simulated_sensor`, `simulated_leak`, `public_dataset`, `operator_report`
- Incident status: `open`, `assigned`, `verified`, `resolved`, `dismissed`
- Severity: `low`, `moderate`, `high`, `very_high`
- Hazard type: `high_water_level`, `flood_risk`, `suspected_leak`

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

## Leak measurement

```json
{
  "location_id": "demo-supply-zone-01",
  "pressure_kpa": 180.0,
  "flow_lpm": 42.0,
  "timestamp": "2026-10-10T10:30:00Z",
  "source": "simulated_leak"
}
```

Pressure and flow must be non-negative. Sprint 0 permits only the clearly synthetic `simulated_leak` source.

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

Confidence is in the inclusive range 0-1. Coordinates use WGS84 decimal degrees. Evidence is hazard-specific JSON.

## Dashboard summary

```json
{
  "total_incidents": 3,
  "open_incidents": 2,
  "high_priority_incidents": 1,
  "incidents_by_hazard": {"high_water_level": 1, "suspected_leak": 2},
  "incidents_by_status": {"open": 2, "verified": 1},
  "latest_reading_at": "2026-10-10T10:30:00Z",
  "generated_at": "2026-10-10T10:31:00Z"
}
```

## Endpoint agreement

| Method | Path | Request | Response | Sprint |
|---|---|---|---|---|
| `GET` | `/health` | None | `HealthResponse` | Implemented in Sprint 0 |
| `GET` | `/api/v1/dashboard/summary` | None | `DashboardSummary` | Implemented in Sprint 1 |
| `GET` | `/api/v1/readings/latest` | `limit` from 1-100 | `SensorReading[]` | Implemented in Sprint 1 |
| `POST` | `/api/v1/readings` | `SensorReading` | `SensorReading`, `201` | Implemented in Sprint 1 |
| `POST` | `/api/v1/leak-measurements` | `LeakMeasurement` | Accepted measurement/result, `201` | Sprint 1 |
| `GET` | `/api/v1/incidents` | Optional `hazard_type`, `status` | `Incident[]` | Implemented in Sprint 1 |
| `GET` | `/api/v1/incidents/{incident_id}` | None | `Incident` | Implemented in Sprint 1 |
| `PATCH` | `/api/v1/incidents/{incident_id}` | `IncidentStatusUpdate` | `Incident` | Implemented in Sprint 1 |
| `POST` | `/api/v1/demo/trigger` | Demo scenario identifier | Created result | Sprint 2; demo mode only |

Errors will use FastAPI's validation format during development. A stable application error envelope will be agreed before public deployment. Unknown JSON fields are rejected by shared Pydantic request models.

## Local persistence

Sprint 1 uses a JSON-file repository at `backend/data/hydrosense.json` by default. The API and domain service depend on a `StorageRepository` protocol, allowing a DynamoDB adapter to replace the local repository without moving threshold or lifecycle logic. The local file is suitable for one development process only and is not production storage.
