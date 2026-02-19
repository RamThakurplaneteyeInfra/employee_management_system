"""
WebSocket URL routing.
- ws/notifications/  : User notifications only
"""
from django.urls import path
from .consumer import NotificationConsumer

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
