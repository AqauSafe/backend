"""Notification queueing and delivery."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.farms.models import FarmMembership
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


def _alert_recipients(alert):
    farm = alert.farm
    users = {}
    if farm.owner_id:
        users[farm.owner_id] = farm.owner
    for membership in FarmMembership.objects.filter(
        farm=farm,
        role__in=[FarmMembership.Role.OWNER, FarmMembership.Role.MANAGER],
    ).select_related("user"):
        users[membership.user_id] = membership.user
    return [user for user in users.values() if user.is_active and user.email]


def queue_alert_notifications(alert) -> list[Notification]:
    """Create one idempotent email outbox item per farm manager."""
    notifications: list[Notification] = []
    for user in _alert_recipients(alert):
        subject = f"[AquaSafe] {alert.get_severity_display()} alert: {alert.metric}"
        location = alert.pond.name if alert.pond else alert.farm.name
        body = (
            f"{alert.message}\n\n"
            f"Farm: {alert.farm.name}\n"
            f"Pond: {location}\n"
            f"Severity: {alert.get_severity_display()}\n"
            f"Triggered: {alert.triggered_at.isoformat()}\n"
        )
        dedupe_key = f"alert:{alert.id}:email:{user.id}"
        notification, created = Notification.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults={
                "alert": alert,
                "farm": alert.farm,
                "user": user,
                "recipient": user.email,
                "subject": subject[:255],
                "body": body,
                "metadata": {"alertId": str(alert.id), "userId": str(user.id)},
            },
        )
        if created:
            notifications.append(notification)
    return notifications


def dispatch_notification(notification: Notification) -> Notification:
    if notification.status != Notification.Status.PENDING:
        return notification
    if not settings.NOTIFICATION_EMAIL_ENABLED:
        notification.status = Notification.Status.SKIPPED
        notification.error = "Email notification delivery is disabled."
        notification.save(update_fields=["status", "error", "updated_at"])
        return notification
    if not notification.recipient:
        notification.status = Notification.Status.SKIPPED
        notification.error = "Recipient has no email address."
        notification.save(update_fields=["status", "error", "updated_at"])
        return notification

    try:
        send_mail(
            notification.subject,
            notification.body,
            settings.DEFAULT_FROM_EMAIL,
            [notification.recipient],
            fail_silently=False,
        )
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.error = ""
        notification.save(update_fields=["status", "sent_at", "error", "updated_at"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Notification %s delivery failed", notification.id)
        notification.status = Notification.Status.FAILED
        notification.error = str(exc)[:4000]
        notification.save(update_fields=["status", "error", "updated_at"])
    return notification
