"""Device command lifecycle model."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.devices.models import Device


class Command(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="commands")
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="device_commands_issued",
    )
    command_type = models.CharField(max_length=50, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    signature = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        db_table = "device_commands"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "status", "-created_at"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.command_type} -> {self.device.device_id} ({self.status})"
