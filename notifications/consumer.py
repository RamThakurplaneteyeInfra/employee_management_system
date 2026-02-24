"""
WebSocket consumer: NotificationConsumer only.
Handles real-time notifications per user via channel_layer.group_send("user_<username>", ...).
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


# =============================================================================
# NotificationConsumer – User-specific notification stream
# Connect: ws://host/ws/notifications/
# Receives: send_notification events from channel_layer.group_send("user_<username>", ...)
# =============================================================================
class NotificationConsumer(AsyncWebsocketConsumer):
    """Handles real-time notifications per user. Join group user_<username>."""

    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close(code=4001)
            return

        self.room_name = f"user_{user.username}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        """Optional: handle client pings/heartbeats."""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong", "message": "ok"}))
        except json.JSONDecodeError:
            pass

    async def send_notification(self, event):
        """Handler for channel_layer group_send type='send_notification'."""
        payload = {
            "category": event.get("category", None),
            "title": event.get("title", ""),
            "message": event.get("message", ""),
            "from":event.get("from", None),
            "extra": event.get("extra", {}),
        }
        await self.send(text_data=json.dumps(payload))
