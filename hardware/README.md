# Hardware Sprint 1 Handoff

**Status: Hardware integration in progress.** No physical sensor reading has been received by the
backend. No Arduino firmware file and no recorded demonstration video are present anywhere in
this repository as of this report; neither is fabricated or linked here. Rasleen owns the hardware
build per the project specification, but its artifacts have not yet been committed.

## Intended bill of materials

| Component | Role |
|---|---|
| Arduino (Wi-Fi capable board, e.g. Arduino Uno R4 WiFi / Nano 33 IoT) | Reads the sensor and posts `SensorReading` JSON to the backend |
| HC-SR04 ultrasonic distance sensor | Measures distance from the sensor to the water surface |
| OLED display (optional, per project spec) | Local readout of distance, depth, and threshold state |
| Voltage divider / logic-level shifter | Steps the 5 V `ECHO` signal down to a safe 3.3 V GPIO input |

The software vertical slice uses `scripts/simulate_sensor.py` until physical hardware is available. The simulator and Arduino must send the same `SensorReading` JSON contract.

Physical hardware work is outside the currently completed software phase. No bench, serial, Wi-Fi, or AWS IoT result has been verified in this repository; the checklist below remains a handoff, not evidence of completion.

## Required bench verification

- [ ] Confirm Arduino board powers and exposes a stable serial port.
- [ ] Wire HC-SR04 `VCC` to 5 V, `GND` to ground, and `TRIG` to the selected output GPIO.
- [ ] Connect `ECHO` through a voltage divider or level shifter before the Arduino input GPIO. Never connect the typical 5 V Echo output directly to 3.3 V GPIO.
- [ ] Mount the sensor above the water and protect electronics from splashes.
- [ ] Measure container height with a ruler and compare at least three known distances.
- [ ] Record measured distance, ruler distance, absolute error, and calibrated container height.
- [ ] Confirm timeout and out-of-range samples are dropped.
- [ ] Publish the sample payload below over serial/local HTTP first.
- [ ] Attempt Wi-Fi and AWS IoT MQTT only when private certificates are available outside this repository.

Note: this is a handoff checklist, not evidence that any step above has been completed.

## Sample payload

```json
{
  "device_id": "hydrosense-demo-01",
  "location_id": "demo-zone-01",
  "water_depth_cm": 25.0,
  "distance_cm": 5.0,
  "timestamp": "2026-10-10T10:30:00Z",
  "source": "arduino"
}
```

## Current blockers

Physical wiring, ruler calibration, Wi-Fi, and MQTT were not verified from the development environment because no serial-connected Arduino/HC-SR04 or AWS IoT device certificates were available to the coding agent. Do not mark these checks complete until Rasleen records bench results. Certificates and Wi-Fi credentials must stay outside Git.
