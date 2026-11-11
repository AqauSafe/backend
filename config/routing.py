"""WebSocket URL routing.

Consumers are added as each realtime feature lands. Keeping the router here
means the ASGI entry point does not change as features are added.
"""

websocket_urlpatterns: list = []
