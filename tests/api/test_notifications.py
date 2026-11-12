from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.core import mail

from apps.alerts.models import Alert, AlertRule
from apps.alerts.services import evaluate_reading
from apps.notifications.models import Notification
from apps.notifications.services import (
    dispatch_notification,
    queue_alert_notifications,
)
from apps.telemetry.models import SensorReading


def make_alert(farm, pond) -> Alert:
    AlertRule.objects.create(
        farm=farm,
        metric="oxygen",
        operator="lt",
        threshold="5.00",
        severity="critical",
        created_by=farm.owner,
    )
    reading = SensorReading.objects.create(
        pond=pond,
        oxygen=Decimal("4.0"),
        recorded_at=datetime(2026, 11, 11, 9, tzinfo=UTC),
        client_id="notification-reading",
    )
    evaluate_reading(reading)
    return Alert.objects.get(farm=farm, status=Alert.Status.ACTIVE)


@pytest.mark.django_db
def test_alert_queues_one_notification_per_manager(farm, pond):
    alert = make_alert(farm, pond)

    notification = Notification.objects.get(alert=alert)
    assert notification.status == Notification.Status.PENDING
    assert notification.recipient == farm.owner.email
    assert notification.subject.startswith("[AquaSafe] Critical alert")
    assert "Pond A" in notification.body

    queue_alert_notifications(alert)
    assert Notification.objects.filter(alert=alert).count() == 1


@pytest.mark.django_db
def test_dispatch_skips_when_email_delivery_is_disabled(farm, pond, settings):
    settings.NOTIFICATION_EMAIL_ENABLED = False
    notification = Notification.objects.create(
        farm=farm,
        user=farm.owner,
        recipient=farm.owner.email,
        subject="Test",
        body="Body",
        dedupe_key="test-disabled",
    )

    dispatch_notification(notification)

    notification.refresh_from_db()
    assert notification.status == Notification.Status.SKIPPED
    assert "disabled" in notification.error
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_dispatch_sends_email_when_enabled(farm, pond, settings, mailoutbox):
    settings.NOTIFICATION_EMAIL_ENABLED = True
    notification = Notification.objects.create(
        farm=farm,
        user=farm.owner,
        recipient=farm.owner.email,
        subject="Test alert",
        body="Low oxygen",
        dedupe_key="test-enabled",
    )

    dispatch_notification(notification)

    notification.refresh_from_db()
    assert notification.status == Notification.Status.SENT
    assert notification.sent_at is not None
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [farm.owner.email]
