"""Persisted notification outbox."""

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Notification(TimeStampedModel):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    alert = models.ForeignKey(
        "alerts.Alert",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    farm = models.ForeignKey(
        "farms.Farm",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    recipient = models.EmailField(blank=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    dedupe_key = models.CharField(max_length=150, unique=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["farm", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.channel} {self.status} to {self.recipient or self.user_id}"
