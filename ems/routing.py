"""
ASGI WebSocket routing. All WebSocket consumers are centralized in notifications app.
"""
from channels.routing import URLRouter
from notifications.routing import websocket_urlpatterns
