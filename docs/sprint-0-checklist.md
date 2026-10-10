# Sprint 0 Checklist

## Shared decisions

- [x] Use the Markdown specification as the source of truth.
- [x] Agree source labels, incident statuses, units, and UTC timestamp format.
- [x] Keep the ESP32 and simulator on the same sensor payload contract.
- [x] Use FastAPI as the main backend and defer the final AWS event path decision.
- [ ] Agree on the exact end-to-end demo location and scenario names.
- [ ] Confirm each teammate can run their component locally.

## Mukul - backend, AWS, integration

- [x] Scaffold FastAPI and add the health endpoint.
- [x] Define and test shared Pydantic contracts.
- [x] Add environment placeholders and secret exclusions.
- [x] Document the API agreement and local commands.
- [ ] Create the remote GitHub repository and issue board.
- [ ] Choose the Sprint 1 storage interface and local development fallback.
- [ ] Decide the lean AWS deployment/event path after validating account access.

## Rasleen - hardware and IoT

- [ ] Inventory the ESP32, HC-SR04, breadboard, divider resistors, USB cable, and container.
- [ ] Verify ESP32 USB/serial connectivity without committing credentials.
- [ ] Confirm the HC-SR04 Echo voltage divider or level shifter.
- [ ] Measure and record the calibrated container height.
- [ ] Produce one sample `SensorReading` JSON payload using centimetres and UTC.
- [ ] Assess AWS IoT Core feasibility; retain HTTP simulator fallback.

## Poojya - frontend and product

- [x] Scaffold React, TypeScript, and Vite.
- [x] Add shared TypeScript contract types and a health client.
- [ ] Confirm the frontend runs locally and reaches the backend health endpoint.
- [ ] Agree the Delhi demo locations and visible `DEMO SCENARIO` labels.
- [ ] Sketch the dashboard shell, map, incident list, and detail panel states.
- [ ] Define loading, empty, and API failure states before Sprint 1 integration.
