import json
from asgiref.sync import sync_to_async
from django.db.models import F, Count
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
from .chat_ws_utils import mark_seen_sync
from accounts.filters import _get_user_object_sync, _get_users_Name_sync, _get_user_role_sync
from .utils import gmt_to_ist_str
from .s3_utils import upload_file as s3_upload_file, get_file_url as s3_get_file_url
from ems.s3_utils import delete_file_from_files as s3_delete_file

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
        return {"error": JsonResponse({"message": "You cannot create your group, untill you Complete your profile"}, status=status.HTTP_400_BAD_REQUEST)}
    if not has_permission:
        raise PermissionDenied("Not allowed")
    group_create_fields = ["group_name", "description", "participants"]
    temp_dict = {}
    for i in group_create_fields:
        if (i == "group_name" or i == "participants") and not data.get(i):
            return {"error": JsonResponse({"message": "Participants are required"}, status=status.HTTP_400_BAD_REQUEST)}
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
            return {"error": JsonResponse(user, status=status.HTTP_400_BAD_REQUEST)}
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
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)


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
            return {"error": JsonResponse({"Message": "user Already Exists"}, status=status.HTTP_409_CONFLICT)}
        elif i.get("message"):
            return {"response": present_members}
        user = _get_user_object_sync(username=participant_username)
    if isinstance(user, User):
        add_participant_to_groupMembers(group_chat=group_obj, participant=user)
        group_obj.participants += 1
        group_obj.save()
        return {"ok": True}
    return {"error": JsonResponse(user, status=status.HTTP_400_BAD_REQUEST)}


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
def _parse_attachment_ids(value):
    """Parse attachment_ids from JSON string or return list."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _attachment_is_linked(att):
    """True if attachment is already used (linked to a message or standalone in group/chat)."""
    return bool(
        att.group_message_id or att.individual_message_id or att.group_id or att.chat_id
    )


def _get_unlinked_attachments_queryset(user, attachment_ids):
    """
    Return attachments that: belong to user, are in attachment_ids,
    and are not yet linked (no group_message, individual_message, group, or chat set).
    """
    if not attachment_ids:
        return MessageAttachment.objects.none()
    return MessageAttachment.objects.filter(
        id__in=attachment_ids,
        uploaded_by=user,
        group_message__isnull=True,
        individual_message__isnull=True,
        group__isnull=True,
        chat__isnull=True,
    )


def _post_message_sync(req, chat_id):
    """
    Post a message and/or attachments to a group or individual chat.

    Logic:
    1) Standalone: user uploads file and posts with empty content → add group_id/chat_id to
       MessageAttachment only (no message row). Attachment appears as standalone in the conversation.
    2) Message with attachment: user sends non-empty message along with attachment → create message
       row, then add group_message_id/individual_message_id to MessageAttachment for the first attachment.
    3) Message only: create GroupMessages/IndividualMessages with content, no attachment.
    """
    verify_method = verifyPost(req)
    if verify_method:
        return verify_method

    data = load_data(req)
    message_text = (data.get("Message") or "").strip()
    attachment_ids = _parse_attachment_ids(data.get("attachment_ids"))
    has_text = bool(message_text)
    has_attachments = bool(attachment_ids)

    if not (has_text or has_attachments):
        return JsonResponse({"message": "Message or attachments required"}, status=status.HTTP_400_BAD_REQUEST)

    is_group = check_group_or_chat(id=chat_id)

    if is_group:
        conv = _get_group_object_sync(group_id=chat_id)
        if not isinstance(conv, GroupChats):
            raise Http404("Invalid Group_id")
        _post_to_group(req, conv, message_text, attachment_ids, has_text, has_attachments)
        conv.save(update_fields=["last_message_at"])
    else:
        conv = _get_individual_chat_object_sync(chat_id)
        if not isinstance(conv, IndividualChats):
            raise Http404("Invalid chat_id")
        _post_to_chat(req, conv, message_text, attachment_ids, has_text, has_attachments)
        conv.save(update_fields=["last_message_at"])


def _post_to_group(req, group_obj, message_text, attachment_ids, has_text, has_attachments):
    """
    Handle post_message for a group.
    - Empty content + attachments → standalone: set group_id on MessageAttachment.
    - Non-empty content + attachments → create message, set group_message_id on MessageAttachment.
    - Message only → create GroupMessages with content.
    """
    if has_text and has_attachments:
        # Message with attachment: create message, then link first attachment via group_message_id
        msg = GroupMessages.objects.create(
            group=group_obj,
            sender=req.user,
            content=message_text,
        )
        unlinked = _get_unlinked_attachments_queryset(req.user, attachment_ids)
        unlinked.update(group_message=msg, group=None, chat=None)
        
    elif has_text:
        # Message only
        GroupMessages.objects.create(
            group=group_obj,
            sender=req.user,
            content=message_text,
        )
    else:
        # Standalone: empty content + attachments → add group_id to MessageAttachment
        unlinked = _get_unlinked_attachments_queryset(req.user, attachment_ids)
        unlinked.update(group=group_obj)


def _post_to_chat(req, chat_obj, message_text, attachment_ids, has_text, has_attachments):
    """
    Handle post_message for an individual chat.
    - Empty content + attachments → standalone: set chat_id on MessageAttachment.
    - Non-empty content + attachments → create message, set individual_message_id on MessageAttachment.
    - Message only → create IndividualMessages with content.
    """
    if has_text and has_attachments:
        # Message with attachment: create message, then link first attachment via individual_message_id
        msg = IndividualMessages.objects.create(
            chat=chat_obj,
            sender=req.user,
            content=message_text,
        )
        unlinked = _get_unlinked_attachments_queryset(req.user, attachment_ids)
        unlinked.update(individual_message=msg, group=None, chat=None)
    elif has_text:
        # Message only
        IndividualMessages.objects.create(
            chat=chat_obj,
            sender=req.user,
            content=message_text,
        )
    else:
        # Standalone: empty content + attachments → add chat_id to MessageAttachment
        unlinked = _get_unlinked_attachments_queryset(req.user, attachment_ids)
        unlinked.update(chat=chat_obj)


@csrf_exempt
@login_required
async def post_message(request: HttpRequest, chat_id: str):
    try:
        await sync_to_async(_post_message_sync)(request, chat_id)
        return JsonResponse({"message": "Message sent successfully"}, status=status.HTTP_201_CREATED)
    except Http404:
        return JsonResponse({"message": "Invalid chat/group id"}, status=status.HTTP_400_BAD_REQUEST)


# ==================== upload_message_file ====================
# Upload a file to S3 and create a MessageAttachment record (unlinked). Client sends attachment_ids in post_message to link.
# URL: {{baseurl}}/messaging/uploadFile/
# Method: POST (multipart/form-data), field name: file
def _upload_message_file_sync(req):
    """Sync helper: upload file to S3 and create MessageAttachment."""
    if req.method != "POST":
        return {"error": JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)}
    file_obj = req.FILES.get("file")
    if not file_obj:
        return {"error": JsonResponse({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)}
    try:
        s3_key = s3_upload_file(file_obj)
    except Exception as e:
        return {"error": JsonResponse({"error": f"Upload failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)}
    file_name = getattr(file_obj, "name", "file") or "file"
    content_type = getattr(file_obj, "content_type", "") or ""
    file_size = getattr(file_obj, "size", None)
    att = MessageAttachment.objects.create(
        s3_key=s3_key,
        file_name=file_name,
        content_type=content_type or None,
        file_size=file_size,
        uploaded_by=req.user,
    )
    url = s3_get_file_url(s3_key)
    return {
        "data": {
            "id": att.id,
            "s3_key": s3_key,
            "file_name": file_name,
            "content_type": content_type,
            "file_size": file_size,
            "url": url,
        }
    }

@csrf_exempt
@login_required
async def upload_message_file(request: HttpRequest):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    result = await sync_to_async(_upload_message_file_sync)(request)
    if "error" in result:
        return result["error"]
    return JsonResponse(result["data"], status=status.HTTP_201_CREATED)


# ==================== add_link ====================
# Add a link attachment (unlinked). Client sends attachment_ids in postMessages to link to a message.
# URL: {{baseurl}}/messaging/addLink/
# Method: POST (JSON), body: { "url": "https://...", "title": "optional" }
def _add_link_sync(req):
    """Sync helper: create MessageAttachment for a shared link."""
    if req.method != "POST":
        return {"error": JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)}
    data = load_data(req)
    url = (data.get("url") or "").strip()
    if not url:
        return {"error": JsonResponse({"error": "url is required"}, status=status.HTTP_400_BAD_REQUEST)}
    title = (data.get("title") or data.get("link_title") or "").strip() or None
    att = MessageAttachment.objects.create(
        link_url=url,
        link_title=title,
        uploaded_by=req.user,
    )
    return {
        "data": {
            "id": att.id,
            "url": att.link_url,
            "title": att.link_title,
        }
    }


@csrf_exempt
@login_required
async def add_link(request: HttpRequest):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    result = await sync_to_async(_add_link_sync)(request)
    if "error" in result:
        return result["error"]
    return JsonResponse(result["data"], status=status.HTTP_201_CREATED)


# ==================== delete_attachment ====================
# Delete an uploaded file or link that is not yet sent. Only uploader can delete; only unlinked attachments.
# URL: {{baseurl}}/messaging/attachments/<attachment_id>/
# Method: DELETE
def _delete_attachment_sync(req, attachment_id):
    """Sync helper: delete attachment if uploader and not linked to a message; remove file from S3 if file."""
    try:
        att = MessageAttachment.objects.get(id=attachment_id)
    except MessageAttachment.DoesNotExist:
        return {"error": JsonResponse({"error": "Attachment not found"}, status=status.HTTP_404_NOT_FOUND)}
    if att.uploaded_by != req.user:
        return {"error": JsonResponse({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)}
    if _attachment_is_linked(att):
        return {"error": JsonResponse({"error": "Cannot delete attachment that is already sent"}, status=status.HTTP_400_BAD_REQUEST)}
    if att.s3_key:
        s3_delete_file(att.s3_key)
    att.delete()
    return {"ok": True}


@csrf_exempt
@login_required
async def delete_attachment(request: HttpRequest, attachment_id: int):
    verify_method = verifyDelete(request)
    if verify_method:
        return verify_method
    result = await sync_to_async(_delete_attachment_sync)(request, attachment_id)
    if "error" in result:
        return result["error"]
    return JsonResponse({"message": "Attachment deleted"}, status=status.HTTP_200_OK)


# ==================== get_attachment_url ====================
# Get a presigned URL for an attachment (for display/download). User must have access via message membership.
# URL: {{baseurl}}/messaging/files/<attachment_id>/url/
# Method: GET
def _get_attachment_url_sync(req, attachment_id):
    """Sync helper: return presigned URL if user can access (linked to message in group/chat, standalone in group/chat, or own unlinked upload)."""
    try:
        att = MessageAttachment.objects.select_related(
            "group_message__group", "individual_message__chat", "group", "chat"
        ).get(id=attachment_id)
    except MessageAttachment.DoesNotExist:
        return {"error": JsonResponse({"error": "Attachment not found"}, status=status.HTTP_404_NOT_FOUND)}
    # Access: attachment references the message (or is standalone)
    if att.group_message_id:
        if not GroupMembers.objects.filter(groupchat=att.group_message.group, participant=req.user).exists():
            return {"error": JsonResponse({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)}
        if att.link_url:
            return {"data": {"url": att.link_url, "file_name": att.link_title, "type": "link"}}
        return {"data": {"url": s3_get_file_url(att.s3_key), "file_name": att.file_name, "type": "file"}}
    if att.individual_message_id:
        chat = att.individual_message.chat
        if req.user != chat.participant1 and req.user != chat.participant2:
            return {"error": JsonResponse({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)}
        if att.link_url:
            return {"data": {"url": att.link_url, "file_name": att.link_title, "type": "link"}}
        return {"data": {"url": s3_get_file_url(att.s3_key), "file_name": att.file_name, "type": "file"}}
    # Standalone in group or chat
    if att.group_id:
        if not GroupMembers.objects.filter(groupchat=att.group, participant=req.user).exists():
            return {"error": JsonResponse({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)}
    elif att.chat_id:
        chat = att.chat
        if req.user != chat.participant1 and req.user != chat.participant2:
            return {"error": JsonResponse({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)}
    else:
        if att.uploaded_by != req.user:
            return {"error": JsonResponse({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)}
    if att.link_url:
        return {"data": {"url": att.link_url, "file_name": att.link_title, "type": "link"}}
    return {"data": {"url": s3_get_file_url(att.s3_key), "file_name": att.file_name, "type": "file"}}


@login_required
async def get_attachment_url(request: HttpRequest, attachment_id: int):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    result = await sync_to_async(_get_attachment_url_sync)(request, attachment_id)
    if "error" in result:
        return result["error"]
    return JsonResponse(result["data"])


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


# ==================== mark_seen (REST) ====================
# POST /messaging/markSeen/<chat_id>/ with body { "message_ids": [101, 102] } or { "last_message_id": 103 }
@csrf_exempt
@login_required
def mark_seen(request: HttpRequest, chat_id: str):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    data = load_data(request)
    message_ids = data.get("message_ids")
    last_message_id = data.get("last_message_id")
    if message_ids is not None and not isinstance(message_ids, list):
        message_ids = None
    payload, err = mark_seen_sync(
        request.user, chat_id,
        message_ids=message_ids,
        last_message_id=last_message_id,
    )
    if err:
        return JsonResponse({"message": err}, status=status.HTTP_403_FORBIDDEN)
    if payload:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    f"chat_{chat_id}",
                    {"type": "chat.messages_seen", "chat_id": chat_id, "payload": payload},
                )
            except Exception:
                pass
    return JsonResponse({"status": "ok"}, status=status.HTTP_200_OK)


# ==================== load_groups_and_chats ====================
# Load groups and individual chats for logged-in user, ordered by last_message_at.
# Includes unseen message count per group/chat.
# URL: {{baseurl}}/messaging/loadChats/
# Method: GET
def _load_groups_and_chats_sync(user):
    """Sync helper: DB operations to fetch user's groups and individual chats ordered by last_message_at with unseen counts. Optimized to minimize queries and avoid N+1."""
    # Groups: avoid cross-schema JOIN for creator name – fetch members+group then creator names in one extra query
    members_qs = (
        GroupMembers.objects.select_related("groupchat","groupchat__created_by__accounts_profile")
        .filter(participant=user)
        .order_by("-groupchat__last_message_at")
    )
    group_info = []
    # creator_usernames = set()
    for gm in members_qs:
        g = gm.groupchat
        creator_profile=getattr(g.created_by,"accounts_profile",None)
        # creator_usernames.add(g.created_by_id)
        group_info.append({
            "group_id": g.group_id,
            "group_name": g.group_name,
            "description": g.description,
            "total_participant": g.participants,
            # "created_at": gmt_to_ist_str(g.created_at, "%d/%m/%y %H:%M:%S") if g.created_at else None,
            "last_message_at": gmt_to_ist_str(g.last_message_at, "%d/%m/%y %H:%M:%S") if g.last_message_at else None,
            "unseen_count": gm.unseenmessages,
            "_created_by_id":creator_profile.Name if creator_profile else None
        })
    # creator_names = {}
    # if creator_usernames:
    #     creator_names = dict(
    #         Profile.objects.filter(Employee_id__in=creator_usernames).values_list("Employee_id", "Name")
    #     )
    # for row in group_info:
    #     row["created_by"] = creator_names.get(row.pop("_created_by_id", None), None)

    # Chats: one query with select_related to avoid N+1 on participant and profile
    chats_qs = (
        IndividualChats.objects.filter(Q(participant1=user) | Q(participant2=user))
        .select_related("participant1__accounts_profile", "participant2__accounts_profile")
        .order_by("-last_message_at")
    )
    chats_list = list(chats_qs)
    chat_ids = [c.chat_id for c in chats_list]
    unread_map = {}
    if chat_ids:
        unread_qs = (
            IndividualMessages.objects.filter(chat_id__in=chat_ids, seen=False)
            .exclude(sender=user)
            .values("chat_id")
            .annotate(unread=Count("id"))
        )
        unread_map = {r["chat_id"]: r["unread"] for r in unread_qs}

    def _other_name(c):
        other = c.get_other_participant(user)
        if other:
            profile = getattr(other, "accounts_profile", None)
            return profile.Name if profile else None
        return None

    chats_info = [
        {
            "chat_id": c.chat_id,
            "with": _other_name(c),
            "last_message_at": gmt_to_ist_str(c.last_message_at, "%d/%m/%y %H:%M:%S") if c.last_message_at else None,
            "unseen_count": unread_map.get(c.chat_id, 0),
        }
        for c in chats_list
    ]

    return {"Group_info": group_info, "chats_info": chats_info}


@login_required
async def load_groups_and_chats(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    response = await sync_to_async(_load_groups_and_chats_sync)(request.user)
    return JsonResponse(response, safe=False,status=status.HTTP_200_OK)


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
        return JsonResponse({"Messsage": "Group details updated successfully"}, status=status.HTTP_200_OK)
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
        "description": g.description, "created_at": gmt_to_ist_str(g.created_at, "%d/%m/%Y, %H:%M:%S")} for g in groups]


@login_required
async def show_created_groups(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    info = await sync_to_async(_show_created_groups_sync)(request.user)
    return JsonResponse(info, safe=False)
