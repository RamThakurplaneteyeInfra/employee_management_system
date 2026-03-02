from asgiref.sync import sync_to_async
from ems.verify_methods import *
from accounts.filters import _get_users_Name_sync
from .models import *
from .utils import gmt_to_ist_date_str, gmt_to_ist_time_str
from .s3_utils import get_file_url as s3_get_file_url

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #


# ==================== get_group_object ====================
def _get_group_object_sync(group_id: str):
    """Sync helper: DB query."""
    try:
        return GroupChats.objects.get(group_id=group_id)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=404)


async def get_group_object(group_id: str):
    return await sync_to_async(_get_group_object_sync)(group_id)


# ==================== get_groupmember_object ====================
def _get_groupmember_object_sync(group: GroupChats, participant: User):
    """Sync helper: DB query."""
    try:
        return GroupMembers.objects.get(groupchat=group, participant=participant)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=404)


async def get_groupmember_object(group: GroupChats, participant: User):
    return await sync_to_async(_get_groupmember_object_sync)(group, participant)


# ==================== check_user_member ====================
def check_user_member(user: User, group_id: str):
    """Sync: uses get_group_object."""
    group = _get_group_object_sync(group_id=group_id)
    if isinstance(group, GroupChats):
        member_instance = _get_groupmember_object_sync(group=group, participant=user)
        if isinstance(member_instance, GroupMembers):
            return member_instance
        return member_instance
    return group


# ==================== get_individual_chat_object ====================
def _get_individual_chat_object_sync(chat_id: str):
    """Sync helper: DB query."""
    try:
        return IndividualChats.objects.get(chat_id=chat_id)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=404)


async def get_individual_chat_object(chat_id: str):
    return await sync_to_async(_get_individual_chat_object_sync)(chat_id)


# ==================== check_group_or_chat ====================
def check_group_or_chat(id: str):
    return id.startswith("G")


# ==================== get_group_members ====================
def _get_group_members_sync(group_id: str):
    """Sync helper: DB query."""
    try:
        group_obj = get_object_or_404(GroupChats, group_id=group_id)
        members = GroupMembers.objects.filter(groupchat=group_obj).select_related("participant").annotate(
            participant_name=F("participant__accounts_profile__Name")
        ).values("participant", "participant_name", "groupchat")
        return JsonResponse(list(members), safe=False)
    except Http404 as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_404_NOT_FOUND)


async def get_group_members(group_id: str):
    return await sync_to_async(_get_group_members_sync)(group_id)


def _attachment_payload(a):
    """Build attachment dict for API: link or file."""
    if a.link_url:
        return {"id": a.id, "type": "link", "url": a.link_url, "title": a.link_title or a.link_url}
    return {"id": a.id, "type": "file", "file_name": a.file_name, "url": s3_get_file_url(a.s3_key)}


def _message_content_for_response(content):
    """
    Return message text for the 'message' field. If content is a file placeholder
    (e.g. client-sent '[FILE:...]'), return empty string so attachment data
    is only exposed via the 'attachments' attribute.
    """
    if not content or not isinstance(content, str):
        return ""
    s = content.strip()
    if s.startswith("[FILE:") and "]" in s:
        return ""
    return content


# ==================== get_messages ====================
def _get_messages_sync(request: HttpRequest, chat_id: str):
    """Unified timeline: message (with optional attachment), or attachment-only (standalone MessageAttachment in group/chat)."""
    try:
        is_group = True
        group_obj = get_object_or_404(GroupChats, group_id=chat_id)
    except Http404:
        is_group = False
        group_obj = None

    def _sender_name(sender):
        if sender is None:
            return None
        profile = getattr(sender, "accounts_profile", None)
        return getattr(profile, "Name", None) if profile else _get_users_Name_sync(sender)

    if is_group and group_obj:
        participants = GroupMembers.objects.filter(groupchat=group_obj).select_related("participant")
        flag = any(request.user == i.participant for i in participants)
        if not flag:
            return JsonResponse({"message": "you are not authorised to accessed this conversation"}, status=status.HTTP_403_FORBIDDEN)
        messages = (
            GroupMessages.objects.filter(group=group_obj)
            .select_related("sender__accounts_profile")
            .prefetch_related("attachments")
            .order_by("-created_at")
        )
        standalone = list(
            MessageAttachment.objects.filter(group=group_obj)
            .select_related("uploaded_by__accounts_profile")
            .order_by("-created_at")
        )
        GroupMembers.objects.filter(groupchat=group_obj, participant=request.user).update(seen=True, unseenmessages=0)
    else:
        try:
            chat_obj = get_object_or_404(IndividualChats, chat_id=chat_id)
        except Http404 as e:
            return JsonResponse({"message": f"{e}"}, status=status.HTTP_403_FORBIDDEN)
        messages = (
            IndividualMessages.objects.filter(chat=chat_obj)
            .select_related("sender__accounts_profile")
            .prefetch_related("attachments")
            .order_by("-created_at")
        )
        standalone = list(
            MessageAttachment.objects.filter(chat=chat_obj)
            .select_related("uploaded_by__accounts_profile")
            .order_by("-created_at")
        )
        other = chat_obj.get_other_participant(request.user)
        if other:
            IndividualMessages.objects.filter(chat=chat_obj, sender=other, seen=False).update(seen=True)

    items = []
    for m in messages:
        attachments = [_attachment_payload(a) for a in m.attachments.all()]
        items.append({
            "id": m.id,
            "sender": _sender_name(m.sender),
            "message": _message_content_for_response(m.content),
            "date": gmt_to_ist_date_str(m.created_at),
            "time": gmt_to_ist_time_str(m.created_at),
            "attachments": attachments,
            "_sort_at": m.created_at,
        })
    for a in standalone:
        items.append({
            "id": None,
            "sender": _sender_name(a.uploaded_by),
            "message": "",
            "date": gmt_to_ist_date_str(a.created_at),
            "time": gmt_to_ist_time_str(a.created_at),
            "attachments": [_attachment_payload(a)],
            "_sort_at": a.created_at,
        })

    items.sort(key=lambda x: x["_sort_at"], reverse=True)
    for it in items:
        del it["_sort_at"]

    return JsonResponse(items, safe=False)


async def get_messages(request: HttpRequest, chat_id: str):
    return await sync_to_async(_get_messages_sync)(request, chat_id)
