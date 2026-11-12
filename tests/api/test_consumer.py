from __future__ import annotations

import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from apps.telemetry.realtime import farm_group_name
from config.asgi import application


@database_sync_to_async
def access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_farm_stream_requires_authentication(farm):
    communicator = WebsocketCommunicator(
        application,
        f"/ws/farms/{farm.id}/",
        headers=[(b"origin", b"http://testserver")],
    )

    connected, code = await communicator.connect()

    assert connected is False
    assert code == 4401


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_farm_stream_receives_group_events(farm, user):
    token = await access_token_for(user)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/farms/{farm.id}/?token={token}",
        headers=[(b"origin", b"http://testserver")],
    )

    connected, _ = await communicator.connect()
    assert connected is True

    await get_channel_layer().group_send(
        farm_group_name(farm.id),
        {
            "type": "farm.event",
            "event": "reading.created",
            "payload": {"pondId": "pond-1", "oxygen": "6.1"},
        },
    )

    message = await communicator.receive_json_from()
    assert message["event"] == "reading.created"
    assert message["data"]["oxygen"] == "6.1"
    await communicator.disconnect()


def test_broadcast_failure_does_not_break_persistence(monkeypatch):
    from apps.telemetry import realtime

    class BrokenLayer:
        async def group_send(self, *args, **kwargs):
            raise RuntimeError("redis unavailable")

    monkeypatch.setattr(realtime, "get_channel_layer", lambda: BrokenLayer())
    realtime.broadcast_farm_event("farm-id", "test.event", {"ok": True})
