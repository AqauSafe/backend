"""Realtime farm event broadcasting over Channels."""

from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def farm_group_name(farm_id) -> str:
    return f"farm.{farm_id}"


def broadcast_farm_event(farm_id, event: str, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            farm_group_name(farm_id),
            {"type": "farm.event", "event": event, "payload": payload},
        )
    except Exception:
        logger.warning("Realtime broadcast failed; continuing without delivery.", exc_info=True)
