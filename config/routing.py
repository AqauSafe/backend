"""WebSocket URL routing."""

from django.urls import path

from apps.telemetry.consumers import FarmStreamConsumer

websocket_urlpatterns = [
    path("ws/farms/<uuid:farm_id>/", FarmStreamConsumer.as_asgi()),
]
