"""
Messaging signals: WebSocket notifications for group/private messages.

These signals must remain synchronous; Django does not await async receivers.
We keep WebSocket notifications resilient even if notification_type rows are missing
or channel layer fails, so realtime messaging keeps working.
"""
import logging
from asgiref.sync import async_to_sync
from django.db.models import F
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str

from .models import GroupChats, GroupMessages, GroupMembers, IndividualMessages
from .chat_ws_utils import build_message_payload_for_ws, chat_id_from_message
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
    group_name=group_obj.group_name
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
                    "title": f"Received a Group message in {group_name}",
                    "from": sender_name,
                    "message": instance.content,
                    "extra": {"time": extra_time, "group_name": group_name},
                },
            )
        except Exception as e:
            logger.warning("Group message WebSocket notification failed for %s: %s", m.participant.username, e)


def _broadcast_new_chat_message_sync(instance, is_group):
    """Broadcast new_message and chat_updated to chat_<chat_id> for Real-Time Chat WebSocket."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    chat_id = chat_id_from_message(instance)
    if not chat_id:
        return
    try:
        payload = build_message_payload_for_ws(instance, is_group)
    except Exception as e:
        logger.warning("Chat WS build_message_payload_for_ws failed: %s", e)
        return
    group_name = f"chat_{chat_id}"
    created_at = instance.created_at
    if created_at and timezone.is_naive(created_at):
        created_at = timezone.make_aware(created_at, timezone.utc)
    last_at_str = created_at.isoformat().replace("+00:00", "Z") if created_at else None
    preview = (instance.content or "")[:100].replace("\n", " ")
    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "chat.new_message", "chat_id": chat_id, "payload": payload},
        )
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "chat.chat_updated",
                "chat_id": chat_id,
                "last_message_at": last_at_str,
                "last_message_preview": preview,
                "unseen_count": 0,
            },
        )
    except Exception as e:
        logger.warning("Chat WS group_send failed for %s: %s", group_name, e)


def _broadcast_unseen_count_for_new_group_message(instance: GroupMessages):
    """Increment GroupMembers.unseenmessages for all except sender; push unseen_count_updated per member."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    chat_id = instance.group.group_id
    group_name = f"chat_{chat_id}"
    sender = instance.sender
    members = GroupMembers.objects.filter(groupchat=instance.group).exclude(participant=sender)
    if not members.exists():
        return
    GroupMembers.objects.filter(groupchat=instance.group).exclude(participant=sender).update(
        unseenmessages=F("unseenmessages") + 1,
        seen=False,
    )
    try:
        for gm in GroupMembers.objects.filter(groupchat=instance.group).exclude(participant=sender):
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "chat.unseen_count_updated",
                    "chat_id": chat_id,
                    "unseen_count": gm.unseenmessages,
                    "for_user": gm.participant_id,
                },
            )
    except Exception as e:
        logger.warning("Unseen count broadcast failed for group %s: %s", chat_id, e)


def _broadcast_unseen_count_for_new_dm_message(instance: IndividualMessages):
    """Notify the other participant of their unseen count (message-wise in IndividualMessages)."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    chat_id = instance.chat_id
    group_name = f"chat_{chat_id}"
    other = instance.chat.get_other_participant(user=instance.sender)
    if not other:
        return
    count = IndividualMessages.objects.filter(chat=instance.chat, sender=instance.sender, seen=False).count()
    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "chat.unseen_count_updated",
                "chat_id": chat_id,
                "unseen_count": count,
                "for_user": other.username,
            },
        )
    except Exception as e:
        logger.warning("Unseen count broadcast failed for DM %s: %s", chat_id, e)


@receiver(post_save, sender=GroupMessages)
def create_notification_for_groupmessage(sender, instance: GroupMessages, created, **kwargs):
    """Receiver: new GroupMessages → notify other group members (DB + WebSocket)."""
    _create_notification_for_groupmessage_sync(sender, instance, created, **kwargs)
    if created:
        _broadcast_new_chat_message_sync(instance, is_group=True)
        _broadcast_unseen_count_for_new_group_message(instance)


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
    if created:
        _broadcast_new_chat_message_sync(instance, is_group=False)
        _broadcast_unseen_count_for_new_dm_message(instance)


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


# -------- Meeting (events.Meeting): broadcast on product channel (create/update/delete) --------
# Skip broadcast when only is_active is toggled. Labels: Created | reschedule | updated | abandoned.
_meeting_previous_state = {}


def _meeting_pre_save_store(sender, instance, **kwargs):
    """Store field snapshot before save so post_save can detect what changed."""
    from events.models import Meeting

    if not isinstance(instance, Meeting) or not instance.pk:
        return
    try:
        old = Meeting.objects.get(pk=instance.pk)
    except Meeting.DoesNotExist:
        return
    _meeting_previous_state[instance.pk] = {
        "product_id": old.product_id,
        "meeting_room_id": old.meeting_room_id,
        "meeting_type": old.meeting_type,
        "time": old.time,
        "is_active": old.is_active,
    }


def _meeting_send_product_channel(instance, action_label, message_text):
    """
    Send WebSocket notification to product group. action_label is one of:
    Created | reschedule | updated | abandoned
    """
    if instance.product_id is None:
        return
    try:
        product = instance.product
        product_name = (getattr(product, "name", None) or "").strip()
    except Exception:
        return
    if not product_name:
        return

    from notifications.consumer import _product_group_name

    group_name = _product_group_name(product_name)
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Meeting notification: channel_layer is None, skipping WebSocket broadcast.")
        return

    room_name = None
    if instance.meeting_room_id:
        try:
            room_name = getattr(instance.meeting_room, "name", None)
        except Exception:
            room_name = None

    extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "category": "Meeting_push",
                "title": action_label,
                "message": message_text,
                "from": None,
                "extra": {
                    "time": extra_time,
                    "action": action_label,
                    "product_name": product_name,
                    "room_name": room_name,
                    "meeting_type": getattr(instance, "meeting_type", None),
                    "time_minutes": getattr(instance, "time", None),
                    "is_active": getattr(instance, "is_active", None),
                },
            },
        )
    except Exception as e:
        logger.warning(
            "Meeting product-channel WebSocket notification failed (group=%s): %s",
            group_name,
            e,
        )


def _notify_meeting_post_save(sender, instance, created, **kwargs):
    """
    Created → 'Created'. Updated: if only is_active changed, skip.
    If time changed → 'reschedule'. Any other attribute change → 'updated'.
    """
    from events.models import Meeting

    if not created:
        prev = _meeting_previous_state.pop(instance.pk, None)
        if prev is None:
            return
        # No broadcast when only is_active is flipped
        only_active_changed = (
            prev["product_id"] == instance.product_id
            and prev["meeting_room_id"] == instance.meeting_room_id
            and prev["meeting_type"] == instance.meeting_type
            and prev["time"] == instance.time
            and prev["is_active"] != instance.is_active
        )
        if only_active_changed:
            return
        time_changed = prev["time"] != instance.time
        if time_changed:
            action_label = "reschedule"
            msg = (
                f"Meeting rescheduled: duration {instance.time} min, "
                f"room={getattr(instance.meeting_room, 'name', None) or 'N/A'}, "
                f"type={instance.meeting_type}."
            )
        else:
            action_label = "updated"
            msg = (
                f"Meeting updated: room={getattr(instance.meeting_room, 'name', None) or 'N/A'}, "
                f"type={instance.meeting_type}, duration={instance.time} min."
            )
        _meeting_send_product_channel(instance, action_label, msg)
        return

    # Created
    room_name = None
    if instance.meeting_room_id:
        try:
            room_name = getattr(instance.meeting_room, "name", None)
        except Exception:
            pass
    msg = (
        f"Meeting created: type={instance.meeting_type}, "
        f"room={room_name or 'N/A'}, duration={instance.time} min."
    )
    _meeting_send_product_channel(instance, "Created", msg)


def _notify_meeting_pre_delete(sender, instance, **kwargs):
    """Deleted meeting → label 'abandoned' on product channel."""
    from events.models import Meeting

    room_name = None
    if instance.meeting_room_id:
        try:
            room_name = getattr(instance.meeting_room, "name", None)
        except Exception:
            pass
    msg = (
        f"Meeting abandoned: type={getattr(instance, 'meeting_type', None)}, "
        f"room={room_name or 'N/A'}."
    )
    _meeting_send_product_channel(instance, "abandoned", msg)
    _meeting_previous_state.pop(instance.pk, None)


def _register_meeting_signals():
    """Register Meeting pre_save, post_save, pre_delete; deferred to avoid circular imports."""
    from events.models import Meeting

    pre_save.connect(_meeting_pre_save_store, sender=Meeting)
    post_save.connect(_notify_meeting_post_save, sender=Meeting)
    pre_delete.connect(_notify_meeting_pre_delete, sender=Meeting)


_register_meeting_signals()


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
