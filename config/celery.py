"""Celery application configuration for AquaSafe."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("aquasafe")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
