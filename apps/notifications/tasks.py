"""Celery tasks for the notification outbox."""

from __future__ import annotations

from celery import shared_task
from django.conf import settings

from apps.notifications.models import Notification
from apps.notifications.services import dispatch_notification


@shared_task
def dispatch_pending_notifications(limit: int | None = None) -> int:
    batch_size = limit or settings.NOTIFICATION_BATCH_SIZE
    notifications = Notification.objects.filter(status=Notification.Status.PENDING).order_by(
        "created_at"
    )[:batch_size]
    dispatched = 0
    for notification in notifications:
        dispatch_notification(notification)
        dispatched += 1
    return dispatched
