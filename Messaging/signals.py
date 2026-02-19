"""
Messaging signals: WebSocket notifications for group/private messages.
"""
from asgiref.sync import sync_to_async, async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer

from .models import GroupChats, GroupMessages, GroupMembers, IndividualMessages
from notifications.models import Notification, notification_type


def _create_notification_for_groupmessage_sync(sender, instance: GroupMessages, created, **kwargs):
    if not created:
        return
    group_obj = instance.group
    members = GroupMembers.objects.filter(groupchat=group_obj).exclude(participant=instance.sender)
    try:
        nt = notification_type.objects.get(type_name="Group_message")
    except notification_type.DoesNotExist:
        return
    channel_layer = get_channel_layer()
    for m in members:
        Notification.objects.create(
            from_user=instance.sender,
            receipient=m.participant,
            message=instance.content,
            type_of_notification=nt,
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{m.participant.username}",
            {
                "type": "send_notification",
                "title": f"Group message from {group_obj.group_name}",
                "message": instance.content,
            },
        )


@receiver(post_save, sender=GroupMessages)
async def create_notification_for_groupmessage(sender, instance: GroupMessages, created, **kwargs):
    await sync_to_async(_create_notification_for_groupmessage_sync)(sender, instance, created, **kwargs)


def _create_notification_for_chatmessage_sync(sender, instance: IndividualMessages, created, **kwargs):
    if not created:
        return
    other = instance.chat.get_other_participant(user=instance.sender)
    try:
        nt = notification_type.objects.get(type_name="private_message")
    except notification_type.DoesNotExist:
        return
    Notification.objects.create(
        from_user=instance.sender,
        receipient=other,
        message=instance.content,
        type_of_notification=nt,
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{other.username}",
        {
            "type": "send_notification",
            "title": f"Message from {instance.sender.username}",
            "message": instance.content,
        },
    )


@receiver(post_save, sender=IndividualMessages)
async def create_notification_for_chatmessage(sender, instance: IndividualMessages, created, **kwargs):
    await sync_to_async(_create_notification_for_chatmessage_sync)(sender, instance, created, **kwargs)


def _notify_added_to_group_sync(sender, created, instance: GroupMembers, **kwargs):
    """Notify user when added to a group."""
    if not created:
        return
    group = instance.groupchat
    added_user = instance.participant
    creator = group.created_by
    if added_user == creator:
        return
    try:
        nt = notification_type.objects.get(type_name="Group_Created")
    except notification_type.DoesNotExist:
        return
    msg = f"You were added to group '{group.group_name}' by {creator.username}"
    Notification.objects.create(
        from_user=creator,
        receipient=added_user,
        message=msg,
        type_of_notification=nt,
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{added_user.username}",
        {"type": "send_notification", "title": "Added to Group", "message": msg, "extra": {"group_id": group.group_id}},
    )


@receiver(post_save, sender=GroupMembers)
async def notify_added_to_group(sender, created, instance: GroupMembers, **kwargs):
    await sync_to_async(_notify_added_to_group_sync)(sender, created, instance, **kwargs)
