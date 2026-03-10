import logging
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from datetime import date

from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str

from .models import Meeting, BookSlot, SlotMembers
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


def _notify_meeting_scheduled_for_users_sync(instance: Meeting, user_pks):
    """Notify users (by pk set) that a meeting was scheduled. Called from m2m_changed so users are already set."""
    if not user_pks:
        return
    from accounts.models import User
    users = list(User.objects.filter(pk__in=user_pks))
    if not users:
        return
    try:
        nt = notification_type.objects.get(type_name="Meeting_scheduled")
    except notification_type.DoesNotExist:
        nt = None
    room = instance.meeting_room
    room_name = room.name if room else "TBD"
    msg = f"A short Meeting scheduled for {instance.time} min in {room_name}"
    from_user = users[0]
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    for u in users:
        try:
            if nt:
                notification_obj = Notification.objects.create(
                    from_user=from_user,
                    receipient=u,
                    message=msg,
                    type_of_notification=nt,
                )
                extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
            else:
                extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
            async_to_sync(channel_layer.group_send)(
                f"user_{u.username}",
                {
                    "type": "send_notification",
                    "title": "Meeting Scheduled",
                    "category": "Meeting_Pushed",
                    "message": msg,
                    "extra": {"time": extra_time},
                },
            )
        except Exception as e:
            logger.warning("Meeting scheduled WebSocket notification failed for %s: %s", u.username, e)


@receiver(m2m_changed, sender=Meeting.users.through)
def notify_meeting_scheduled_m2m(sender, instance, action, pk_set, **kwargs):
    """When users are added to a meeting (create or update), notify those users. post_save runs before M2M is set."""
    if action != "post_add" or not pk_set:
        return
    _notify_meeting_scheduled_for_users_sync(instance, pk_set)


# Keep post_save for backwards compatibility; M2M is empty at create time so this no-op is harmless.
@receiver(post_save, sender=Meeting)
def notify_meeting_scheduled(sender, created, instance: Meeting, **kwargs):
    pass