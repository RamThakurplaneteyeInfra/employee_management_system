import logging
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from datetime import date

from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str

from .models import BookSlot, SlotMembers
from notifications.models import Notification, notification_type

logger = logging.getLogger(__name__)


# def _cleanup_old_meetings_sync(sender, instance: Meeting, **kwargs):
#     to_delete = Meeting.objects.all().exclude(created_at__date=date.today())
#     if to_delete.exists():
#         to_delete.delete()


# @receiver(pre_save, sender=Meeting)
# def cleanup_old_meetings(sender, instance: Meeting, **kwargs):
#     _cleanup_old_meetings_sync(sender, instance, **kwargs)


def _notify_slot_booked_sync(sender, created, instance: SlotMembers, **kwargs):
    """Notify member when added to a booked slot."""
    if not created:
        return
    slot = instance.slot
    member = instance.member
    creator = slot.created_by
    if not creator or member == creator:
        return
    creator_name = _get_users_Name_sync(creator)
    msg = f"Slot for '{slot.meeting_title}' on {slot.date} has been scheduled. You are invited."
    try:
        nt = notification_type.objects.get(type_name="Slot_booked")
        notification_obj = Notification.objects.create(
            from_user=creator,
            receipient=member,
            message=msg,
            type_of_notification=nt,
        )
        extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
    except notification_type.DoesNotExist:
        extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f"user_{member.username}",
            {
                "type": "send_notification",
                "title": "Meeting booked",
                "category": "Meeting_Slot",
                "from": creator_name,
                "message": msg,
                "extra": {"time": extra_time},
            },
        )
    except Exception as e:
        logger.warning("Slot booked WebSocket notification failed for %s: %s", member.username, e)


@receiver(post_save, sender=SlotMembers)
def notify_slot_booked(sender, created, instance: SlotMembers, **kwargs):
    _notify_slot_booked_sync(sender, created, instance, **kwargs)


# Meeting model no longer has users M2M; notifications per meeting can be sent via
# product-based WebSocket groups (notifications_product_<ProductName>) if needed.