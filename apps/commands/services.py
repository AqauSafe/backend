"""Command signing, publishing, acknowledgement and expiry."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.commands.models import Command
from apps.devices.provisioning import device_secret
from integrations.mqtt.publishing import publish_message
from integrations.mqtt.signing import command_message, sign_command
from integrations.mqtt.topics import commands_topic

logger = logging.getLogger(__name__)


def create_command(
    *,
    device,
    actor,
    command_type: str,
    payload: dict | None = None,
    ttl_seconds: int = 60,
) -> Command:
    if not device.command_secret_encrypted:
        raise ValidationError("Device command secret is not provisioned.")
    now = timezone.now()
    command = Command.objects.create(
        device=device,
        issued_by=actor if getattr(actor, "is_authenticated", False) else None,
        command_type=command_type,
        payload=payload or {},
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    command.signature = sign_command(device_secret(device), command)
    command.save(update_fields=["signature", "updated_at"])
    try:
        publish_message(
            commands_topic(device.device_id),
            command_message(command),
            qos=1,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to publish command %s: %s", command.id, exc)
        command.error = f"publish_failed: {exc}"[:2000]
        command.save(update_fields=["error", "updated_at"])
        return command
    command.status = Command.Status.SENT
    command.sent_at = timezone.now()
    command.save(update_fields=["status", "sent_at", "updated_at"])
    return command


def acknowledge_command(
    *,
    device,
    command_id: str,
    success: bool,
    result: dict | None = None,
    error: str = "",
) -> Command | None:
    command = Command.objects.filter(id=command_id, device=device).first()
    if command is None:
        return None
    command.acknowledged_at = timezone.now()
    command.result = result or {}
    command.error = error[:2000]
    command.status = Command.Status.ACKNOWLEDGED if success else Command.Status.FAILED
    command.save(update_fields=["acknowledged_at", "result", "error", "status", "updated_at"])
    return command


def expire_commands() -> int:
    return Command.objects.filter(
        status__in=[Command.Status.PENDING, Command.Status.SENT],
        expires_at__lt=timezone.now(),
    ).update(status=Command.Status.EXPIRED, updated_at=timezone.now())
