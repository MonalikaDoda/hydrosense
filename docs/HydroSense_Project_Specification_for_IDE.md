# HydroSense — Project Specification & IDE Implementation Guide

**Hackathon:** WeMakeDevs × AWS Environmental Hacks  
**Track:** Track 2 — Heat & Water  
**Project location/context:** Delhi, India  
**Team:** Mukul Rana (backend/AWS/integration), Rasleen (hardware/IoT), Poojya (frontend/product experience)  
**Target submission:** October 11, 2026 (verify the official cutoff time on the event page)  
**Document purpose:** A single source of truth for an AI coding IDE/agent to implement the project in phases.

---

## 1. Product Summary

HydroSense is a Delhi-focused, geospatial water-risk and response-prioritization platform. It combines two related but technically different workflows:

1. **Flood-risk monitoring:** Uses available rainfall, terrain, drainage and historical waterlogging context to estimate risk for selected pilot locations. Satellite radar may support historical/current flood-extent analysis when suitable data is available, but it is not treated as a live underground-drainage sensor.
2. **Water-loss / leak anomaly monitoring:** Analyzes pressure and flow readings to flag patterns that may indicate a pipeline leak. For the hackathon demo, these readings may be simulated and must be labelled as simulated.
3. **Equity-aware response prioritization:** Combines hazard severity with service vulnerability and exposure to help operators prioritize inspection. Scores are decision-support indicators, not scientific probabilities or proof of household-level deprivation.
4. **Physical water-level demonstration:** An ESP32 and HC-SR04 ultrasonic sensor measure water depth in a container. This proves a sensor-to-cloud workflow; it does not prove citywide flood prediction.

### One-line pitch
**HydroSense helps city teams see where water-related risks may emerge, prioritize vulnerable service areas, and turn sensor or model signals into actionable, trackable incidents.**

### Product promise and limitations
- The prototype supports decision-making; it does not autonomously dispatch emergency services.
- A predicted flood risk, suspected leak and verified incident are distinct statuses.
- Do not claim access to live Delhi Jal Board pressure data unless access is actually obtained.
- Do not present simulated readings or synthetic incident locations as real events.
- Do not claim that satellite imagery can pinpoint small underground drinking-water pipe leaks.

---

## 2. Hackathon MVP: Scope and Priorities

### P0 — Must work in the submission
- A polished responsive dashboard.
- A Delhi-context map with clearly labelled pilot/demo locations and risk layers.
- A flood-risk scoring flow based on available inputs or explicit demo scenarios.
- A simulated pipeline pressure/flow anomaly workflow.
- An incident record with hazard type, location, severity, confidence, evidence/source, timestamp and status.
- A working backend and AWS persistence/processing path.
- One end-to-end alert path; SNS SMS if configured, otherwise a verified fallback such as an in-app alert plus logs.
- A physical ESP32 sensor stream if hardware is available and stable; otherwise a simulator that uses the same payload contract.
- A public repository, setup instructions, project write-up and demo video under three minutes.

### P1 — Add only after P0 is reliable
- Live ESP32 ingestion via AWS IoT Core MQTT.
- SMS alerting through Amazon SNS.
- Real public rainfall/elevation/historical flood datasets.
- Incident assignment and resolution actions.
- Downloadable incident data or audit history.

### Explicitly out of scope for the deadline
- Citywide operational deployment.
- Guaranteed flood prediction or exact underground leak localization.
- Integration with private/municipal sensor systems without permission.
- Complex ML models without relevant labelled training data.
- Unnecessary AWS services added only for architecture appearance.
- Direct WhatsApp delivery through SNS; SNS supports SMS, not direct WhatsApp messaging. Use an approved WhatsApp Business provider only if time and access permit.

---

## 3. Primary User and Core User Journey

### Primary user
A municipal field operator or water/environment response coordinator reviewing possible hazards and deciding which locations need inspection.

### Core journey
1. Operator opens HydroSense dashboard.
2. Dashboard shows risk summaries and a map of pilot/demo locations.
3. New sensor reading, rainfall scenario or simulated pressure/flow anomaly is processed.
4. Backend applies thresholds/risk rules and creates or updates an incident.
5. Incident appears in the map and incident list.
6. If the configured threshold is crossed, the alert workflow sends a notification or records a visible demo notification.
7. Operator opens the incident, reviews evidence/confidence, and marks it `assigned`, `verified`, `resolved` or `dismissed`.

### Required incident statuses
- `open`
- `assigned`
- `verified`
- `resolved`
- `dismissed`

### Required source labels
- `esp32` — physical prototype sensor
- `simulated_sensor` — simulated depth reading
- `simulated_leak` — synthetic pressure/flow anomaly
- `public_dataset` — public geographic/weather data
- `operator_report` — manually entered report

---

## 4. Technical Architecture

### Recommended lean architecture

**Frontend**
- React + TypeScript + Vite
- Tailwind CSS
- Leaflet + OpenStreetMap for map display
- Recharts or lightweight native charts if needed

**Backend**
- Python + FastAPI for API and domain logic
- Pydantic request/response schemas
- A small service layer for flood scoring, leak anomaly detection and incident management

**AWS**
- Amazon API Gateway + AWS Lambda for serverless ingestion/alert handlers, or deploy FastAPI as one backend service. Do not duplicate the same business logic in two implementations.
- Amazon DynamoDB for sensor readings, incidents and alert records
- Amazon S3 for source data files and analysis artifacts
- AWS IoT Core + MQTT for the optional ESP32 live path
- AWS IoT Rules or EventBridge to route threshold events
- Amazon SNS for SMS if credentials/configuration are available
- CloudWatch logs for troubleshooting

### Recommended implementation choice
For a short hackathon, keep FastAPI as the main application backend and use AWS Lambda for the event-driven IoT/alert path if useful. If setup complexity threatens delivery, use API Gateway + Lambda for a small set of endpoints and keep domain logic in shared Python modules. Choose one clear deployment path.

### Data flow
1. ESP32 publishes JSON over MQTT to AWS IoT Core, or a simulator posts the same schema to the API.
2. Backend validates the reading, timestamp and device/location.
3. Reading is stored.
4. Rules evaluate water depth or anomaly score.
5. If a threshold is crossed, an incident is created or deduplicated.
6. Dashboard fetches updated readings/incidents.
7. Notification is sent to a configured recipient, if enabled.

### Security requirements
- Never commit AWS access keys, certificates, private keys, `.env` files or real phone numbers.
- Add `.env.example` with placeholder values only.
- Use least-privilege IAM policies.
- Validate all incoming payloads.
- Keep IoT certificates private and outside the repository.
- Do not expose administrative write endpoints without authentication if publicly deployed.
- Add CORS configuration for the actual frontend origin rather than `*` in production.

---

## 5. Data Model and API Contract

Use ISO-8601 UTC timestamps. Keep units explicit.

### Sensor reading payload
```json
{
  "device_id": "hydrosense-demo-01",
  "location_id": "demo-zone-01",
  "water_depth_cm": 22.0,
  "distance_cm": 8.0,
  "timestamp": "2026-10-10T10:30:00Z",
  "source": "esp32"
}
```

`water_depth_cm` and `distance_cm` are example values. A real device must calculate them from its calibration. For the simulator, set `source` to `simulated_sensor`.

### Leak measurement payload
```json
{
  "location_id": "demo-supply-zone-01",
  "pressure_kpa": 180.0,
  "flow_lpm": 42.0,
  "timestamp": "2026-10-10T10:30:00Z",
  "source": "simulated_leak"
}
```

These are synthetic example readings, not real Delhi water-network measurements.

### Incident object
```json
{
  "incident_id": "generated-uuid",
  "hazard_type": "high_water_level",
  "title": "Prototype water level threshold crossed",
  "location_id": "demo-zone-01",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "severity": "high",
  "confidence": 0.9,
  "status": "open",
  "source": "esp32",
  "evidence": {
    "water_depth_cm": 25.0,
    "threshold_cm": 24.0
  },
  "created_at": "ISO-8601 UTC timestamp",
  "updated_at": "ISO-8601 UTC timestamp"
}
```

Coordinates above are illustrative central-Delhi coordinates for a demo only. Do not label them as a real hazard location. Prefer a clearly named demo site or verified public point in the UI.

### Suggested API endpoints
- `GET /health` — service health
- `GET /api/v1/dashboard/summary` — counts and headline risk indicators
- `GET /api/v1/readings/latest` — latest readings
- `POST /api/v1/readings` — ingest a simulated or trusted reading
- `POST /api/v1/leak-measurements` — submit simulated pressure/flow readings
- `GET /api/v1/incidents` — list incidents; allow filtering by hazard/status
- `GET /api/v1/incidents/{incident_id}` — incident details
- `PATCH /api/v1/incidents/{incident_id}` — update allowed status/assignment fields
- `POST /api/v1/demo/trigger` — demo-only trigger to create a test scenario; disable or protect outside demo mode

Use consistent JSON error responses and appropriate HTTP status codes. Document the API with FastAPI OpenAPI/Swagger.

---

## 6. Domain Logic

### A. Prototype water depth
The HC-SR04 measures distance from the sensor to the water surface.

`water_depth_cm = calibrated_container_height_cm - measured_distance_cm`

Requirements:
- Average several readings or use a small median filter.
- Reject timeout/out-of-range measurements.
- Do not report negative depth.
- Configure container height and threshold through environment/config values.
- Use a configurable demo threshold, for example 24 cm, clearly labelled as a prototype threshold.
- Add a cooldown/deduplication window to avoid sending repeated alerts every second while the water remains above threshold.

### B. Flood-risk score
Build a transparent baseline, not an unvalidated black-box model. Use normalized values in the range 0–100:
- rainfall risk
- terrain/low-lying risk
- drainage/historical-waterlogging risk, if available

Example placeholder formula:
`flood_score = 0.4 * rainfall_score + 0.35 * terrain_score + 0.25 * drainage_history_score`

These weights are illustrative and must be configurable. If real data is unavailable, label the output `DEMO SCENARIO` and show the inputs used. Do not imply scientific calibration.

Suggested bands:
- 0–29: low
- 30–59: moderate
- 60–79: high
- 80–100: very high

### C. Leak anomaly score
For the hackathon, implement a transparent rule-based detector against a configurable baseline:
- pressure drop larger than configured threshold
- unexpected flow increase or imbalance
- repeated anomalies over a short window

Example logic: flag a suspected leak when pressure is below baseline by a configured percentage and flow is unusually high. Make the thresholds adjustable and document that real utility data would be required to calibrate it.

Do not claim the system can identify the exact buried leak point from these values alone. Output the suspected supply zone/segment and inspection priority.

### D. Equity-aware priority score
Use three normalized inputs:
- `H` = hazard severity (0–100)
- `V` = water-service vulnerability (0–100, based on explicit service indicators where available)
- `E` = exposure (0–100, based on estimated people/services affected where available)

Example:
`priority_score = 0.5 * H + 0.3 * V + 0.2 * E`

This is an illustrative prioritization score, not a probability. Display the component values and their sources. Do not infer an area's service vulnerability solely from income or use household-identifying data.

---

## 7. Hardware Specification — Rasleen

### Components
- ESP32 DevKit board with Wi-Fi
- HC-SR04 ultrasonic sensor
- I²C OLED display
- Breadboard and jumper wires
- Resistors for a voltage divider on Echo
- USB power
- Plastic container/bucket and ruler

Approximate component costs may vary. Use existing components first.

### Local-first implementation milestone
The first hardware milestone is a working local ESP32 + HC-SR04 + OLED prototype. Wi-Fi and AWS IoT Core publishing are the next step after local validation; they are not prerequisites for accepting the local hardware milestone.

The device must:
- measure the sensor-to-water distance in centimetres;
- calculate `water_depth_cm = configured_reference_depth_cm - measured_distance_cm`;
- display the measured distance, calculated depth in centimetres and status (`NORMAL`, `CAUTION` or `HIGH`) on the OLED; and
- produce stable serial output for the same values.

Reference depth and the status thresholds must be configurable. Status thresholds are illustrative demo settings, not validated flood-safety thresholds. The physical prototype measures water level inside a controlled container; it does not itself predict flooding across Delhi. The Delhi risk map and simulated pipeline pressure/flow anomaly workflow remain separate software components.

### Example wiring and configuration
- HC-SR04 `TRIG`: GPIO 5.
- HC-SR04 `ECHO`: GPIO 18 through a suitable voltage divider or level shifter.
- Typical I²C OLED `SDA`: GPIO 21; `SCL`: GPIO 22.
- Verify the actual ESP32 board and sensor/display module pin labels before wiring; labels and supported pins may differ by board revision.

### Electrical safety
- ESP32 GPIO is 3.3 V logic. Typical HC-SR04 Echo output is 5 V; use a voltage divider or suitable level shifter.
- Never connect a 5 V Echo output directly to an ESP32 GPIO input.
- Keep all electronics dry, above the container and protected from splashes.
- Use USB power and keep mains power away from water.
- HC-SR04 is not waterproof and is for a controlled prototype only.
- Treat missing echoes, timeouts and out-of-range measurements as invalid; do not calculate or publish a normal depth from them.
- Reject or safely clamp calculated depths outside the configured container range, and expose an error state instead of displaying a misleading status.

### Shared sensor payload
Physical readings must remain compatible with the existing backend `SensorReading` schema and simulator. Preserve `device_id`, `location_id`, `water_depth_cm`, `distance_cm`, a timezone-aware ISO-8601 timestamp and `source`. Use `source: "esp32"` for physical readings and `source: "simulated_sensor"` for synthetic simulator readings. Do not introduce a separate hardware schema without a demonstrated need.

Agreed units are centimetres for distance and water depth, and UTC for timestamps:

```json
{
  "device_id": "hydrosense-demo-01",
  "location_id": "demo-zone-01",
  "water_depth_cm": 25.0,
  "distance_cm": 5.0,
  "timestamp": "2026-10-10T10:30:00Z",
  "source": "esp32"
}
```

### Hardware deliverables
1. Circuit/wiring note or diagram.
2. Firmware source code committed to `hardware/`.
3. Locally validated distance and calibrated water-depth output in centimetres.
4. OLED output showing distance, depth and `NORMAL`, `CAUTION` or `HIGH` status.
5. Stable serial output and one sample payload matching the shared contract.
6. Short video clip showing the water level, OLED status and readings changing together.
7. AWS IoT Core MQTT publish attempted after local validation, or the exact blocker documented while retaining the simulator integration path.
8. README with device setup, configurable reference depth and thresholds, secrets/certificate handling and calibration.

### Hardware acceptance tests
- Sensor readings are checked against a ruler or known distances and approximate error is recorded.
- OLED distance, calculated depth and status change as the water level changes.
- Missing echoes, invalid readings and calculated depths outside the configured container range fail safely.
- Stable serial output and a short local hardware demonstration are available.
- A sample payload follows the existing backend schema and uses the agreed units and source label.
- AWS publishing is attempted only after local validation. If it is blocked, record the exact blocker and retain the simulator as the software integration path.
- Device reconnects or fails gracefully if Wi-Fi is unavailable during the later connectivity step.
- Device does not expose credentials in logs or source code.

---

## 8. Sprint Plan and Ownership

### Sprint 0 — Contract and scaffolding (October 9)
**All:** agree on one demo scenario, source labels, payload schema and definition of done.

**Mukul**
- Create repository, issue board, environment templates and architecture README.
- Define API schemas and incident lifecycle.
- Set up backend skeleton and health endpoint.

**Rasleen**
- Inventory hardware, test ESP32 USB connection and sensor.
- Confirm Wi-Fi and AWS IoT feasibility.
- Send a sample payload matching the contract.

**Poojya**
- Create React/Vite app and dashboard shell.
- Build map and incident list against mock JSON.
- Agree on frontend API client interface.

**Sprint exit criteria:** each person can run their own component; payload contract is agreed.

### Sprint 1 — Independent vertical slices (October 10, first work block)
**Mukul**
- Implement reading validation, incident model, flood-risk baseline, leak rules and basic storage.
- Provide mock data and API responses early.
- Set up AWS resources needed for the selected path.

**Rasleen**
- First complete the local ESP32 + HC-SR04 + OLED milestone using configurable reference depth and illustrative status thresholds.
- Check sensor distance and calculated depth against a ruler or known distances, and verify that OLED values and `NORMAL`, `CAUTION` and `HIGH` states change with water level.
- Produce stable serial output, a short local demonstration and one `source: "esp32"` payload matching the existing `SensorReading` contract.
- After local validation, attempt Wi-Fi and AWS IoT Core MQTT publishing without committing credentials or certificates.
- If AWS publishing is blocked, document the exact blocker and retain the existing simulator as the backend/dashboard integration path.

**Poojya**
- Complete dashboard cards, map markers, risk legend and incident detail panel.
- Show clear labels for real, simulated and demo-scenario data.
- Add loading, error and empty states.

**Sprint exit criteria:** backend works with a test payload; the local hardware prototype has ruler-checked readings, changing OLED values/status, stable serial output, a short demonstration and a schema-compatible sample payload; frontend works with mock data. AWS publishing is attempted after local hardware validation, with any blocker documented and the simulator retained as the integration path.

### Sprint 2 — Integration (October 10, second work block)
**Mukul + Rasleen**
- Connect MQTT ingestion or simulator POST to backend processing.
- Verify persistence and threshold processing.
- Configure notification path.

**Mukul + Poojya**
- Connect UI to API.
- Verify that a newly created incident appears in map and list.
- Implement incident status update.

**All**
- Run the exact demo scenario from start to finish.
- Fix only blockers and high-severity bugs.

**Sprint exit criteria:** one complete sensor/simulator → AWS/backend → stored incident → dashboard → alert path works.

### Sprint 3 — Submission hardening (October 11)
**Mukul**
- Verify deployed backend, AWS logs, data persistence and notification.
- Review IAM permissions and repository secrets.
- Finalize architecture and setup documentation.

**Rasleen**
- Stabilize sensor mounting, water experiment and calibration.
- Capture backup footage if needed.

**Poojya**
- Polish responsive layout, visual hierarchy and incident labels.
- Ensure map and demo states are legible in screen recording.

**All**
- Record a demo video under three minutes.
- Confirm repository is public and runnable with documented setup.
- Complete the project write-up.
- Verify official submission cutoff and submit early.

---

## 9. Repository Structure

Use this as a target structure; simplify if the team has already started a different clean structure.

```text
hydrosense/
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── data-sources.md
│   ├── api-contract.md
│   ├── demo-script.md
│   └── limitations.md
├── frontend/
│   ├── package.json
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── api/
│       ├── hooks/
│       ├── types/
│       └── data/
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── flood_risk.py
│   │   │   ├── leak_detection.py
│   │   │   ├── prioritization.py
│   │   │   └── alerting.py
│   │   ├── repositories/
│   │   └── config.py
│   └── tests/
├── hardware/
│   ├── firmware/
│   ├── wiring.md
│   └── README.md
├── infrastructure/
│   └── README.md
└── scripts/
    ├── seed_demo_data.py
    └── simulate_sensor.py
```

---

## 10. IDE Agent Instructions

Paste the following into the coding IDE as the implementation brief:

> You are the senior full-stack engineer implementing HydroSense for the WeMakeDevs × AWS Environmental Hacks, Track 2: Heat & Water.
>
> First inspect the existing repository and preserve working code. Do not rewrite the project blindly. Read this specification and turn it into small, testable tasks.
>
> Implement the project in the listed sprints. Start with a working end-to-end vertical slice and use mock data where external data or hardware is unavailable. Keep the ESP32 payload contract identical to the simulator payload contract.
>
> Implement hardware local-first. Rasleen must first demonstrate an ESP32 + HC-SR04 + OLED prototype that measures sensor-to-water distance, calculates depth from a configurable reference depth, and displays distance, depth in centimetres and `NORMAL`, `CAUTION` or `HIGH`. Treat thresholds as illustrative demo settings, verify readings against known distances, handle invalid readings safely, and use a voltage divider or level shifter on the HC-SR04 Echo line. Attempt Wi-Fi and AWS IoT Core only after this local milestone works.
>
> Preserve the existing `SensorReading` contract for both physical and simulated ingestion, using `esp32` and `simulated_sensor` source labels respectively. The container prototype does not predict flooding across Delhi; keep it distinct from the Delhi risk map and simulated pipeline pressure/flow anomaly workflow. A blocked hardware MQTT path may use the simulator for integration, but the submitted project still requires genuine, demonstrable AWS use.
>
> Build a React + TypeScript + Vite frontend with a map, risk summaries, incident list, incident details and status updates. Build a Python FastAPI backend with validated schemas, documented endpoints, transparent flood-risk scoring, rule-based simulated leak anomaly detection and incident lifecycle handling.
>
> Integrate AWS in a way that is real and demonstrable: DynamoDB for readings/incidents, S3 for source artifacts where useful, and an actual event-driven alert path. Use AWS IoT Core MQTT for the ESP32 if credentials and time permit. Never hardcode credentials. Use `.env.example` placeholders and document deployment.
>
> Clearly distinguish `esp32`, `simulated_sensor`, `simulated_leak`, `public_dataset` and `operator_report` data. Never label synthetic data as real municipal data. Show the inputs behind risk scores and label uncalibrated scores as demo estimates. Do not claim exact underground leak localization or citywide flood prediction.
>
> Add tests for schema validation, water-level thresholds, duplicate alert suppression, flood score bands, leak anomaly rules and incident status transitions. Add a simulator script so the whole workflow can be demonstrated without hardware.
>
> Work incrementally. After each sprint, run the relevant tests and build, fix errors, and update the README. Do not add unnecessary services, complex ML, or features that threaten the deadline. Prioritize the working demo path and submission deliverables.
>
> Before finishing, provide: (1) implemented features, (2) commands to run locally, (3) AWS resources/configuration required, (4) tests and their results, (5) known limitations, (6) a three-minute demo script, and (7) any unfinished tasks. Never claim a test, deployment or integration succeeded unless it was actually run and verified.

---

## 11. Testing Checklist

### Backend
- Valid reading accepted; malformed reading rejected.
- Depth below threshold does not create a high-water incident.
- Depth crossing threshold creates an incident.
- Sustained threshold crossing does not create repeated alert spam.
- Stale timestamps and invalid negative depth are handled.
- Leak anomaly rules trigger only when configured conditions are met.
- Incident status only accepts allowed transitions.
- Dashboard summary matches stored records.

### Frontend
- Dashboard loads with seeded demo data.
- Map markers use valid coordinates and clear demo labels.
- Filters for hazard type and status work.
- Incident details show source, timestamp, severity, confidence and evidence.
- API failure produces a helpful error state.
- Responsive layout works at recording resolution.

### End-to-end
- Simulator or ESP32 sends a payload.
- Payload is validated and stored.
- Threshold processing creates an incident.
- UI shows the new incident.
- Notification is recorded or delivered through the configured path.
- README setup instructions work on a clean environment.

---

## 12. Three-Minute Demo Script

**0:00–0:20 — Problem and context**  
“Delhi faces monsoon waterlogging and uneven access to reliable drinking water. HydroSense helps response teams identify risks and prioritize inspections.”

**0:20–0:55 — Dashboard**  
Show the Delhi-context map, flood-risk scenario, risk factors and incident panel. Clearly identify which inputs are public data and which are demo scenarios.

**0:55–1:30 — Physical sensor**  
Raise the water level in the container. Show the ESP32 reading changing and the same payload arriving in AWS or the backend.

**1:30–2:00 — Alert workflow**  
Cross the configured demo threshold. Show the incident being stored, displayed on the dashboard and sent to the test recipient or visible notification panel.

**2:00–2:25 — Leak and equity**  
Trigger the simulated pressure/flow anomaly. Show a suspected leak in a demo supply zone and explain how the illustrative priority score combines hazard, vulnerability and exposure.

**2:25–2:50 — AWS and engineering**  
Briefly show the real AWS resources and event flow, plus repository tests or logs proving the workflow.

**2:50–3:00 — Honest close**  
“This prototype demonstrates the workflow using a physical water-level sensor and clearly labelled simulated scenarios. A real municipal pilot would require validated local datasets and authorized utility integrations.”

---

## 13. Definition of Done

HydroSense is ready to submit when:

- [ ] The application runs using documented instructions.
- [ ] The dashboard shows a Delhi-context map and incident states.
- [ ] Flood-risk and leak-anomaly logic run and explain their inputs.
- [ ] At least one complete data-to-alert workflow is demonstrated.
- [ ] AWS is genuinely integrated and the used services are documented.
- [ ] Hardware works, or the same sensor schema is supported by a reliable simulator.
- [ ] Simulated data is clearly labelled.
- [ ] Tests run and results are accurately reported.
- [ ] No credentials or secrets are committed.
- [ ] Public GitHub repository, project write-up and video under three minutes are ready.
- [ ] The team has verified the official deadline and submitted.

**Guiding principle:** Ship one credible, testable end-to-end workflow. Treat citywide prediction and municipal integrations as future work, not as capabilities the prototype already has.
