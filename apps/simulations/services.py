"""Simulation calculations and ingestion."""

from __future__ import annotations

import math
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.utils import timezone

from apps.alerts.services import evaluate_reading
from apps.simulations.models import Simulation
from apps.telemetry.models import ReadingSource, SensorReading
from apps.telemetry.realtime import broadcast_farm_event

FORMULA_VERSION = "aquasafe-simple-v1"
WARNING_TEMPERATURE = "Temperature is outside the model's preferred 26–30°C planning range."
WARNING_OXYGEN = "Dissolved oxygen is below the 5 mg/L planning threshold."
WARNING_PH = "pH is outside the model's preferred 6.5–8.5 planning range."


def _round_half_up(value: float, places: int = 2) -> float:
    quantizer = Decimal("1").scaleb(-places)
    try:
        return float(Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP))
    except InvalidOperation:
        return 0.0


def calculate_simulation(
    *,
    population: int,
    duration_days: int,
    starting_weight_g: float,
    daily_growth_g: float,
    daily_feed_kg: float,
    daily_mortality_percent: float,
    temperature_c: float,
    dissolved_oxygen_mg_l: float,
    ph: float,
) -> dict:
    """Port the deterministic calculator in frontend `test1.tsx`."""
    temperature_stress = temperature_c < 26 or temperature_c > 30
    oxygen_stress = dissolved_oxygen_mg_l < 5
    ph_stress = ph < 6.5 or ph > 8.5
    daily_stress_penalty = (
        (0.0005 if temperature_stress else 0)
        + (0.001 if oxygen_stress else 0)
        + (0.0005 if ph_stress else 0)
    )
    daily_loss_rate = min(0.05, daily_mortality_percent / 100 + daily_stress_penalty)
    projected_survivors = max(
        0,
        int(math.floor(population * math.pow(1 - daily_loss_rate, duration_days) + 0.5)),
    )
    projected_average_weight_g = starting_weight_g + daily_growth_g * duration_days
    projected_biomass_kg = projected_survivors * projected_average_weight_g / 1000
    initial_biomass_kg = population * starting_weight_g / 1000
    total_feed_kg = daily_feed_kg * duration_days
    biomass_gain_kg = max(0, projected_biomass_kg - initial_biomass_kg)
    estimated_fcr = total_feed_kg / biomass_gain_kg if biomass_gain_kg > 0 else 0
    warnings = [
        *([WARNING_TEMPERATURE] if temperature_stress else []),
        *([WARNING_OXYGEN] if oxygen_stress else []),
        *([WARNING_PH] if ph_stress else []),
    ]

    daily_projection = []
    for day in range(1, duration_days + 1):
        day_survivors = max(
            0, int(math.floor(population * math.pow(1 - daily_loss_rate, day) + 0.5))
        )
        day_weight = starting_weight_g + daily_growth_g * day
        daily_projection.append(
            {
                "day": day,
                "survivors": day_survivors,
                "averageWeightG": _round_half_up(day_weight),
                "biomassKg": _round_half_up(day_survivors * day_weight / 1000),
                "cumulativeFeedKg": _round_half_up(daily_feed_kg * day),
            }
        )

    return {
        "formula_version": FORMULA_VERSION,
        "projected_survivors": projected_survivors,
        "projected_biomass_kg": _round_half_up(projected_biomass_kg),
        "total_feed_kg": _round_half_up(total_feed_kg),
        "estimated_fcr": _round_half_up(estimated_fcr),
        "warnings": warnings,
        "daily_projection": daily_projection,
    }


def ingest_simulation_state(
    *,
    pond,
    values: dict,
    recorded_at: datetime | None = None,
    client_id: str = "",
    message_id: str = "",
    raw: dict | None = None,
) -> tuple[Simulation, SensorReading]:
    """Persist simulated state and a distinguishable sensor reading."""
    recorded_at = recorded_at or timezone.now()
    simulation, _ = Simulation.objects.get_or_create(pond=pond, defaults={"farm": pond.farm})
    if simulation.farm_id != pond.farm_id:
        simulation.farm = pond.farm
    simulation.state = {
        "temperature": values.get("temperature"),
        "oxygen": values.get("oxygen"),
        "ph": values.get("ph"),
        "level": values.get("level"),
        "turbidityNtu": values.get("turbidity_ntu"),
        "recordedAt": recorded_at.isoformat(),
    }
    simulation.last_state_at = recorded_at
    simulation.save(update_fields=["farm", "state", "last_state_at", "updated_at"])
    reading = SensorReading.objects.create(
        pond=pond,
        source=ReadingSource.SIMULATION,
        recorded_at=recorded_at,
        client_id=client_id,
        message_id=message_id,
        raw=raw or values,
        metadata={"simulation": True},
        **values,
    )
    evaluate_reading(reading)
    broadcast_farm_event(
        pond.farm_id,
        "simulation.state",
        {
            "pondId": str(pond.id),
            "simulationId": str(simulation.id),
            "readingId": str(reading.id),
            "recordedAt": recorded_at.isoformat(),
            "state": simulation.state,
        },
    )
    return simulation, reading


def normalise_legacy_reading(payload: dict) -> tuple[dict, dict]:
    """Map the HTML demo's raw 0..1023 ADC values to physical units."""
    raw = dict(payload)

    def number(key):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    oxygen = number("do")
    if oxygen is None and (raw_o := number("o")) is not None:
        oxygen = max(0.0, min(12.0, raw_o / 1023 * 12))
    ph = number("ph")
    if ph is None and (raw_p := number("p")) is not None:
        ph = max(0.0, min(14.0, raw_p / 1023 * 14))
    level = number("lvl")
    if level is None and (raw_l := number("l")) is not None:
        level = max(0.0, min(100.0, raw_l / 1023 * 100))
    turbidity = number("ntu")
    if turbidity is None and (raw_t := number("t")) is not None:
        turbidity = max(0.0, min(100.0, raw_t / 1023 * 100))

    values = {
        "temperature": number("temp") or number("temperature"),
        "oxygen": oxygen,
        "ph": ph,
        "level": level,
        "turbidity_ntu": turbidity,
    }
    values = {key: value for key, value in values.items() if value is not None}
    if turbidity is not None:
        raw["turbidityNtu"] = turbidity
    return values, raw
