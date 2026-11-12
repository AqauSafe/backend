"""Authenticated WebSocket stream for farm events."""

from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from apps.farms.access import can_view_farm
from apps.farms.models import Farm
from apps.telemetry.realtime import farm_group_name


@database_sync_to_async
def _user_from_token(token: str):
    try:
        payload = AccessToken(token)
        user_id = payload.get("user_id")
    except Exception:  # noqa: BLE001
        return None
    return get_user_model().objects.filter(id=user_id, is_active=True).first()


@database_sync_to_async
def _can_view(user, farm_id: str) -> bool:
    farm = Farm.objects.filter(id=farm_id).first()
    return farm is not None and can_view_farm(user, farm)


class FarmStreamConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.farm_id = str(self.scope["url_route"]["kwargs"]["farm_id"])
        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [""])[0]
        user = await _user_from_token(token) if token else None
        if user is None or not await _can_view(user, self.farm_id):
            await self.close(code=4401)
            return
        self.group_name = farm_group_name(self.farm_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def farm_event(self, message):
        await self.send_json({"event": message["event"], "data": message["payload"]})
