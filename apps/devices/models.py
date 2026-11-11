"""Device, sensor and actuator registry models."""

from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel
from apps.farms.models import Farm, Pond


class Device(TimeStampedModel):
    class Kind(models.TextChoices):
        CONTROLLER = "controller", "Controller"
        SENSOR_NODE = "sensor_node", "Sensor Node"
        ACTUATOR_NODE = "actuator_node", "Actuator Node"
        GATEWAY = "gateway", "Gateway"

    class Status(models.TextChoices):
        PROVISIONED = "provisioned", "Provisioned"
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        MAINTENANCE = "maintenance", "Maintenance"
        RETIRED = "retired", "Retired"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="devices")
    pond = models.ForeignKey(
        Pond,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="devices",
    )
    device_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CONTROLLER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROVISIONED)
    hardware_model = models.CharField(max_length=100, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    claim_token_hash = models.CharField(max_length=128, blank=True)
    secret_encrypted = models.TextField(blank=True)
    client_id = models.CharField(max_length=100, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "devices"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["farm", "status"]),
            models.Index(fields=["pond", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "client_id"],
                condition=~Q(client_id=""),
                name="unique_device_client_id_per_farm",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.device_id})"


class Sensor(TimeStampedModel):
    class SensorType(models.TextChoices):
        TEMPERATURE = "temperature", "Temperature"
        DISSOLVED_OXYGEN = "dissolved_oxygen", "Dissolved Oxygen"
        PH = "ph", "pH"
        WATER_LEVEL = "water_level", "Water Level"
        OTHER = "other", "Other"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="sensors")
    key = models.SlugField(max_length=50)
    name = models.CharField(max_length=100)
    sensor_type = models.CharField(
        max_length=30, choices=SensorType.choices, default=SensorType.OTHER
    )
    unit = models.CharField(max_length=30, blank=True)
    pin = models.CharField(max_length=20, blank=True)
    calibration = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "sensors"
        ordering = ["device", "name"]
        constraints = [
            models.UniqueConstraint(fields=["device", "key"], name="unique_sensor_key_per_device")
        ]

    def __str__(self) -> str:
        return f"{self.device.name} / {self.name}"


class Actuator(TimeStampedModel):
    class ActuatorType(models.TextChoices):
        AERATOR = "aerator", "Aerator"
        PUMP = "pump", "Pump"
        FEEDER = "feeder", "Feeder"
        VALVE = "valve", "Valve"
        LIGHT = "light", "Light"
        OTHER = "other", "Other"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="actuators")
    key = models.SlugField(max_length=50)
    name = models.CharField(max_length=100)
    actuator_type = models.CharField(
        max_length=30, choices=ActuatorType.choices, default=ActuatorType.OTHER
    )
    pin = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    state = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "actuators"
        ordering = ["device", "name"]
        constraints = [
            models.UniqueConstraint(fields=["device", "key"], name="unique_actuator_key_per_device")
        ]

    def __str__(self) -> str:
        return f"{self.device.name} / {self.name}"
