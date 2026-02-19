from asgiref.sync import sync_to_async
from ems.verify_methods import *
from accounts.filters import _get_users_Name_sync
from .models import *

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


# ==================== get_messages ====================
def _get_messages_sync(request: HttpRequest, chat_id: str):
    """Sync helper: DB operations for group or individual messages."""
    try:
        is_group = True
        group_obj = get_object_or_404(GroupChats, group_id=chat_id)
    except Http404:
        is_group = False
        group_obj = None

    if is_group and group_obj:
        participants = GroupMembers.objects.filter(groupchat=group_obj).select_related("participant")
        flag = any(request.user == i.participant for i in participants)
        if not flag:
            return JsonResponse({"message": "you are not authorised to accessed this conversation"}, status=status.HTTP_403_FORBIDDEN)
        messages = GroupMessages.objects.filter(group=group_obj).order_by("-created_at")
        GroupMembers.objects.filter(groupchat=group_obj, participant=request.user).update(seen=True)
    else:
        try:
            chat_obj = get_object_or_404(IndividualChats, chat_id=chat_id)
        except Http404 as e:
            return JsonResponse({"message": f"{e}"}, status=status.HTTP_403_FORBIDDEN)
        messages = IndividualMessages.objects.filter(chat=chat_obj).order_by("-created_at")

    data = [
        {
            "sender": _get_users_Name_sync(m.sender),
            "message": m.content,
            "date": m.created_at.strftime("%d/%m/%y"),
            "time": m.created_at.strftime("%H:%M"),
        }
        for m in messages
    ]
    return JsonResponse(data, safe=False)


async def get_messages(request: HttpRequest, chat_id: str):
    return await sync_to_async(_get_messages_sync)(request, chat_id)
