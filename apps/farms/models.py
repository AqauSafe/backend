"""Farm, pond, membership and feeding models."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Farm(TimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_farms",
    )
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255, blank=True)
    client_id = models.CharField(max_length=100, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "farms"
        ordering = ["name"]
        indexes = [models.Index(fields=["owner", "name"])]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "client_id"],
                condition=~Q(client_id=""),
                name="unique_farm_client_id_per_owner",
            )
        ]

    def __str__(self) -> str:
        return self.name


class FarmMembership(TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        WORKER = "worker", "Worker"
        VIEWER = "viewer", "Viewer"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="farm_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WORKER)

    class Meta:
        db_table = "farm_memberships"
        ordering = ["farm", "user"]
        constraints = [
            models.UniqueConstraint(fields=["farm", "user"], name="unique_farm_membership")
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.farm} ({self.role})"


class Pond(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FALLOW = "fallow", "Fallow"
        MAINTENANCE = "maintenance", "Maintenance"
        HARVESTED = "harvested", "Harvested"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="ponds")
    name = models.CharField(max_length=150)
    population = models.PositiveIntegerField(default=0)
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    depth = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    species = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    client_id = models.CharField(max_length=100, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ponds"
        ordering = ["farm", "name"]
        indexes = [models.Index(fields=["farm", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "client_id"],
                condition=~Q(client_id=""),
                name="unique_pond_client_id_per_farm",
            )
        ]

    def __str__(self) -> str:
        return f"{self.farm.name} / {self.name}"

    @property
    def area(self):
        return self.length * self.width


class Feeding(TimeStampedModel):
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name="feedings")
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    fed_at = models.DateTimeField(default=timezone.now, db_index=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedings_recorded",
    )
    client_id = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        db_table = "feedings"
        ordering = ["-fed_at"]
        indexes = [models.Index(fields=["pond", "-fed_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["pond", "client_id"],
                condition=~Q(client_id=""),
                name="unique_feeding_client_id_per_pond",
            )
        ]

    def __str__(self) -> str:
        return f"{self.pond} feed {self.amount}kg"
