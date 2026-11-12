"""HMAC signing for device commands."""

from __future__ import annotations

import hashlib
import hmac
import json


def command_canonical(command) -> str:
    payload = json.dumps(command.payload, sort_keys=True, separators=(",", ":"))
    return "\n".join(
        [
            str(command.id),
            command.device.device_id,
            command.command_type,
            command.expires_at.isoformat(),
            payload,
        ]
    )


def command_message(command) -> dict:
    return {
        "command_id": str(command.id),
        "device_id": command.device.device_id,
        "type": command.command_type,
        "payload": command.payload,
        "expires_at": command.expires_at.isoformat(),
        "signature": command.signature,
    }


def sign_command(secret: str, command) -> str:
    return hmac.new(
        secret.encode(), command_canonical(command).encode(), hashlib.sha256
    ).hexdigest()


def verify_command(secret: str, command, signature: str) -> bool:
    expected = sign_command(secret, command)
    return hmac.compare_digest(expected, signature)


def sign_telemetry(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify_telemetry(secret: str, payload: str, signature: str) -> bool:
    return hmac.compare_digest(sign_telemetry(secret, payload), signature)
