"""Development-only bridge for the canonical fish_pond-live.html demo."""

from __future__ import annotations

import json
import logging
import time
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.farms.models import Pond
from apps.simulations.services import ingest_simulation_state, normalise_legacy_reading

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Subscribe to the legacy fish_pond-live.html MQTT topic and store simulated readings."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Connect, report and exit.")

    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.SIMULATION_LEGACY_BRIDGE_ENABLED:
            raise CommandError(
                "The legacy simulation bridge is disabled. Set DEBUG=true and "
                "SIMULATION_LEGACY_BRIDGE_ENABLED=true for local development only."
            )
        pond = (
            Pond.objects.select_related("farm")
            .filter(id=settings.SIMULATION_LEGACY_BRIDGE_POND_ID)
            .first()
        )
        if pond is None:
            raise CommandError("SIMULATION_LEGACY_BRIDGE_POND_ID does not match a pond.")

        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise CommandError("paho-mqtt is not installed.") from exc

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"aquasafe-legacy-bridge-{uuid.uuid4().hex[:8]}",
        )

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code != 0:
                logger.error("Legacy bridge MQTT connection failed: %s", reason_code)
                return
            client.subscribe(settings.SIMULATION_LEGACY_TOPIC, qos=0)
            logger.info("Legacy bridge subscribed to %s", settings.SIMULATION_LEGACY_TOPIC)

        def on_message(client, userdata, message):
            try:
                payload = json.loads(message.payload.decode())
                if not isinstance(payload, dict):
                    return
                values, raw = normalise_legacy_reading(payload)
                if not values:
                    logger.warning("Legacy reading contained no usable sensor values: %s", raw)
                    return
                simulation, reading = ingest_simulation_state(
                    pond=pond,
                    values=values,
                    client_id=str(payload.get("id") or payload.get("message_id") or ""),
                    raw=raw,
                )
                logger.info("Legacy reading %s -> simulation %s", reading.id, simulation.id)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to process legacy simulation message")

        client.on_connect = on_connect
        client.on_message = on_message
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        try:
            client.connect(
                settings.SIMULATION_LEGACY_MQTT_HOST,
                settings.SIMULATION_LEGACY_MQTT_PORT,
                settings.MQTT_KEEPALIVE,
            )
        except OSError as exc:
            raise CommandError(f"Unable to connect to legacy MQTT broker: {exc}") from exc
        client.loop_start()
        if options["once"]:
            time.sleep(1)
            client.loop_stop()
            client.disconnect()
            return
        self.stdout.write(
            self.style.SUCCESS("Legacy simulation bridge running. Press Ctrl+C to stop.")
        )
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.loop_stop()
            client.disconnect()
