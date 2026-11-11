"""Alert rules and lifecycle models."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.farms.models import Farm, Pond


class AlertMetric(models.TextChoices):
    TEMPERATURE = "temperature", "Temperature"
    OXYGEN = "oxygen", "Dissolved oxygen"
    PH = "ph", "pH"
    LEVEL = "level", "Water level"


class AlertOperator(models.TextChoices):
    LT = "lt", "Less than"
    LTE = "lte", "Less than or equal"
    GT = "gt", "Greater than"
    GTE = "gte", "Greater than or equal"


class AlertSeverity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class AlertRule(TimeStampedModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="alert_rules")
    pond = models.ForeignKey(
        Pond,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="alert_rules",
    )
    metric = models.CharField(max_length=20, choices=AlertMetric.choices)
    operator = models.CharField(max_length=5, choices=AlertOperator.choices)
    threshold = models.DecimalField(max_digits=8, decimal_places=2)
    severity = models.CharField(
        max_length=20, choices=AlertSeverity.choices, default=AlertSeverity.WARNING
    )
    cooldown_minutes = models.PositiveIntegerField(default=15)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alert_rules_created",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "alert_rules"
        ordering = ["farm", "metric"]
        indexes = [models.Index(fields=["farm", "is_active"])]

    def __str__(self) -> str:
        return f"{self.farm} {self.metric} {self.operator} {self.threshold}"

    def matches(self, value) -> bool:
        comparisons = {
            AlertOperator.LT: value < self.threshold,
            AlertOperator.LTE: value <= self.threshold,
            AlertOperator.GT: value > self.threshold,
            AlertOperator.GTE: value >= self.threshold,
        }
        return comparisons[self.operator]


class Alert(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="alerts")
    pond = models.ForeignKey(
        Pond,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )
    rule = models.ForeignKey(
        AlertRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )
    device = models.ForeignKey(
        "devices.Device",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )
    reading = models.ForeignKey(
        "telemetry.SensorReading",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )
    metric = models.CharField(max_length=20, choices=AlertMetric.choices)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    threshold = models.DecimalField(max_digits=8, decimal_places=2)
    severity = models.CharField(max_length=20, choices=AlertSeverity.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    message = models.CharField(max_length=255)
    triggered_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts_acknowledged",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts"
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(fields=["farm", "status", "-triggered_at"]),
            models.Index(fields=["pond", "status", "-triggered_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["rule", "pond"],
                condition=Q(status="active"),
                name="unique_active_alert_per_rule_pond",
            )
        ]

    def __str__(self) -> str:
        return f"{self.metric} {self.status} on {self.pond or self.farm}"
