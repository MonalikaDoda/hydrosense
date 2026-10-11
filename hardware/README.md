# Hardware Sprint 1 Handoff

The software vertical slice uses `scripts/simulate_sensor.py` until physical hardware is available. The simulator and ESP32 must send the same `SensorReading` JSON contract.

Physical hardware work is outside the currently completed software phase. No bench, serial, Wi-Fi, or AWS IoT result has been verified in this repository; the checklist below remains a handoff, not evidence of completion.

## Required bench verification

- [ ] Confirm ESP32 board powers and exposes a stable serial port.
- [ ] Wire HC-SR04 `VCC` to 5 V, `GND` to ground, and `TRIG` to the selected output GPIO.
- [ ] Connect `ECHO` through a voltage divider or level shifter before the ESP32 input GPIO. Never connect the typical 5 V Echo output directly to 3.3 V GPIO.
- [ ] Mount the sensor above the water and protect electronics from splashes.
- [ ] Measure container height with a ruler and compare at least three known distances.
- [ ] Record measured distance, ruler distance, absolute error, and calibrated container height.
- [ ] Confirm timeout and out-of-range samples are dropped.
- [ ] Publish the sample payload below over serial/local HTTP first.
- [ ] Attempt Wi-Fi and AWS IoT MQTT only when private certificates are available outside this repository.

## Sample payload

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

## Current blockers

Physical wiring, ruler calibration, Wi-Fi, and MQTT were not verified from the development environment because no serial-connected ESP32/HC-SR04 or AWS IoT device certificates were available to the coding agent. Do not mark these checks complete until Rasleen records bench results. Certificates and Wi-Fi credentials must stay outside Git.
