"""
Messaging signals: WebSocket notifications for group/private messages.
"""
from asgiref.sync import sync_to_async, async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from accounts.filters import _get_users_Name_sync

from .models import GroupChats, GroupMessages, GroupMembers, IndividualMessages
from notifications.models import Notification, notification_type


def _create_notification_for_groupmessage_sync(sender, instance: GroupMessages, created, **kwargs):
    if not created:
        return
    group_obj = instance.group
    sender_name=_get_users_Name_sync(instance.sender)
    members = GroupMembers.objects.filter(groupchat=group_obj).exclude(participant=instance.sender)
    try:
        nt = notification_type.objects.get(type_name="Group_message")
    except notification_type.DoesNotExist:
        return
    channel_layer = get_channel_layer()
    for m in members:
        notification_obj=Notification.objects.create(
            from_user=instance.sender,
            receipient=m.participant,
            message=instance.content,
            type_of_notification=nt,
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{m.participant.username}",
            {
                "type": "send_notification",
                "category":"Group_message",
                "title": f"Received a Group message from {group_obj.group_name}",
                "from":sender_name,
                "message": instance.content,
                "extra":{"time": notification_obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")}
            }
        )


@receiver(post_save, sender=GroupMessages)
def create_notification_for_groupmessage(sender, instance: GroupMessages, created, **kwargs):
    _create_notification_for_groupmessage_sync(sender, instance, created, **kwargs)


def _create_notification_for_chatmessage_sync(sender, instance: IndividualMessages, created, **kwargs):
    if not created:
        return
    other = instance.chat.get_other_participant(user=instance.sender)
    sender_name=_get_users_Name_sync(instance.sender)
    try:
        nt = notification_type.objects.get(type_name="private_message")
    except notification_type.DoesNotExist:
        return
    notification_obj=Notification.objects.create(
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
                "category":"Private_message",
                "title": f"You received a Private message",
                "from": sender_name,
                "message": instance.content,
                "extra":{"time": notification_obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")}
            }
        )


@receiver(post_save, sender=IndividualMessages)
def create_notification_for_chatmessage(sender, instance: IndividualMessages, created, **kwargs):
    _create_notification_for_chatmessage_sync(sender, instance, created, **kwargs)


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
    msg = f"You were added to group '{group.group_name}'"
    notification_obj=Notification.objects.create(
        from_user=creator,
        receipient=added_user,
        message=msg,
        type_of_notification=nt,
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{added_user.username}",
        {"type": "send_notification", "title": "Added to a New Group","message":msg,"category":"Group_Created","extra": {"time": notification_obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")}},
    )

@receiver(post_save, sender=GroupMembers)
def notify_added_to_group(sender, created, instance: GroupMembers, **kwargs):
    _notify_added_to_group_sync(sender, created, instance, **kwargs)
