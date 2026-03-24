"""
Helpers for Real-Time Chat WebSocket: message payload, chat access, mark_seen.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.filters import _get_users_Name_sync
from .models import GroupChats, GroupMembers, IndividualChats, IndividualMessages, GroupMessages
from .filters import _get_group_object_sync, _get_individual_chat_object_sync, check_group_or_chat
from .filters import _attachment_payload, _message_content_for_response
from .utils import gmt_to_ist_date_str, gmt_to_ist_time_str


def _sender_name(sender):
    if sender is None:
        return None
    profile = getattr(sender, "accounts_profile", None)
    return getattr(profile, "Name", None) if profile else _get_users_Name_sync(sender)


def build_message_payload_for_ws(message, is_group):
    """
    Build new_message payload for one message (GroupMessages or IndividualMessages).
    Matches GET /messaging/getMessages/ shape: id, sender (username), sender_name, message, date, time, attachments, created_at.
    """
    if is_group:
        sender = message.sender
        attachments = [_attachment_payload(a) for a in message.attachments.all()]
    else:
        sender = message.sender
        attachments = [_attachment_payload(a) for a in message.attachments.all()]

    created_at = message.created_at
    if created_at and timezone.is_naive(created_at):
        created_at = timezone.make_aware(created_at, timezone.utc)
    created_at_str = created_at.isoformat().replace("+00:00", "Z") if created_at else None

    reply_to_id = getattr(message, "reply_to_id", None)
    replied_message = None
    if reply_to_id:
        r = getattr(message, "reply_to", None)
        if r is not None:
            replied_message = {
                "id": r.id,
                "message": _message_content_for_response(r.content),
                "sender": _sender_name(r.sender),
            }

    updated_at = getattr(message, "updated_at", None)
    if updated_at and timezone.is_naive(updated_at):
        updated_at = timezone.make_aware(updated_at, timezone.utc)

    payload = {
        "id": message.id,
        "sender": sender.username if sender else None,
        "sender_name": _sender_name(sender),
        "message": _message_content_for_response(message.content),
        "date": gmt_to_ist_date_str(created_at),
        "time": gmt_to_ist_time_str(message.created_at),
        "attachment_id": message.attachments.first().id if message.attachments.exists() else None,
        "attachment": attachments[0] if attachments else None,
        "attachments": attachments,
        "created_at": created_at_str,
        "replyTo": reply_to_id,
        "repliedMessage": replied_message,
        "edited": bool(getattr(message, "edited", False)),
        "editedAtDate": gmt_to_ist_date_str(updated_at) if getattr(message, "edited", False) and updated_at else None,
        "editedAtTime": gmt_to_ist_time_str(updated_at) if getattr(message, "edited", False) and updated_at else None,
    }
    return payload


logger = logging.getLogger(__name__)


def broadcast_message_edited_sync(message, is_group):
    """Push message_edited to chat_<chat_id> for subscribers (same channel as new_message)."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    chat_id = chat_id_from_message(message)
    if not chat_id:
        return
    try:
        payload = build_message_payload_for_ws(message, is_group)
    except Exception as e:
        logger.warning("Chat WS build_message_payload_for_ws (edit) failed: %s", e)
        return
    group_name = f"chat_{chat_id}"
    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "chat.message_edited", "chat_id": chat_id, "payload": payload},
        )
    except Exception as e:
        logger.warning("Chat WS message_edited group_send failed for %s: %s", group_name, e)


def chat_id_from_message(message):
    """Return chat_id (str) for a GroupMessages or IndividualMessages instance."""
    if isinstance(message, GroupMessages):
        return message.group.group_id
    if isinstance(message, IndividualMessages):
        return message.chat_id
    return None


def user_can_access_chat(user, chat_id):
    """
    Return True if user is a participant in the chat (DM or group).
    """
    if not chat_id or not user:
        return False
    try:
        if check_group_or_chat(chat_id):
            group = _get_group_object_sync(chat_id)
            if not isinstance(group, GroupChats):
                return False
            return GroupMembers.objects.filter(groupchat=group, participant=user).exists()
        else:
            chat = _get_individual_chat_object_sync(chat_id)
            if not hasattr(chat, "participant1"):  # HttpResponse from get
                return False
            return user in (chat.participant1, chat.participant2)
    except Exception:
        return False


def mark_seen_sync(user, chat_id, message_ids=None, last_message_id=None):
    """
    Mark messages as read. If message_ids given, mark those; else if last_message_id mark up to that;
    else mark all in chat as seen for this user.
    Returns dict for messages_seen broadcast: seen_by, seen_by_name, message_ids or last_seen_message_id, seen_at.
    """
    User = get_user_model()
    if not user or not chat_id:
        return None, "Invalid input"
    if not user_can_access_chat(user, chat_id):
        return None, "Not a participant"

    seen_at = timezone.now()
    if timezone.is_naive(seen_at):
        seen_at = timezone.make_aware(seen_at, timezone.utc)
    seen_at_str = seen_at.isoformat().replace("+00:00", "Z")

    if check_group_or_chat(chat_id):
        group = _get_group_object_sync(chat_id)
        if not isinstance(group, GroupChats):
            return None, "Invalid group"
        GroupMembers.objects.filter(groupchat=group, participant=user).update(seen=True, unseenmessages=0)
        return {
            "seen_by": user.username,
            "seen_by_name": _sender_name(user),
            "message_ids": message_ids or [],
            "last_seen_message_id": last_message_id,
            "seen_at": seen_at_str,
        }, None
    else:
        chat = _get_individual_chat_object_sync(chat_id)
        if not hasattr(chat, "participant1"):
            return None, "Invalid chat"
        qs = IndividualMessages.objects.filter(chat=chat).exclude(sender=user)
        if message_ids is not None:
            qs = qs.filter(id__in=message_ids)
        elif last_message_id is not None:
            qs = qs.filter(id__lte=last_message_id)
        qs.update(seen=True)
        last_id = last_message_id
        if message_ids:
            last_id = max(message_ids) if message_ids else None
        elif last_message_id is None and message_ids is None:
            last_in_chat = IndividualMessages.objects.filter(chat=chat).order_by("-id").values_list("id", flat=True).first()
            last_id = last_in_chat
        return {
            "seen_by": user.username,
            "seen_by_name": _sender_name(user),
            "message_ids": list(message_ids) if message_ids else [],
            "last_seen_message_id": last_id,
            "seen_at": seen_at_str,
        }, None
