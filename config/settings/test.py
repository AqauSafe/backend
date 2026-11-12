"""Test settings: PostgreSQL test database, in-memory services."""

from .base import *  # noqa: F403

DEBUG = False

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES["default"]["TEST"] = {"NAME": "aquasafe_test"}  # noqa: F405

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEVICE_SECRET_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "auth": "100000/min",
    "register": "100000/min",
    "password": "100000/min",
    "telemetry": "100000/min",
    "provision": "100000/min",
}
