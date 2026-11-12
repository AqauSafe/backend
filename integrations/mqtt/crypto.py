"""Fernet encryption for device credentials and command secrets."""

from __future__ import annotations

import base64
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet() -> Fernet:
    key = settings.DEVICE_SECRET_ENCRYPTION_KEY
    if not key:
        if not settings.DEBUG:
            raise ImproperlyConfigured(
                "DEVICE_SECRET_ENCRYPTION_KEY is required outside development."
            )
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ImproperlyConfigured("Unable to decrypt device secret.") from exc


def generate_mqtt_password() -> str:
    return secrets.token_urlsafe(32)
