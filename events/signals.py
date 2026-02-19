from asgiref.sync import async_to_sync
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from datetime import date

from .models import Meeting, BookSlot, SlotMembers
from notifications.models import Notification, notification_type


def _cleanup_old_meetings_sync(sender, instance: Meeting, **kwargs):
    to_delete = Meeting.objects.all().exclude(created_at__date=date.today())
    if to_delete.exists():
        to_delete.delete()


@receiver(pre_save, sender=Meeting)
def cleanup_old_meetings(sender, instance: Meeting, **kwargs):
    _cleanup_old_meetings_sync(sender, instance, **kwargs)


def _notify_slot_booked_sync(sender, created, instance: SlotMembers, **kwargs):
    """Notify member when added to a booked slot."""
    if not created:
        return
    slot = instance.slot
    member = instance.member
    creator = slot.created_by
    if member == creator:
        return
    try:
        nt = notification_type.objects.get(type_name="Slot_booked")
    except notification_type.DoesNotExist:
        return
    msg = f"Slot '{slot.meeting_title}' on {slot.date} has been scheduled. You are invited."
    notification_obj=Notification.objects.create(
        from_user=creator,
        receipient=member,
        message=msg,
        type_of_notification=nt,
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{member.username}",
        {"type": "send_notification", "title": "Slot Booked", "message": msg, "extra": {"time": notification_obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")}},
    )


@receiver(post_save, sender=SlotMembers)
def notify_slot_booked(sender, created, instance: SlotMembers, **kwargs):
    _notify_slot_booked_sync(sender, created, instance, **kwargs)


def _notify_meeting_scheduled_sync(sender, instance: Meeting, created, **kwargs):
    """Notify users when MD schedules a meeting."""
    if not created:
        return
    users = list(instance.users.all())
    if not users:
        return
    try:
        nt = notification_type.objects.get(type_name="Meeting_scheduled")
    except notification_type.DoesNotExist:
        return
    room = instance.meeting_room
    room_name = room.name if room else "TBD"
    msg = f"Meeting scheduled for {instance.time} min in {room_name}"
    from_user = users[0]
    channel_layer = get_channel_layer()
    for u in users:
        notification_obj=Notification.objects.create(from_user=from_user, receipient=u, message=msg, type_of_notification=nt)
        async_to_sync(channel_layer.group_send)(
            f"user_{u.username}",
            {"type": "send_notification", "title": "Meeting Scheduled", "message": msg, "extra": {"time":notification_obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")}},
        )


@receiver(post_save, sender=Meeting)
def notify_meeting_scheduled(sender, created, instance: Meeting, **kwargs):
    _notify_meeting_scheduled_sync(sender, instance, created, **kwargs)