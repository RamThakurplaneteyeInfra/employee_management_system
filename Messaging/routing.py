from django.urls import path
from .consumer import ChatConsumer

websocket_urlpatterns = [
    path("ws/chat/<slug:chat_id>/", ChatConsumer.as_asgi()),
]