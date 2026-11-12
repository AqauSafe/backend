"""MQTT topic conventions shared by the backend and firmware."""

from django.conf import settings


def prefix() -> str:
    return settings.MQTT_TOPIC_PREFIX.rstrip("/")


def device_topic(device_id: str, suffix: str) -> str:
    return f"{prefix()}/devices/{device_id}/{suffix.lstrip('/')}"


def telemetry_topic(device_id: str) -> str:
    return device_topic(device_id, "telemetry")


def heartbeat_topic(device_id: str) -> str:
    return device_topic(device_id, "heartbeat")


def events_topic(device_id: str) -> str:
    return device_topic(device_id, "events")


def status_topic(device_id: str) -> str:
    return device_topic(device_id, "status")


def commands_topic(device_id: str) -> str:
    return device_topic(device_id, "commands")


def command_ack_topic(device_id: str) -> str:
    return device_topic(device_id, "command-acks")


def config_topic(device_id: str) -> str:
    return device_topic(device_id, "config")


def config_ack_topic(device_id: str) -> str:
    return device_topic(device_id, "config-ack")


def subscription_topics() -> list[tuple[str, int]]:
    qos = settings.MQTT_QOS
    return [
        (f"{prefix()}/devices/+/telemetry", qos),
        (f"{prefix()}/devices/+/heartbeat", qos),
        (f"{prefix()}/devices/+/events", qos),
        (f"{prefix()}/devices/+/status", qos),
        (f"{prefix()}/devices/+/command-acks", qos),
        (f"{prefix()}/devices/+/config-ack", qos),
    ]
