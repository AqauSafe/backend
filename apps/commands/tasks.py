"""Celery tasks for device command lifecycle."""

from celery import shared_task

from apps.commands.services import expire_commands


@shared_task
def expire_device_commands() -> int:
    return expire_commands()
