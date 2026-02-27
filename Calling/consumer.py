"""
WebSocket consumer for calls: incoming call notifications + WebRTC signaling.
Connect: ws://host/ws/calls/

WebRTC signaling flow:
1. Caller creates offer -> sends webrtc_offer to callee via this consumer
2. Callee receives offer -> creates answer -> sends webrtc_answer to caller
3. Both peers exchange ice_candidate for NAT traversal
4. Either peer can send end_call to notify the other
All signaling is relayed via channel layer; media is peer-to-peer (WebRTC).
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

# Only process these message types; ignore unknown types
KNOWN_MESSAGE_TYPES = frozenset({"webrtc_offer", "webrtc_answer", "ice_candidate", "end_call"})


class CallConsumer(AsyncWebsocketConsumer):
    """WebSocket for calls: incoming call notifications + WebRTC offer/answer/ICE + group calls."""

    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return
        self.room_name = f"call_{user.username}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        self.group_call_rooms = set()  # group_call_{id} names for leave on disconnect
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        for group_name in getattr(self, "group_call_rooms", set()):
            try:
                await self.channel_layer.group_discard(group_name, self.channel_name)
            except Exception:
                pass
        self.group_call_rooms = set()

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

        # Group call channel subscription (client subscribes to group_call_{call_id})
        if msg_type == "join_group_call":
            call_id = data.get("call_id")
            if call_id is not None:
                try:
                    call_id = int(call_id)
                    group_name = f"group_call_{call_id}"
                    await self.channel_layer.group_add(group_name, self.channel_name)
                    self.group_call_rooms.add(group_name)
                except (TypeError, ValueError):
                    pass
            return
        if msg_type == "leave_group_call":
            call_id = data.get("call_id")
            if call_id is not None:
                try:
                    call_id = int(call_id)
                    group_name = f"group_call_{call_id}"
                    await self.channel_layer.group_discard(group_name, self.channel_name)
                    self.group_call_rooms.discard(group_name)
                except (TypeError, ValueError):
                    pass
            return

        target = data.get("target")

        # Validate: only process known message types
        if msg_type not in KNOWN_MESSAGE_TYPES:
            return
        # Validate: target must be non-empty string
        if not target or not isinstance(target, str) or not target.strip():
            return
        target = target.strip()

        # Ensure authenticated user in scope
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            return
        # Prevent sending to self (invalid signaling)
        if target == user.username:
            return

        try:
            if msg_type == "webrtc_offer":
                await self.channel_layer.group_send(
                    f"call_{target}",
                    {
                        "type": "webrtc_signal",
                        "payload": data,
                        "from_user": user.username,
                    },
                )
            elif msg_type == "webrtc_answer":
                await self.channel_layer.group_send(
                    f"call_{target}",
                    {
                        "type": "webrtc_signal",
                        "payload": data,
                        "from_user": user.username,
                    },
                )
            elif msg_type == "ice_candidate":
                await self.channel_layer.group_send(
                    f"call_{target}",
                    {
                        "type": "webrtc_signal",
                        "payload": data,
                        "from_user": user.username,
                    },
                )
            elif msg_type == "end_call":
                logger.info(
                    "Call end signaled: %s ended call, notifying %s",
                    user.username, target,
                )
                await self.channel_layer.group_send(
                    f"call_{target}",
                    {
                        "type": "call_ended",
                        "payload": data,
                        "from_user": user.username,
                    },
                )
        except Exception:
            # Avoid crashing on channel layer errors (e.g. invalid target group)
            pass

    async def incoming_call(self, event):
        """Pushed when someone initiates a call to this user."""
        try:
            payload = event.get("payload", {})
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    async def webrtc_signal(self, event):
        """Forward WebRTC offer/answer/ICE to the other peer."""
        try:
            payload = dict(event.get("payload", {}))
            payload["from_user"] = event.get("from_user")
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    async def call_ended(self, event):
        """Notify that the other peer ended the call."""
        try:
            from_user = event.get("from_user", "?")
            recv_user = self.scope.get("user")
            recv_name = recv_user.username if recv_user else "?"
            logger.info(
                "Call ended notification: %s notified that %s ended the call",
                recv_name, from_user,
            )
            payload = dict(event.get("payload", {}))
            payload["type"] = "call_ended"
            payload["from_user"] = from_user
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    async def call_accepted(self, event):
        """Notify sender that receiver accepted the call."""
        try:
            payload = event.get("payload", {})
            logger.info("Call accepted: forwarding to sender")
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    async def call_declined(self, event):
        """Notify sender that receiver declined the call."""
        try:
            payload = event.get("payload", {})
            logger.info("Call declined: forwarding to sender")
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    # ---------- Group call events (sent to call_{username} or group_call_{call_id}) ----------
    async def incoming_group_call(self, event):
        """Pushed to invitees when creator starts a group call."""
        try:
            payload = event.get("payload", {})
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    async def participant_joined(self, event):
        """Broadcast to group_call_{call_id}: a participant joined."""
        try:
            payload = event.get("payload", {})
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    async def participant_left(self, event):
        """Broadcast to group_call_{call_id}: a participant left."""
        try:
            payload = event.get("payload", {})
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass

    async def group_call_ended(self, event):
        """Broadcast to group_call_{call_id}: the group call has ended."""
        try:
            payload = event.get("payload", {})
            await self.send(text_data=json.dumps(payload))
        except Exception:
            pass
