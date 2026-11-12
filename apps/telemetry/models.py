"""Telemetry, heartbeat and device event models."""

from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.devices.models import Device, Sensor
from apps.farms.models import Pond


class ReadingSource(models.TextChoices):
    PHYSICAL = "physical", "Physical device"
    SIMULATION = "simulation", "Simulation"
    MANUAL = "manual", "Manual entry"
    IMPORT = "import", "Imported"


class SensorReading(TimeStampedModel):
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name="readings")
    device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="readings",
    )
    sensor = models.ForeignKey(
        Sensor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="readings",
    )
    source = models.CharField(
        max_length=20, choices=ReadingSource.choices, default=ReadingSource.MANUAL
    )
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    temperature = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    oxygen = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    level = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    turbidity_ntu = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    client_id = models.CharField(max_length=100, blank=True, db_index=True)
    message_id = models.CharField(max_length=100, blank=True, db_index=True)
    raw = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "sensor_readings"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["pond", "-recorded_at"]),
            models.Index(fields=["source", "-recorded_at"]),
            models.Index(fields=["device", "-recorded_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["pond", "client_id"],
                condition=~Q(client_id=""),
                name="unique_reading_client_id_per_pond",
            ),
            models.UniqueConstraint(
                fields=["device", "message_id"],
                condition=~Q(message_id=""),
                name="unique_reading_message_id_per_device",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.pond} reading @ {self.recorded_at.isoformat()}"

    def has_measurement(self) -> bool:
        return any(
            value is not None
            for value in (self.temperature, self.oxygen, self.ph, self.level, self.turbidity_ntu)
        )


class DeviceHeartbeat(TimeStampedModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="heartbeats")
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=30, blank=True)
    rssi = models.IntegerField(null=True, blank=True)
    uptime_seconds = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "device_heartbeats"
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["device", "-recorded_at"])]

    def __str__(self) -> str:
        return f"{self.device} heartbeat @ {self.recorded_at.isoformat()}"


class DeviceEvent(TimeStampedModel):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    message = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "device_events"
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["device", "-recorded_at"])]

    def __str__(self) -> str:
        return f"{self.device} {self.event_type}"
