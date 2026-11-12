"""Simulation state and planning-run models."""

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.farms.models import Farm, Pond


class Simulation(TimeStampedModel):
    """Mutable state for a pond fed by a simulator or the legacy bridge."""

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="simulations")
    pond = models.OneToOneField(Pond, on_delete=models.CASCADE, related_name="simulation")
    is_active = models.BooleanField(default=True, db_index=True)
    state = models.JSONField(default=dict, blank=True)
    last_state_at = models.DateTimeField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "simulations"
        ordering = ["farm", "pond"]
        indexes = [models.Index(fields=["farm", "is_active"])]

    def __str__(self) -> str:
        return f"Simulation for {self.pond}"


class SimulationRun(TimeStampedModel):
    """Immutable result of the deterministic pond planning calculator."""

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="simulation_runs")
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name="simulation_runs")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="simulation_runs",
    )
    formula_version = models.CharField(max_length=50, default="aquasafe-simple-v1")
    population = models.PositiveIntegerField()
    duration_days = models.PositiveSmallIntegerField()
    starting_weight_g = models.DecimalField(max_digits=10, decimal_places=2)
    daily_growth_g = models.DecimalField(max_digits=10, decimal_places=2)
    daily_feed_kg = models.DecimalField(max_digits=12, decimal_places=3)
    daily_mortality_percent = models.DecimalField(max_digits=6, decimal_places=2)
    temperature_c = models.DecimalField(max_digits=6, decimal_places=2)
    dissolved_oxygen_mg_l = models.DecimalField(max_digits=6, decimal_places=2)
    ph = models.DecimalField(max_digits=5, decimal_places=2)
    projected_survivors = models.PositiveIntegerField()
    projected_biomass_kg = models.DecimalField(max_digits=14, decimal_places=2)
    total_feed_kg = models.DecimalField(max_digits=14, decimal_places=2)
    estimated_fcr = models.DecimalField(max_digits=10, decimal_places=2)
    warnings = models.JSONField(default=list, blank=True)
    daily_projection = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "simulation_runs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["farm", "-created_at"]),
            models.Index(fields=["pond", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.pond} simulation run {self.id}"
