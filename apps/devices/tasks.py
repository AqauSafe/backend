"""Celery tasks for device liveness."""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.devices.models import Device
from apps.telemetry.realtime import broadcast_farm_event


@shared_task
def mark_stale_devices() -> int:
    cutoff = timezone.now() - timedelta(seconds=settings.DEVICE_STALE_AFTER_SECONDS)
    stale = list(
        Device.objects.filter(status=Device.Status.ONLINE, last_seen_at__lt=cutoff).select_related(
            "farm"
        )
    )
    for device in stale:
        broadcast_farm_event(
            device.farm_id,
            "device.status",
            {
                "deviceId": str(device.id),
                "deviceKey": device.device_id,
                "status": Device.Status.OFFLINE,
                "lastSeenAt": device.last_seen_at.isoformat() if device.last_seen_at else None,
            },
        )
    if stale:
        Device.objects.filter(id__in=[device.id for device in stale]).update(
            status=Device.Status.OFFLINE,
            updated_at=timezone.now(),
        )
    return len(stale)
