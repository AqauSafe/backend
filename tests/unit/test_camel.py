import pytest

from apps.common.camel import camelize, snakeize, to_camel_case, to_snake_case


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("farm_id", "farmId"),
        ("dissolved_oxygen", "dissolvedOxygen"),
        ("id", "id"),
        ("is_active", "isActive"),
    ],
)
def test_to_camel_case(value, expected):
    assert to_camel_case(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("farmId", "farm_id"),
        ("dissolvedOxygen", "dissolved_oxygen"),
        ("requestID", "request_id"),
    ],
)
def test_to_snake_case(value, expected):
    assert to_snake_case(value) == expected


def test_camelize_nested_structures():
    assert camelize(
        {
            "farm_id": "f1",
            "readings": [{"sensor_key": "ph", "received_at": "2026-01-01T00:00:00Z"}],
        }
    ) == {
        "farmId": "f1",
        "readings": [{"sensorKey": "ph", "receivedAt": "2026-01-01T00:00:00Z"}],
    }


def test_snakeize_nested_structures():
    assert snakeize(
        {
            "farmId": "f1",
            "sensorReadings": [{"recordedAt": "2026-01-01T00:00:00Z"}],
        }
    ) == {
        "farm_id": "f1",
        "sensor_readings": [{"recorded_at": "2026-01-01T00:00:00Z"}],
    }
