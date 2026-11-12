"""Run the AquaSafe MQTT ingress worker."""

from __future__ import annotations

import logging
import time
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from integrations.mqtt.handlers import handle_message
from integrations.mqtt.topics import subscription_topics

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Subscribe to device MQTT topics and persist telemetry, status and acknowledgements."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Connect, report and exit.")

    def handle(self, *args, **options):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise CommandError("paho-mqtt is not installed.") from exc

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"aquasafe-backend-{uuid.uuid4().hex[:8]}",
        )
        if settings.MQTT_USERNAME:
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        if settings.MQTT_TLS:
            client.tls_set(ca_certs=settings.MQTT_CA_CERTS or None)

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code != 0:
                logger.error("MQTT connection failed: %s", reason_code)
                return
            for topic, qos in subscription_topics():
                client.subscribe(topic, qos=qos)
            logger.info("MQTT worker subscribed to %d topic filters.", len(subscription_topics()))

        def on_message(client, userdata, message):
            try:
                result = handle_message(message.topic, message.payload)
                logger.info("MQTT %s -> %s", message.topic, result)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to process MQTT message on %s", message.topic)

        client.on_connect = on_connect
        client.on_message = on_message
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        try:
            client.connect(settings.MQTT_HOST, settings.MQTT_PORT, settings.MQTT_KEEPALIVE)
        except OSError as exc:
            raise CommandError(f"Unable to connect to MQTT broker: {exc}") from exc
        client.loop_start()
        if options["once"]:
            time.sleep(1)
            client.loop_stop()
            client.disconnect()
            return
        self.stdout.write(self.style.SUCCESS("MQTT worker running. Press Ctrl+C to stop."))
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.loop_stop()
            client.disconnect()
