"""
Real-Time Chat WebSocket consumer: /ws/chat/
Auth: Session-based (same as /ws/notifications/ and /ws/calls/). Cookie must be sent with the handshake.
Supports: subscribe/unsubscribe, typing_start/typing_stop, mark_seen.
Server pushes: new_message, message_edited, chat_updated, messages_seen, user_typing.
"""
import asyncio
import json
import logging
from asgiref.sync import sync_to_async

from channels.generic.websocket import AsyncWebsocketConsumer

from .chat_ws_utils import user_can_access_chat, mark_seen_sync

logger = logging.getLogger(__name__)

CHAT_GROUP_PREFIX = "chat_"
TYPING_EXPIRE_SECONDS = 8


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket for real-time chat: subscribe per chat_id, typing indicators, read receipts.
    Session auth on connect (scope["user"] from AuthMiddlewareStack); reject if anonymous.
    """

    async def connect(self):
        self._subscribed_chats = set()
        self._typing_tasks = {}
        user = self.scope.get("user")
        if user is None or getattr(user, "is_anonymous", True):
            logger.warning(
                "ChatConsumer connect rejected: anonymous or missing user (path=%s)",
                self.scope.get("path"),
            )
            await self.close(code=4001)
            return
        await self.accept()

    async def disconnect(self, close_code):
        for task in getattr(self, "_typing_tasks", {}).values():
            task.cancel()
        self._typing_tasks.clear()
        for chat_id in list(getattr(self, "_subscribed_chats", set())):
            await self._leave_chat_group(chat_id)

    async def _leave_chat_group(self, chat_id):
        group = f"{CHAT_GROUP_PREFIX}{chat_id}"
        try:
            await self.channel_layer.group_discard(group, self.channel_name)
        except Exception:
            pass
        self._subscribed_chats.discard(chat_id)

    async def _join_chat_group(self, chat_id):
        allowed = await sync_to_async(user_can_access_chat)(self.scope["user"], chat_id)
        if not allowed:
            return False
        group = f"{CHAT_GROUP_PREFIX}{chat_id}"
        await self.channel_layer.group_add(group, self.channel_name)
        self._subscribed_chats.add(chat_id)
        return True

    async def receive(self, text_data):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return

        msg_type = data.get("type")
        chat_id = data.get("chat_id")
        if chat_id is not None:
            chat_id = str(chat_id).strip() or None

        if msg_type == "subscribe":
            if chat_id:
                ok = await self._join_chat_group(chat_id)
                if not ok:
                    await self.send(text_data=json.dumps({"type": "error", "message": "Not a participant"}))
            return

        if msg_type == "unsubscribe":
            if chat_id:
                await self._leave_chat_group(chat_id)
            return

        if msg_type == "typing_start":
            if chat_id:
                await self._handle_typing(chat_id, True)
            return

        if msg_type == "typing_stop":
            if chat_id:
                await self._handle_typing(chat_id, False)
            return

        if msg_type == "mark_seen":
            if not chat_id:
                await self.send(text_data=json.dumps({"type": "error", "message": "chat_id required"}))
                return
            user_id = data.get("user_id")
            if user_id is not None and str(user_id).strip() != self.scope["user"].username:
                await self.send(text_data=json.dumps({"type": "error", "message": "user_id must match logged-in user"}))
                return
            payload, err = await sync_to_async(mark_seen_sync)(
                self.scope["user"], chat_id,
                message_ids=None,
                last_message_id=None,
            )
            if err:
                await self.send(text_data=json.dumps({"type": "error", "message": err}))
                return
            group = f"{CHAT_GROUP_PREFIX}{chat_id}"
            await self.channel_layer.group_send(
                group,
                {
                    "type": "chat.messages_seen",
                    "chat_id": chat_id,
                    "payload": payload,
                },
            )
            await self.send(text_data=json.dumps({
                "type": "unseen_count_updated",
                "chat_id": chat_id,
                "unseen_count": 0,
            }))
            return

    async def _handle_typing(self, chat_id, is_typing):
        user = self.scope["user"]
        key = (chat_id, user.username)
        if key in self._typing_tasks:
            self._typing_tasks[key].cancel()
            del self._typing_tasks[key]
        if not is_typing:
            await self._broadcast_typing(chat_id, user, False)
            return
        await self._broadcast_typing(chat_id, user, True)
        task = asyncio.create_task(self._typing_expire(chat_id))
        self._typing_tasks[key] = task

    async def _typing_expire(self, chat_id):
        try:
            await asyncio.sleep(TYPING_EXPIRE_SECONDS)
        except asyncio.CancelledError:
            return
        finally:
            user = self.scope["user"]
            key = (chat_id, user.username)
            self._typing_tasks.pop(key, None)
        await self._broadcast_typing(chat_id, user, False)

    async def _broadcast_typing(self, chat_id, user, is_typing):
        from accounts.filters import _get_users_Name_sync
        user_name = await sync_to_async(_get_users_Name_sync)(user)
        group = f"{CHAT_GROUP_PREFIX}{chat_id}"
        await self.channel_layer.group_send(
            group,
            {
                "type": "chat.user_typing",
                "chat_id": chat_id,
                "user_id": user.username,
                "user_name": user_name or user.username,
                "is_typing": is_typing,
            },
        )

    async def chat_new_message(self, event):
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "chat_id": event.get("chat_id"),
            "message": payload,
        }))

    async def chat_message_edited(self, event):
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps({
            "type": "message_edited",
            "chat_id": event.get("chat_id"),
            "message": payload,
        }))

    async def chat_chat_updated(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_updated",
            "chat_id": event.get("chat_id"),
            "last_message_at": event.get("last_message_at"),
            "last_message_preview": event.get("last_message_preview", ""),
            "unseen_count": event.get("unseen_count", 0),
        }))

    async def chat_messages_seen(self, event):
        payload = event.get("payload", {})
        seen_by = payload.get("seen_by")
        if seen_by == self.scope["user"].username:
            return
        await self.send(text_data=json.dumps({
            "type": "messages_seen",
            "chat_id": event.get("chat_id"),
            "seen_by": payload.get("seen_by"),
            "seen_by_name": payload.get("seen_by_name"),
            "message_ids": payload.get("message_ids", []),
            "last_seen_message_id": payload.get("last_seen_message_id"),
            "seen_at": payload.get("seen_at"),
        }))

    async def chat_user_typing(self, event):
        if event.get("user_id") == self.scope["user"].username:
            return
        await self.send(text_data=json.dumps({
            "type": "user_typing",
            "chat_id": event.get("chat_id"),
            "user_id": event.get("user_id"),
            "user_name": event.get("user_name"),
            "is_typing": event.get("is_typing", False),
        }))

    async def chat_unseen_count_updated(self, event):
        """Deliver unseen_count only to the user it applies to (for_user)."""
        for_user = event.get("for_user")
        if for_user != self.scope["user"].username:
            return
        await self.send(text_data=json.dumps({
            "type": "unseen_count_updated",
            "chat_id": event.get("chat_id"),
            "unseen_count": event.get("unseen_count", 0),
        }))
