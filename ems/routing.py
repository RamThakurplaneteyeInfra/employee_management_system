"""
ASGI WebSocket routing. All WebSocket consumers are centralized here.
"""
from channels.routing import URLRouter
from django.urls import path
from notifications.consumer import NotificationConsumer
from Calling.consumer import CallConsumer
from Messaging.consumers import ChatConsumer

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/calls/", CallConsumer.as_asgi()),
    path("ws/chat/", ChatConsumer.as_asgi()),
]
