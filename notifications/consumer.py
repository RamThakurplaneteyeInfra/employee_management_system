"""
Unified WebSocket consumers: Chat (real-time messaging) + Notifications.
Production-ready with validation, error handling, and consistent event format.
"""
import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.contrib.auth.models import User

from Messaging.models import IndividualChats, IndividualMessages, GroupChats, GroupMessages, GroupMembers
from accounts.filters import get_created_time_format


# =============================================================================
# ChatConsumer – Real-time chat for group and individual conversations
# Connect: ws://host/ws/chat/<chat_id>/
# =============================================================================
class ChatConsumer(AsyncWebsocketConsumer):
    """Handles real-time chat messaging for group (G*) and individual (C*) chat rooms."""

    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.room_name = f"chat_{self.chat_id}"
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close(code=4001)
            return

        allowed = await sync_to_async(self._validate_chat_access)(user)
        if not allowed:
            await self.close(code=4004)
            return

        self._allowed_obj = allowed
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
            return

        message = (data.get("message") or "").strip()
        if not message:
            await self.send(text_data=json.dumps({"error": "Message required"}))
            return

        sender = self.scope["user"]
        result = await self._save_message(sender.username, message)
        if isinstance(result, dict) and "error" in result:
            await self.send(text_data=json.dumps(result))
            return

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat_message",
                "sender": sender.username,
                "message": message,
                "at": get_created_time_format(result.created_at),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "sender": event["sender"],
            "message": event["message"],
            "at": event.get("at", ""),
        }))

    def _validate_chat_access(self, user):
        try:
            if self.chat_id.startswith("G"):
                return GroupChats.objects.get(group_id=self.chat_id)
            return IndividualChats.objects.get(chat_id=self.chat_id)
        except (GroupChats.DoesNotExist, IndividualChats.DoesNotExist):
            return None

    async def _save_message(self, sender_username, message):
        def _save():
            try:
                sender = User.objects.get(username=sender_username)
                if self.chat_id.startswith("G"):
                    return GroupMessages.objects.create(group=self._allowed_obj, sender=sender, content=message)
                return IndividualMessages.objects.create(chat=self._allowed_obj, sender=sender, content=message)
            except User.DoesNotExist:
                return {"error": "User not found"}
            except Exception as e:
                return {"error": str(e)}

        return await sync_to_async(_save)()


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
            print(user)
            await self.close(code=4001)
            return

        self.room_name = f"user_{user.username}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        print("disconnecting")
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
            "type": "notification",
            "title": event.get("title", "Notification"),
            "message": event.get("message", ""),
            "extra": event.get("extra", {}),
        }
        await self.send(text_data=json.dumps(payload))
