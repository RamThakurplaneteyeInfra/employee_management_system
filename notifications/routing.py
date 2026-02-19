"""
WebSocket URL routing.
- ws/chat/<chat_id>/ : Real-time chat (group/individual)
- ws/notifications/  : User notifications
"""
from django.urls import path
from .consumer import ChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    path("ws/chat/<slug:chat_id>/", ChatConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
