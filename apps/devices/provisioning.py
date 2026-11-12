"""One-time device provisioning and credential claim flow."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.devices.models import Device
from integrations.mqtt.crypto import decrypt_secret, encrypt_secret, generate_mqtt_password
from integrations.mqtt.topics import (
    command_ack_topic,
    commands_topic,
    config_ack_topic,
    config_topic,
    events_topic,
    heartbeat_topic,
    status_topic,
    telemetry_topic,
)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_claim_token(device: Device, *, ttl_minutes: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    device.claim_token_hash = _hash_token(token)
    device.claim_expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    device.save(update_fields=["claim_token_hash", "claim_expires_at", "updated_at"])
    return token


def claim_device(device_id: str, token: str) -> tuple[Device, str, str]:
    device = Device.objects.filter(device_id=device_id).first()
    if device is None or not device.claim_token_hash:
        raise ValidationError("Invalid device or claim token.")
    if device.claim_expires_at is None or device.claim_expires_at < timezone.now():
        raise ValidationError("This claim token has expired.")
    if not hmac.compare_digest(device.claim_token_hash, _hash_token(token)):
        raise ValidationError("Invalid device or claim token.")

    password = generate_mqtt_password()
    command_secret = secrets.token_urlsafe(32)
    device.secret_encrypted = encrypt_secret(password)
    device.command_secret_encrypted = encrypt_secret(command_secret)
    device.provisioned_at = timezone.now()
    device.claim_token_hash = ""
    device.claim_expires_at = None
    device.status = Device.Status.PROVISIONED
    device.save(
        update_fields=[
            "secret_encrypted",
            "command_secret_encrypted",
            "provisioned_at",
            "claim_token_hash",
            "claim_expires_at",
            "status",
            "updated_at",
        ]
    )
    return device, password, command_secret


def device_mqtt_password(device: Device) -> str:
    if not device.secret_encrypted:
        raise ValidationError("Device is not provisioned.")
    return decrypt_secret(device.secret_encrypted)


def device_secret(device: Device) -> str:
    if not device.command_secret_encrypted:
        raise ValidationError("Device command secret is not provisioned.")
    return decrypt_secret(device.command_secret_encrypted)


def device_topics(device: Device) -> dict:
    device_id = device.device_id
    return {
        "telemetry": telemetry_topic(device_id),
        "heartbeat": heartbeat_topic(device_id),
        "events": events_topic(device_id),
        "status": status_topic(device_id),
        "commands": commands_topic(device_id),
        "commandAcks": command_ack_topic(device_id),
        "config": config_topic(device_id),
        "configAck": config_ack_topic(device_id),
    }
