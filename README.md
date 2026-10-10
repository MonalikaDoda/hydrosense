# HydroSense

HydroSense is a Delhi-focused decision-support prototype for flood risk, simulated water-loss anomalies, and equity-aware incident prioritization. The current **Sprint 1 vertical slice** processes simulated water-level readings into locally persisted incidents and displays them in the dashboard.

Synthetic readings and demo locations must remain clearly labelled. The project does not claim citywide flood prediction, exact underground leak localization, or access to live municipal sensor data.

## Implemented vertical slice

- FastAPI reading ingestion, latest readings, incident list/detail, status updates, and dashboard summary
- Configurable 24 cm default threshold and five-minute duplicate suppression
- JSON-file local persistence behind a replaceable repository interface
- ESP32-compatible Python simulator
- Responsive React dashboard with live API data and loading, failure, and empty states
- Strict Pydantic v2 and matching TypeScript contracts

AWS, flood scoring, and leak anomaly processing are not implemented yet.

## Prerequisites

- Python 3.12+
- Node.js 20+ and npm

## Run the backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` or Swagger UI at `http://127.0.0.1:8000/docs`.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The backend must be running for its health indicator.

## Run the vertical slice

With backend and frontend running in separate terminals, send an above-threshold reading:

```powershell
py scripts\simulate_sensor.py --depth-cm 26
```

Refresh the dashboard to see the simulated reading and generated incident. Local records are stored in `backend/data/hydrosense.json` and excluded from Git. Set `STORAGE_PATH`, `WATER_ALERT_THRESHOLD_CM`, and `ALERT_COOLDOWN_SECONDS` in a local `.env` to override defaults.

## Run checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm run typecheck
npm run build
```

Configuration placeholders are documented in `.env.example`. Copy values into a local `.env`; never commit secrets, certificates, private keys, or real phone numbers.

## Documentation

- [Project specification](docs/HydroSense_Project_Specification_for_IDE.md)
- [API contract](docs/api-contract.md)
- [Minimal AWS integration plan](docs/aws-integration-plan.md)
- [Sprint 0 checklist](docs/sprint-0-checklist.md)
- [Hardware handoff](hardware/README.md)
