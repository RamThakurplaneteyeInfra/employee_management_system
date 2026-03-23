"""
WebSocket consumer: NotificationConsumer only.
Handles real-time notifications per user via channel_layer.group_send("user_<username>", ...).
Also joins product-based groups (names from project.Product) so group_send by product reaches subscribers.
"""
import json
import logging
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from ems.channel_groups import product_group_name, user_group_name

logger = logging.getLogger(__name__)


def _product_group_name(product_label: str) -> str:
    """Build a safe channel group name from a Product.name (spaces → underscores)."""
    # Backwards-compatible wrapper used by other modules.
    return product_group_name(product_label)


def _fetch_product_names_sync():
    """Sync ORM: list all Product.name values from the database."""
    from project.models import Product

    return list(Product.objects.order_by("name").values_list("name", flat=True))


# Async wrapper for use in connect() — must not block the event loop
_fetch_product_names = sync_to_async(_fetch_product_names_sync, thread_sensitive=True)


# =============================================================================
# NotificationConsumer – User-specific notification stream
# Connect: ws://host/ws/notifications/
# Receives: send_notification from group_send("user_<username>", ...)
#          and from notifications_product_<ProductName> where ProductName matches project.Product.name
# =============================================================================
class NotificationConsumer(AsyncWebsocketConsumer):
    """Handles real-time notifications per user. Joins user_<username> and all product groups."""

    async def connect(self):
        # Same auth rules as Calling.consumer.CallConsumer so both /ws/notifications/
        # and /ws/calls/ accept only when session user is authenticated.
        user = self.scope.get("user")
        if user is None or getattr(user, "is_anonymous", True):
            logger.warning(
                "NotificationConsumer connect rejected: anonymous or missing user (path=%s)",
                self.scope.get("path"),
            )
            await self.close(code=4001)
            return

        self.room_name = user_group_name(user.username)
        await self.channel_layer.group_add(self.room_name, self.channel_name)

        # Subscribe to every product group derived from project.Product (DB)
        try:
            product_names = await _fetch_product_names()
        except Exception:
            product_names = []
        self._product_groups_joined = [_product_group_name(n) for n in product_names if n]
        for group_name in self._product_groups_joined:
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        for group_name in getattr(self, "_product_groups_joined", ()):
            await self.channel_layer.group_discard(group_name, self.channel_name)

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
