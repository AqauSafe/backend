from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.commands.models import Command
from apps.devices.models import Device
from apps.telemetry.models import DeviceEvent, DeviceHeartbeat, SensorReading
from integrations.mqtt.crypto import encrypt_secret
from integrations.mqtt.handlers import handle_message
from integrations.mqtt.signing import sign_telemetry
from integrations.mqtt.topics import (
    command_ack_topic,
    config_ack_topic,
    events_topic,
    heartbeat_topic,
    status_topic,
    telemetry_topic,
)


def make_device(farm, pond, device_id="esp32-mqtt"):
    return Device.objects.create(
        farm=farm,
        pond=pond,
        device_id=device_id,
        name="MQTT Device",
        status=Device.Status.PROVISIONED,
        command_secret_encrypted=encrypt_secret("device-secret"),
    )


def signed(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return json.dumps({"payload": body, "signature": sign_telemetry("device-secret", body)})


@pytest.mark.django_db
def test_telemetry_is_persisted_once(farm, pond):
    device = make_device(farm, pond)
    payload = {
        "messageId": "message-1",
        "recordedAt": "2026-11-11T10:00:00Z",
        "temperature": 27.4,
        "oxygen": 6.1,
        "ph": 7.2,
        "level": 81,
        "turbidityNtu": 14.2,
    }

    first = handle_message(telemetry_topic(device.device_id), signed(payload))
    second = handle_message(telemetry_topic(device.device_id), signed(payload))

    assert first == "reading.created"
    assert second == "duplicate"
    assert SensorReading.objects.filter(pond=pond).count() == 1
    reading = SensorReading.objects.get(pond=pond)
    assert reading.source == "physical"
    assert reading.message_id == "message-1"
    assert reading.oxygen == Decimal("6.1")
    assert reading.turbidity_ntu == Decimal("14.2")
    device.refresh_from_db()
    assert device.status == Device.Status.ONLINE
    assert device.last_seen_at is not None


@pytest.mark.django_db
def test_telemetry_requires_valid_signature(farm, pond):
    device = make_device(farm, pond)
    payload = {"messageId": "unsigned-1", "oxygen": 6.1}

    with pytest.raises(ValueError, match="Signed telemetry is required"):
        handle_message(telemetry_topic(device.device_id), json.dumps(payload))

    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    tampered = json.dumps({"payload": body, "signature": sign_telemetry("wrong-secret", body)})
    with pytest.raises(ValueError, match="Invalid telemetry signature"):
        handle_message(telemetry_topic(device.device_id), tampered)
    assert SensorReading.objects.count() == 0


@pytest.mark.django_db
def test_heartbeat_updates_device_and_records_history(farm, pond):
    device = make_device(farm, pond)

    result = handle_message(
        heartbeat_topic(device.device_id),
        json.dumps({"recordedAt": "2026-11-11T10:00:00Z", "rssi": -52, "uptimeSeconds": 100}),
    )

    assert result == "device.heartbeat"
    heartbeat = DeviceHeartbeat.objects.get(device=device)
    assert heartbeat.rssi == -52
    assert heartbeat.uptime_seconds == 100
    device.refresh_from_db()
    assert device.status == Device.Status.ONLINE


@pytest.mark.django_db
def test_status_and_event_messages(farm, pond):
    device = make_device(farm, pond)

    status = handle_message(status_topic(device.device_id), json.dumps({"status": "offline"}))
    assert status == "device.status"
    device.refresh_from_db()
    assert device.status == Device.Status.OFFLINE

    event = handle_message(
        events_topic(device.device_id),
        json.dumps({"eventType": "sensor_fault", "severity": "warning", "message": "Probe open"}),
    )
    assert event == "device.event"
    stored = DeviceEvent.objects.get(device=device)
    assert stored.event_type == "sensor_fault"
    assert stored.severity == "warning"


@pytest.mark.django_db
def test_command_ack_updates_command(farm, pond):
    device = make_device(farm, pond)
    command = Command.objects.create(
        device=device,
        command_type="aerator.set",
        payload={"on": True},
        status=Command.Status.SENT,
        expires_at=timezone.now() + timedelta(minutes=1),
    )

    result = handle_message(
        command_ack_topic(device.device_id),
        json.dumps({"commandId": str(command.id), "success": True, "result": {"on": True}}),
    )

    assert result == "command.status"
    command.refresh_from_db()
    assert command.status == Command.Status.ACKNOWLEDGED
    assert command.result == {"on": True}
    assert command.acknowledged_at is not None


@pytest.mark.django_db
def test_config_ack_advances_version(farm, pond):
    device = make_device(farm, pond)

    result = handle_message(
        config_ack_topic(device.device_id),
        json.dumps({"version": 3, "accepted": True}),
    )

    assert result == "device.config"
    device.refresh_from_db()
    assert device.config_version == 3


@pytest.mark.django_db
def test_unknown_device_and_unassigned_pond_are_rejected(farm):
    orphan = Device.objects.create(farm=farm, device_id="esp32-orphan", name="Orphan")

    with pytest.raises(ValueError):
        handle_message(telemetry_topic("missing-device"), "{}")

    with pytest.raises(ValueError):
        handle_message(telemetry_topic(orphan.device_id), json.dumps({"oxygen": 5}))

    assert SensorReading.objects.count() == 0
