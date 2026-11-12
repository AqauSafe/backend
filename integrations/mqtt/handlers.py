"""MQTT message handlers for device ingress."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.alerts.services import evaluate_reading
from apps.commands.models import Command
from apps.commands.services import acknowledge_command
from apps.devices.models import Device
from apps.devices.provisioning import device_secret
from apps.telemetry.models import (
    DeviceEvent,
    DeviceHeartbeat,
    ReadingSource,
    SensorReading,
)
from apps.telemetry.realtime import broadcast_farm_event
from integrations.mqtt.signing import verify_telemetry

TOPIC_RE = re.compile(
    r"^/devices/(?P<device_id>[^/]+)/(?P<kind>"
    r"telemetry|heartbeat|events|status|command-acks|config-ack)$"
)


def _as_dict(raw) -> dict:
    if isinstance(raw, bytes):
        raw = raw.decode()
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError("MQTT payload must be a JSON object.")
    return raw


def _number(message: dict, *keys: str) -> Decimal | None:
    for key in keys:
        if key in message and message[key] not in (None, ""):
            try:
                return Decimal(str(message[key]))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError(f"{key} must be numeric.") from exc
    return None


def _timestamp(message: dict) -> datetime:
    value = (
        message.get("recorded_at")
        or message.get("recordedAt")
        or message.get("timestamp")
        or message.get("date")
    )
    if not value:
        return timezone.now()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value)
    parsed = parse_datetime(text.replace("Z", "+00:00"))
    if parsed is not None:
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    parsed_date = parse_date(text[:10])
    if parsed_date is not None:
        return datetime.combine(parsed_date, time.min, tzinfo=UTC)
    raise ValueError("recorded_at must be an ISO-8601 date or datetime.")


def _json_safe(value):
    return json.loads(json.dumps(value, default=str))


def _mark_seen(device: Device, status: str | None = None) -> None:
    device.last_seen_at = timezone.now()
    if status:
        device.status = status
    device.save(update_fields=["last_seen_at", "status", "updated_at"])


def _ingest_signed_telemetry(device: Device, envelope: dict) -> str:
    if "payload" in envelope or "signature" in envelope:
        payload = envelope.get("payload")
        signature = envelope.get("signature")
        if not isinstance(payload, str) or not isinstance(signature, str):
            raise ValueError("Signed telemetry requires string payload and signature.")
        if not device.command_secret_encrypted:
            raise ValueError("Device has no command secret for telemetry verification.")
        if not verify_telemetry(device_secret(device), payload, signature):
            raise ValueError("Invalid telemetry signature.")
        return _ingest_telemetry(device, _as_dict(payload))
    if device.command_secret_encrypted:
        raise ValueError("Signed telemetry is required for this device.")
    return _ingest_telemetry(device, envelope)


def _ingest_telemetry(device: Device, message: dict) -> str:
    if device.pond_id is None:
        raise ValueError("Device is not assigned to a pond.")
    message_id = str(
        message.get("message_id")
        or message.get("messageId")
        or message.get("id")
        or uuid.uuid4().hex
    )[:100]
    if SensorReading.objects.filter(device=device, message_id=message_id).exists():
        _mark_seen(device, Device.Status.ONLINE)
        return "duplicate"

    reading = SensorReading.objects.create(
        pond=device.pond,
        device=device,
        source=ReadingSource.PHYSICAL,
        recorded_at=_timestamp(message),
        temperature=_number(message, "temperature", "temp"),
        oxygen=_number(message, "oxygen", "dissolved_oxygen", "dissolvedOxygen"),
        ph=_number(message, "ph", "pH"),
        level=_number(message, "level", "water_level", "waterLevel"),
        turbidity_ntu=_number(
            message, "turbidity_ntu", "turbidityNtu", "turbidity", "ntu"
        ),
        message_id=message_id,
        raw=message.get("raw") if isinstance(message.get("raw"), dict) else {},
        metadata=message.get("metadata") if isinstance(message.get("metadata"), dict) else {},
    )
    if not reading.has_measurement():
        reading.delete()
        raise ValueError("Telemetry has no measurements.")
    _mark_seen(device, Device.Status.ONLINE)
    evaluate_reading(reading)
    from apps.telemetry.serializers import SensorReadingSerializer

    broadcast_farm_event(
        device.farm_id,
        "reading.created",
        _json_safe(SensorReadingSerializer(reading).data),
    )
    return "reading.created"


def _ingest_heartbeat(device: Device, message: dict) -> str:
    status = str(message.get("status") or Device.Status.ONLINE)
    heartbeat = DeviceHeartbeat.objects.create(
        device=device,
        recorded_at=_timestamp(message),
        status=status,
        rssi=message.get("rssi"),
        uptime_seconds=message.get("uptime_seconds") or message.get("uptimeSeconds"),
        metadata=message.get("metadata") if isinstance(message.get("metadata"), dict) else {},
    )
    _mark_seen(device, status if status in Device.Status.values else Device.Status.ONLINE)
    broadcast_farm_event(
        device.farm_id,
        "device.heartbeat",
        {
            "deviceId": str(device.id),
            "deviceKey": device.device_id,
            "recordedAt": heartbeat.recorded_at.isoformat(),
            "rssi": heartbeat.rssi,
            "uptimeSeconds": heartbeat.uptime_seconds,
            "status": heartbeat.status,
        },
    )
    return "device.heartbeat"


def _ingest_event(device: Device, message: dict) -> str:
    severity = str(message.get("severity") or DeviceEvent.Severity.INFO)
    if severity not in DeviceEvent.Severity.values:
        severity = DeviceEvent.Severity.INFO
    event = DeviceEvent.objects.create(
        device=device,
        event_type=str(message.get("event_type") or message.get("eventType") or "device")[:100],
        severity=severity,
        message=str(message.get("message") or "")[:4000],
        recorded_at=_timestamp(message),
        metadata=message.get("metadata") if isinstance(message.get("metadata"), dict) else {},
    )
    _mark_seen(device, Device.Status.ONLINE)
    broadcast_farm_event(
        device.farm_id,
        "device.event",
        {
            "deviceId": str(device.id),
            "eventType": event.event_type,
            "severity": event.severity,
            "message": event.message,
            "recordedAt": event.recorded_at.isoformat(),
        },
    )
    return "device.event"


def _ingest_status(device: Device, message: dict) -> str:
    status = str(message.get("status") or Device.Status.ONLINE)
    if status not in Device.Status.values:
        raise ValueError("Unknown device status.")
    _mark_seen(device, status)
    broadcast_farm_event(
        device.farm_id,
        "device.status",
        {
            "deviceId": str(device.id),
            "deviceKey": device.device_id,
            "status": status,
            "lastSeenAt": device.last_seen_at.isoformat() if device.last_seen_at else None,
        },
    )
    return "device.status"


def _ingest_command_ack(device: Device, message: dict) -> str:
    command_id = message.get("command_id") or message.get("commandId") or message.get("id")
    if not command_id:
        raise ValueError("Command acknowledgement is missing command_id.")
    command = acknowledge_command(
        device=device,
        command_id=str(command_id),
        success=bool(message.get("success", True)),
        result=message.get("result") if isinstance(message.get("result"), dict) else {},
        error=str(message.get("error") or ""),
    )
    if command is None:
        raise ValueError("Command not found for this device.")
    broadcast_farm_event(
        device.farm_id,
        "command.status",
        {
            "commandId": str(command.id),
            "deviceId": str(device.id),
            "status": command.status,
            "result": command.result,
            "error": command.error,
        },
    )
    return "command.status"


def _ingest_config_ack(device: Device, message: dict) -> str:
    version = message.get("version") or message.get("config_version")
    if isinstance(version, int) and version > device.config_version:
        device.config_version = version
        device.save(update_fields=["config_version", "updated_at"])
    _mark_seen(device, Device.Status.ONLINE)
    broadcast_farm_event(
        device.farm_id,
        "device.config",
        {
            "deviceId": str(device.id),
            "version": device.config_version,
            "accepted": bool(message.get("accepted", True)),
        },
    )
    return "device.config"


HANDLERS = {
    "telemetry": _ingest_telemetry,
    "heartbeat": _ingest_heartbeat,
    "events": _ingest_event,
    "status": _ingest_status,
    "command-acks": _ingest_command_ack,
    "config-ack": _ingest_config_ack,
}


def handle_message(topic: str, raw_payload) -> str:
    prefix = settings.MQTT_TOPIC_PREFIX.rstrip("/")
    if not topic.startswith(f"{prefix}/devices/"):
        raise ValueError("Topic does not belong to this deployment.")
    match = TOPIC_RE.match(topic[len(prefix) :])
    if match is None:
        raise ValueError("Unsupported MQTT topic.")
    device = (
        Device.objects.filter(device_id=match.group("device_id"), status__in=Device.Status.values)
        .select_related("farm", "pond")
        .first()
    )
    if device is None:
        raise ValueError("Unknown device.")
    kind = match.group("kind")
    message = _as_dict(raw_payload)
    if kind == "telemetry":
        return _ingest_signed_telemetry(device, message)
    return HANDLERS[kind](device, message)


def handle_command_ack(device: Device, message: dict) -> Command | None:
    return acknowledge_command(
        device=device,
        command_id=str(message.get("command_id") or message.get("commandId") or ""),
        success=bool(message.get("success", True)),
        result=message.get("result") if isinstance(message.get("result"), dict) else {},
        error=str(message.get("error") or ""),
    )
