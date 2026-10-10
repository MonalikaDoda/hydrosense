from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas import LeakMeasurement, SensorReading


def test_sensor_reading_accepts_simulator_contract() -> None:
    reading = SensorReading(
        device_id="hydrosense-demo-01",
        location_id="demo-zone-01",
        water_depth_cm=22.0,
        distance_cm=8.0,
        timestamp=datetime.now(UTC),
        source="simulated_sensor",
    )

    assert reading.water_depth_cm == 22.0


def test_sensor_reading_rejects_negative_depth() -> None:
    with pytest.raises(ValidationError):
        SensorReading(
            device_id="hydrosense-demo-01",
            location_id="demo-zone-01",
            water_depth_cm=-1,
            distance_cm=8.0,
            timestamp=datetime.now(UTC),
            source="simulated_sensor",
        )


def test_sensor_reading_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        SensorReading(
            device_id="hydrosense-demo-01",
            location_id="demo-zone-01",
            water_depth_cm=22.0,
            distance_cm=8.0,
            timestamp=datetime.now(),
            source="simulated_sensor",
        )


def test_leak_measurement_rejects_non_simulated_source() -> None:
    with pytest.raises(ValidationError):
        LeakMeasurement(
            location_id="demo-supply-zone-01",
            pressure_kpa=180.0,
            flow_lpm=42.0,
            timestamp=datetime.now(UTC),
            source="public_dataset",
        )
