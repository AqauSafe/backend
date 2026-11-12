"""Best-effort MQTT publishing used by API requests and workers."""

from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def publish_message(topic: str, payload: dict, *, qos: int | None = None, retain: bool = False):
    import paho.mqtt.publish as mqtt_publish

    auth = None
    if settings.MQTT_USERNAME:
        auth = {"username": settings.MQTT_USERNAME, "password": settings.MQTT_PASSWORD}
    return mqtt_publish.single(
        topic,
        payload=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        qos=settings.MQTT_QOS if qos is None else qos,
        retain=retain,
        hostname=settings.MQTT_HOST,
        port=settings.MQTT_PORT,
        auth=auth,
        tls={"ca_certs": settings.MQTT_CA_CERTS} if settings.MQTT_TLS else None,
        keepalive=settings.MQTT_KEEPALIVE,
    )
