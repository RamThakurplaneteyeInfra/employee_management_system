"""
ASGI WebSocket routing. All WebSocket consumers are centralized in notifications app.
"""
from channels.routing import URLRouter
# from notifications.routing import websocket_urlpatterns

from django.urls import path
from notifications.consumer import NotificationConsumer
from Calling.consumer import CallConsumer

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/calls/", CallConsumer.as_asgi())
]
