"""Alert evaluation foundation."""

from __future__ import annotations

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.alerts.models import Alert, AlertRule
from apps.telemetry.models import SensorReading

METRIC_LABELS = {
    "temperature": "Temperature",
    "oxygen": "Dissolved oxygen",
    "ph": "pH",
    "level": "Water level",
}


def evaluate_reading(reading: SensorReading) -> list[Alert]:
    """Create at most one active alert per matching rule and pond."""
    farm = reading.pond.farm
    rules = AlertRule.objects.filter(is_active=True, farm=farm).filter(
        Q(pond=reading.pond) | Q(pond__isnull=True)
    )
    generated: list[Alert] = []
    for rule in rules:
        value = getattr(reading, rule.metric, None)
        if value is None or not rule.matches(value):
            continue

        existing = Alert.objects.filter(rule=rule, pond=reading.pond, status=Alert.Status.ACTIVE)
        if existing.exists():
            existing.update(value=value, reading=reading)
            continue

        recent = Alert.objects.filter(
            rule=rule,
            pond=reading.pond,
            status=Alert.Status.RESOLVED,
            resolved_at__gte=timezone.now() - timedelta(minutes=rule.cooldown_minutes),
        ).exists()
        if recent:
            continue

        message = (
            f"{METRIC_LABELS.get(rule.metric, rule.metric)} is {value} "
            f"({rule.get_operator_display()} {rule.threshold})."
        )
        try:
            with transaction.atomic():
                alert = Alert.objects.create(
                    farm=farm,
                    pond=reading.pond,
                    rule=rule,
                    device=reading.device,
                    reading=reading,
                    metric=rule.metric,
                    value=value,
                    threshold=rule.threshold,
                    severity=rule.severity,
                    message=message,
                    triggered_at=reading.recorded_at,
                )
        except IntegrityError:
            alert = Alert.objects.filter(
                rule=rule, pond=reading.pond, status=Alert.Status.ACTIVE
            ).first()
        if alert is not None:
            generated.append(alert)
    return generated
