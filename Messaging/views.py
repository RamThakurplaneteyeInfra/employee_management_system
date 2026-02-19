from asgiref.sync import sync_to_async
from accounts.models import Profile
from ems.verify_methods import *
from .models import *
from .permissions import *
from .snippet import add_participant_to_groupMembers
from .filters import (
    _get_group_object_sync,
    _get_group_members_sync,
    _get_messages_sync,
    _get_individual_chat_object_sync,
    get_group_members,
    get_messages,
    check_group_or_chat,
)
from accounts.filters import _get_user_object_sync, _get_users_Name_sync, _get_user_role_sync, get_created_time_format

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #


# ==================== access_or_create_conversation ====================
# Get or create individual conversation with a participant.
# URL: {{baseurl}}/messaging/startChat/
# Method: POST
def _access_or_create_conversation_sync(req, participant_username):
    """Sync helper: DB operations for get/create individual chat."""
    user1 = User.objects.get(username=participant_username)
    user2 = req.user
    obj, is_created = IndividualChats.get_or_create_indivisual_Chat(user1=user1, user2=user2)
    if not is_created:
        other_user = obj.get_other_participant(req.user)
        return {"json": {"chat_id": obj.chat_id, "participant": _get_users_Name_sync(other_user), "messages": {}}}
    return {"messages": _get_messages_sync(req, chat_id=obj.chat_id)}


@csrf_exempt
@login_required
async def access_or_create_conversation(request: HttpRequest):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    data = load_data(request)
    try:
        result = await sync_to_async(_access_or_create_conversation_sync)(request, data.get("participant"))
        if "json" in result:
            return JsonResponse(result["json"])
        return result["messages"]
    except User.DoesNotExist:
        return JsonResponse({"message": "Invalid User."}, status=status.HTTP_404_NOT_FOUND)


# ==================== create_group ====================
# Create new group chat.
# URL: {{baseurl}}/messaging/createGroup/
# Method: POST
def _create_group_sync(req, data):
    """Sync helper: DB operations for group creation and adding participants."""
    has_permission = has_group_create_or_add_member_permission(req.user)
    current_user_name = Profile.objects.get(Employee_id=req.user).Name
    if not current_user_name:
        return {"error": JsonResponse({"message": "You cannot create your group, untill you Complete your profile"}, status=status.HTTP_304_NOT_MODIFIED)}
    if not has_permission:
        raise PermissionDenied("Not allowed")
    group_create_fields = ["group_name", "description", "participants"]
    temp_dict = {}
    for i in group_create_fields:
        if (i == "group_name" or i == "participants") and not data.get(i):
            return {"error": JsonResponse({"message": "Participants are required"}, status=status.HTTP_406_NOT_ACCEPTABLE)}
        elif i == "participants":
            temp_dict[i] = len(data.get(i))
        else:
            temp_dict[i] = data.get(i)
    temp_dict["created_by"] = req.user
    temp_dict["group_id"] = generate_group_id()
    chat = GroupChats.objects.create(**temp_dict)
    chat.save()
    participants_data = data.get("participants")
    for i in participants_data:
        user = _get_user_object_sync(username=participants_data[i])
        if isinstance(user, User):
            add_participant_to_groupMembers(group_chat=chat, participant=user)
        else:
            return {"error": JsonResponse(user, status=status.HTTP_304_NOT_MODIFIED)}
    return {"ok": True}


@csrf_exempt
@login_required
async def create_group(request: HttpRequest):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    try:
        data = load_data(request=request)
        result = await sync_to_async(_create_group_sync)(request, data)
        if "error" in result:
            return result["error"]
        return JsonResponse({"Messsage": "Group created successfully"}, status=status.HTTP_201_CREATED)
    except PermissionDenied:
        return JsonResponse({"message": "you cannot create a Group. Kindly contact your TeamLead/Admin"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_304_NOT_MODIFIED)


# ==================== api_to_get_group_members ====================
# Fetch group members for a group_id.
# URL: {{baseurl}}/messaging/showGroupMembers/<group_id>/
# Method: GET
@login_required
async def api_to_get_group_members(request: HttpRequest, group_id: str):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    return  await get_group_members(group_id=group_id)


# ==================== add_user ====================
# Add a user to a group.
# URL: {{baseurl}}/messaging/addUser/<group_id>/
# Method: POST
def _add_user_sync(req, group_id, participant_username):
    """Sync helper: DB operations to add participant to group."""
    group_obj = get_object_or_404(GroupChats, group_id=group_id)
    if not has_group_create_or_add_member_permission(req.user):
        raise PermissionDenied("Not allowed")
    present_members = _get_group_members_sync(group_id=group_id)
    data = json.loads(present_members.content.decode('utf-8'))
    for i in data:
        if i.get("participant") == participant_username:
            return {"error": JsonResponse({"Message": "user Already Exists"}, status=status.HTTP_302_FOUND)}
        elif i.get("message"):
            return {"response": present_members}
        user = _get_user_object_sync(username=participant_username)
    if isinstance(user, User):
        add_participant_to_groupMembers(group_chat=group_obj, participant=user)
        group_obj.participants += 1
        group_obj.save()
        return {"ok": True}
    return {"error": JsonResponse(user, status=status.HTTP_304_NOT_MODIFIED)}


@csrf_exempt
@login_required
async def add_user(request: HttpRequest, group_id: str):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    try:
        request_data = load_data(request)
        result = await sync_to_async(_add_user_sync)(request, group_id, request_data.get("participant"))
        if "error" in result:
            return result["error"]
        if "response" in result:
            return result["response"]
        return JsonResponse({"Message": "user added Successfully"}, status=status.HTTP_201_CREATED)
    except PermissionDenied:
        return JsonResponse({"message": "you cannot create a Group. Kindly contact your TeamLead/Admin"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_403_FORBIDDEN)


# ==================== delete_user ====================
# Delete a member from a group.
# URL: {{baseurl}}/messaging/deleteUser/<group_id>/<user_id>/
# Method: DELETE
def _delete_user_sync(req, group_id, user_id):
    """Sync helper: DB operations to remove participant from group."""
    group_obj = get_object_or_404(GroupChats, group_id=group_id)
    user_obj = get_object_or_404(User, username=user_id)
    if not has_group_create_or_add_member_permission(req.user):
        raise PermissionDenied("Not allowed")
    if user_id == req.user.username:
        return {"error": JsonResponse({"Message": "self-deletion is prohibited"}, status=status.HTTP_404_NOT_FOUND)}
    if group_obj.created_by.username == user_id:
        return {"error": JsonResponse({"Message": "Cannot delete the Group Admin"}, status=status.HTTP_404_NOT_FOUND)}
    if _get_user_role_sync(user_obj) == "MD":
        return {"error": JsonResponse({"Message": "Cannot delete MD from the group"}, status=status.HTTP_404_NOT_FOUND)}
    group_member_obj = GroupMembers.objects.filter(groupchat=group_obj, participant=user_obj).first()
    if group_obj.participants > 2:
        group_member_obj.delete()
        group_obj.participants -= 1
        group_obj.save()
        return {"ok": "user deleted Successfully"}
    if not group_member_obj:
        return {"ok": "selected user is not a group member"}
    raise Http404("there should be at least 2 members in the group")


@csrf_exempt
@login_required
async def delete_user(request: HttpRequest, group_id: str, user_id: str):
    verify_method = verifyDelete(request)
    if verify_method:
        return verify_method
    try:
        result = await sync_to_async(_delete_user_sync)(request, group_id, user_id)
        if "error" in result:
            return result["error"]
        return JsonResponse({"Message": result["ok"]}, status=status.HTTP_200_OK)
    except Http404 as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_404_NOT_FOUND)
    except PermissionDenied:
        return JsonResponse({"message": "you cannot create a Group. Kindly contact your TeamLead/Admin"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)


# ==================== delete_group ====================
# Delete a group.
# URL: {{baseurl}}/messaging/deleteGroup/<group_id>/
# Method: DELETE
def _delete_group_sync(req, group_id):
    """Sync helper: DB operations to delete group."""
    group_obj = _get_group_object_sync(group_id=group_id)
    if isinstance(group_obj, GroupChats):
        if can_Delete_group(group=group_obj, user=req.user):
            group_obj.delete()
            return {"ok": True}
        raise PermissionDenied("Not allowed")
    return {"response": group_obj}


@csrf_exempt
@login_required
async def delete_group(request: HttpRequest, group_id: str):
    verify_method = verifyDelete(request)
    if verify_method:
        return verify_method
    try:
        result = await sync_to_async(_delete_group_sync)(request, group_id)
        if "response" in result:
            return result["response"]
        return JsonResponse({"message": "group deleted successfully"}, status=status.HTTP_202_ACCEPTED)
    except PermissionDenied:
        return JsonResponse({"message": "you cannot delete a Group."}, status=status.HTTP_403_FORBIDDEN)


# ==================== post_message ====================
# Post a message in a group or individual chat.
# URL: {{baseurl}}/messaging/postMessages/<chat_id>/
# Method: POST
def _post_message_sync(req, chat_id):
    """Sync helper: DB operations to create message in group or individual chat."""
    verify_method = verifyPost(req)
    if verify_method:
        return verify_method
    data = load_data(req)
    message = data.get("Message")
    if not message:
        return JsonResponse({"message": "Message is empty"}, status=status.HTTP_204_NO_CONTENT)
    is_group = check_group_or_chat(id=chat_id)
    if is_group:
        chat_obj = _get_group_object_sync(group_id=chat_id)
        if not isinstance(chat_obj, GroupChats):
            raise Http404("Invalid Group_id")
        GroupMessages.objects.create(group=chat_obj, sender=req.user, content=message).save()
        chat_obj.save()
    else:
        chat_obj = _get_individual_chat_object_sync(chat_id)
        if not isinstance(chat_obj, IndividualChats):
            raise Http404("Invalid chat_id")
        IndividualMessages.objects.create(chat=chat_obj, sender=req.user, content=message)
        chat_obj.save()


@csrf_exempt
@login_required
async def post_message(request: HttpRequest, chat_id: str):
    try:
        await sync_to_async(_post_message_sync)(request, chat_id)
        return JsonResponse({"message": "Message sent successfully"}, status=status.HTTP_201_CREATED)
    except Http404:
        return JsonResponse({"message": "Invalid chat/group id"}, status=status.HTTP_400_BAD_REQUEST)


# ==================== get_chats ====================
# Fetch messages from a conversation (group or individual).
# URL: {{baseurl}}/messaging/getMessages/<chat_id>/
# Method: GET
@login_required
async def get_chats(request: HttpRequest, chat_id: str):
    request_method = verifyGet(request)
    if request_method:
        return request_method
    return await get_messages(request=request, chat_id=chat_id)


# ==================== load_groups_and_chats ====================
# Load groups and individual chats for logged-in user.
# URL: {{baseurl}}/messaging/loadChats/
# Method: GET
def _load_groups_and_chats_sync(user):
    """Sync helper: DB operations to fetch user's groups and individual chats."""
    groups = GroupMembers.objects.select_related("groupchat").filter(participant=user).annotate(group_id=F("groupchat__group_id"),group_name=F("groupchat__group_name"),
                description=F("groupchat__description"),created_by=F("groupchat__created_by__accounts_profile__Name"),total_participant=F("groupchat__participants"),created_at=F("groupchat__created_at")).values("group_id","group_name",
                        "total_participant","created_by","description","created_at")
    chats = IndividualChats.objects.filter(Q(participant1=user) | Q(participant2=user))
    # groups_info = [{
    #     "group_id": g.groupchat.group_id,
    #     "group_name": g.groupchat.group_name,
    #     "total_participant": g.groupchat.participants,
    #     "created_by": _get_users_Name_sync(g.groupchat.created_by),
    #     "description": g.groupchat.description,
    #     "created_at": get_created_time_format(g.groupchat.created_at)
    # } for g in groups]
    chats_info = [{"chat_id": c.chat_id, "with": _get_users_Name_sync(c.get_other_participant(user))} for c in chats]
    return {"Group_info": list(groups), "chats_info": chats_info}


@login_required
async def load_groups_and_chats(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    response = await sync_to_async(_load_groups_and_chats_sync)(request.user)
    return JsonResponse(response, safe=False)


# ==================== search_or_find_conversation ====================
# Find conversations by participant name. (Un-used API)
# URL: {{baseurl}}/messaging/... (if configured)
# Method: GET
def _search_conversation_sync(user, search_name):
    """Sync helper: DB query for profiles by name prefix."""
    if search_name:
        profiles = Profile.objects.filter(Name__startswith=search_name).exclude(Employee_id=user).order_by("Name").values("Names")
    else:
        profiles = Profile.objects.exclude(Employee_id=user).order_by("Name").values("Names")
    return list(profiles)


@login_required
async def search_or_find_conversation(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    search_name = request.GET.get("search_name") if request.GET else None
    profiles = await sync_to_async(_search_conversation_sync)(request.user, search_name)
    return JsonResponse(profiles, safe=False)


# ==================== delete_message ====================
# Delete a particular message. (Placeholder)
# URL: {{baseurl}}/messaging/... (if configured)
# Method: DELETE
@login_required
async def delete_message(request: HttpRequest, chat_id: str, msg_id: int):
    ...


# ==================== update_group ====================
# Update group name/description. Creator only.
# URL: {{baseurl}}/messaging/... (if configured)
# Method: PATCH
def _update_group_sync(req, group_id, data):
    """Sync helper: DB operations to update group fields."""
    group_obj = get_object_or_404(GroupChats, group_id=group_id)
    if req.user != group_obj.created_by:
        raise PermissionDenied("Not Allowed")
    for field in ["group_name", "description"]:
        field_value = data.get(field)
        if field_value:
            setattr(group_obj, field, field_value)
    group_obj.save()


@csrf_exempt
@login_required
async def update_group(request: HttpRequest, group_id: str):
    verify_method = verifyPatch(request)
    if verify_method:
        return verify_method
    try:
        data = load_data(request=request)
        await sync_to_async(_update_group_sync)(request, group_id, data)
        return JsonResponse({"Messsage": "Group details updated successfully"}, status=status.HTTP_201_CREATED)
    except Http404 as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_404_NOT_FOUND)
    except PermissionDenied:
        return JsonResponse({"message": "Permission denied"}, status=status.HTTP_404_NOT_FOUND)


# ==================== show_created_groups ====================
# Show groups created by the logged-in user.
# URL: {{baseurl}}/messaging/showCreatedGroups/
# Method: GET
def _show_created_groups_sync(user):
    """Sync helper: DB query for groups created by user."""
    groups = GroupChats.objects.filter(created_by=user).order_by("-created_at").values()
    return [{"group_id": g.group_id, "total_participant": g.participants, "name": g.group_name,
        "description": g.description, "created_at": get_created_time_format(g.created_at)} for g in groups]


@login_required
async def show_created_groups(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    info = await sync_to_async(_show_created_groups_sync)(request.user)
    return JsonResponse(info, safe=False)
