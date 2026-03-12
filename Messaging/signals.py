"""
Messaging signals: WebSocket notifications for group/private messages.

These signals must remain synchronous; Django does not await async receivers.
We keep WebSocket notifications resilient even if notification_type rows are missing
or channel layer fails, so realtime messaging keeps working.
"""
import logging
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str

from .models import GroupChats, GroupMessages, GroupMembers, IndividualMessages
from notifications.models import Notification, notification_type
from Calling.models import Call

# Store previous Call status for post_save (detect transition to MISSED)
_call_previous_status = {}

logger = logging.getLogger(__name__)


# -------- Group message: notify all members except sender --------
def _create_notification_for_groupmessage_sync(sender, instance: GroupMessages, created, **kwargs):
    if not created:
        return
    group_obj = instance.group
    sender_name = _get_users_Name_sync(instance.sender)
    members = GroupMembers.objects.filter(groupchat=group_obj).exclude(participant=instance.sender)
    try:
        nt = notification_type.objects.get(type_name="Group_message")
    except notification_type.DoesNotExist:
        nt = None
        logger.warning("notification_type 'Group_message' not found; sending WebSocket only.")
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Group message: channel_layer is None, skipping WebSocket notifications.")
        return
    for m in members:
        try:
            if nt:
                notification_obj = Notification.objects.create(
                    from_user=instance.sender,
                    receipient=m.participant,
                    message=instance.content,
                    type_of_notification=nt,
                )
                extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
            else:
                extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
            async_to_sync(channel_layer.group_send)(
                f"user_{m.participant.username}",
                {
                    "type": "send_notification",
                    "category": "Group_message",
                    "title": f"Received a Group message from {group_obj.group_name}",
                    "from": sender_name,
                    "message": instance.content,
                    "extra": {"time": extra_time, "group_id": group_obj.group_id},
                },
            )
        except Exception as e:
            logger.warning("Group message WebSocket notification failed for %s: %s", m.participant.username, e)


@receiver(post_save, sender=GroupMessages)
def create_notification_for_groupmessage(sender, instance: GroupMessages, created, **kwargs):
    """Receiver: new GroupMessages → notify other group members (DB + WebSocket)."""
    _create_notification_for_groupmessage_sync(sender, instance, created, **kwargs)


# -------- Private/DM message: notify the other participant --------
def _create_notification_for_chatmessage_sync(sender, instance: IndividualMessages, created, **kwargs):
    if not created:
        return
    other = instance.chat.get_other_participant(user=instance.sender)
    sender_name = _get_users_Name_sync(instance.sender)
    try:
        nt = notification_type.objects.get(type_name="private_message")
    except notification_type.DoesNotExist:
        nt = None
        logger.warning("notification_type 'private_message' not found; sending WebSocket only.")
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Private message: channel_layer is None, skipping WebSocket notification.")
        return
    try:
        if nt:
            notification_obj = Notification.objects.create(
                from_user=instance.sender,
                receipient=other,
                message=instance.content,
                type_of_notification=nt,
            )
            extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
        else:
            extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
        async_to_sync(channel_layer.group_send)(
            f"user_{other.username}",
            {
                "type": "send_notification",
                "category": "Private_message",
                "title": "You received a Private message",
                "from": sender_name,
                "message": instance.content,
                "extra": {"time": extra_time, "chat_id": instance.chat.chat_id},
            },
        )
    except Exception as e:
        logger.warning("Private message WebSocket notification failed for %s: %s", other.username, e)


@receiver(post_save, sender=IndividualMessages)
def create_notification_for_chatmessage(sender, instance: IndividualMessages, created, **kwargs):
    """Receiver: new IndividualMessages → notify the other chat participant (DB + WebSocket)."""
    _create_notification_for_chatmessage_sync(sender, instance, created, **kwargs)


# -------- Added to group: notify the added user (not the creator) --------
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
        nt = None
        logger.warning("notification_type 'Group_Created' not found; sending WebSocket only.")
    msg = f"You were added to a group '{group.group_name}'"
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Added-to-group: channel_layer is None, skipping WebSocket notification.")
        return
    try:
        if nt:
            notification_obj = Notification.objects.create(
                from_user=creator,
                receipient=added_user,
                message=msg,
                type_of_notification=nt,
            )
            extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
        else:
            extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
        async_to_sync(channel_layer.group_send)(
            f"user_{added_user.username}",
            {
                "type": "send_notification",
                "title": "Added to a New Group",
                "message": msg,
                "category": "Group_Created",
                "extra": {"time": extra_time, "group_id": group.group_id},
            },
        )
    except Exception as e:
        logger.warning("Added-to-group WebSocket notification failed for %s: %s", added_user.username, e)


@receiver(post_save, sender=GroupMembers)
def notify_added_to_group(sender, created, instance: GroupMembers, **kwargs):
    """Receiver: new GroupMembers → notify the added user (DB + WebSocket)."""
    _notify_added_to_group_sync(sender, created, instance, **kwargs)


# -------- Removed from group: notify the removed user --------
def _notify_removed_from_group_sync(sender, instance: GroupMembers, **kwargs):
    """Notify the user when they are removed from a group. Uses groupchat_id/participant_id from deleted instance."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        group = GroupChats.objects.get(pk=instance.groupchat_id)
    except GroupChats.DoesNotExist:
        return
    try:
        removed_user = User.objects.get(username=instance.participant_id)
    except User.DoesNotExist:
        return
    # from_user = group admin (who can remove members)
    from_user = group.created_by
    if from_user == removed_user:
        return
    try:
        nt = notification_type.objects.get(type_name="User_Removed_From_Group")
    except notification_type.DoesNotExist:
        nt = None
        logger.warning("notification_type 'User_Removed_From_Group' not found; sending WebSocket only.")
    msg = f"You have been removed from the group '{group.group_name}'."
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Removed-from-group: channel_layer is None, skipping WebSocket notification.")
        return
    remover_name = _get_users_Name_sync(from_user)
    try:
        if nt:
            notification_obj = Notification.objects.create(
                from_user=from_user,
                receipient=removed_user,
                message=msg,
                type_of_notification=nt,
            )
            extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
        else:
            extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
        async_to_sync(channel_layer.group_send)(
            f"user_{removed_user.username}",
            {
                "type": "send_notification",
                "title": "Removed from the group",
                "message": msg,
                "category": "User_Removed_From_Group",
                "from": remover_name,
                "extra": {
                    "time": extra_time,
                    "group_id": group.group_id,
                },
            },
        )
    except Exception as e:
        logger.warning("Removed-from-group WebSocket notification failed for %s: %s", removed_user.username, e)


@receiver(post_delete, sender=GroupMembers)
def notify_removed_from_group(sender, instance: GroupMembers, **kwargs):
    """Receiver: GroupMembers delete → notify the removed user (DB + WebSocket)."""
    _notify_removed_from_group_sync(sender, instance, **kwargs)


# -------- Group deleted: notify all members before group is removed --------
def _notify_group_deleted_sync(sender, instance: GroupChats, **kwargs):
    """Notify all group members when the group is deleted. Runs in pre_delete so members still exist."""
    members = GroupMembers.objects.filter(groupchat=instance).select_related("participant")
    try:
        nt = notification_type.objects.get(type_name="Group_Deleted")
    except notification_type.DoesNotExist:
        nt = None
        logger.warning("notification_type 'Group_Deleted' not found; sending WebSocket only.")
    from_user = instance.created_by
    group_name = instance.group_name or f"Group ({instance.group_id})"
    msg = f"The group '{group_name}' has been deleted."
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Group-deleted: channel_layer is None, skipping WebSocket notifications.")
        return
    deleter_name = _get_users_Name_sync(from_user)
    for gm in members:
        try:
            if nt:
                notification_obj = Notification.objects.create(
                    from_user=from_user,
                    receipient=gm.participant,
                    message=msg,
                    type_of_notification=nt,
                )
                extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
            else:
                extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
            async_to_sync(channel_layer.group_send)(
                f"user_{gm.participant.username}",
                {
                    "type": "send_notification",
                    "title": "Group deleted",
                    "message": msg,
                    "category": "Group_Deleted",
                    "from": deleter_name,
                    "extra": {
                        "time": extra_time,
                        "group_id": instance.group_id,
                    },
                },
            )
        except Exception as e:
            logger.warning("Group-deleted WebSocket notification failed for %s: %s", gm.participant.username, e)


@receiver(pre_delete, sender=GroupChats)
def notify_group_deleted(sender, instance: GroupChats, **kwargs):
    """Receiver: GroupChats pre_delete → notify all members that the group was deleted (DB + WebSocket)."""
    _notify_group_deleted_sync(sender, instance, **kwargs)


# -------- Call status MISSED: increment receiver's MissedCallCount (table in Calling app) --------
def _increment_missed_call_count_for_receiver_sync(receiver_user):
    """Get or create MissedCallCount for receiver_user and increment by 1."""
    from Calling.models import MissedCallCount
    obj, _ = MissedCallCount.objects.get_or_create(
        user=receiver_user,
        defaults={"missed_call_count": 0},
    )
    obj.missed_call_count += 1
    obj.save(update_fields=["missed_call_count"])


def _store_call_status_before_save(sender, instance, **kwargs):
    """Store previous Call status so we only increment MissedCallCount when status becomes MISSED."""
    if not instance.pk:
        return
    try:
        old = Call.objects.get(pk=instance.pk)
        _call_previous_status[instance.pk] = old.status
    except Call.DoesNotExist:
        pass


def _increment_missed_call_count_on_missed(sender, instance, created, **kwargs):
    """When a Call is saved with status=MISSED, increment the receiver's missed_call_count (create record if needed)."""
    if instance.status != Call.MISSED or not instance.receiver_id:
        _call_previous_status.pop(instance.pk, None)
        return
    prev = _call_previous_status.pop(instance.pk, None)
    # Increment only when status became MISSED (new call with MISSED, or update from non-MISSED to MISSED)
    if created or prev != Call.MISSED:
        try:
            _increment_missed_call_count_for_receiver_sync(instance.receiver)
        except Exception as e:
            logger.warning("MissedCallCount increment failed for receiver %s: %s", instance.receiver_id, e)


pre_save.connect(_store_call_status_before_save, sender=Call)
post_save.connect(_increment_missed_call_count_on_missed, sender=Call)
