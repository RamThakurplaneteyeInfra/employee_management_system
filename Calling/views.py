from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from asgiref.sync import sync_to_async
import json
import logging
from datetime import timedelta

from accounts.models import User, Profile
from ems.verify_methods import *
from .models import Call, GroupCall, GroupCallParticipant

# ==================== Voice/Video Call APIs ====================
# Call lifecycle: pending -> (accepted | declined | ended)
# - initiate_call: creates Call (pending), pushes incoming_call to receiver via WebSocket
# - accept_call: receiver only; pending -> accepted
# - decline_call: receiver only; pending -> declined
# - end_call: sender or receiver; pending/accepted -> ended
# Offline receiver: Call is still created; WebSocket push may fail silently (receiver not connected)

logger = logging.getLogger(__name__)

def _initiate_call_sync(req, user_id, call_type):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    # Validation: sender cannot call themselves
    if req.user.username == user_id:
        return {"error": "Cannot call yourself", "status": 400}
    try:
        receiver = User.objects.get(username=user_id)
    except User.DoesNotExist:
        return {"error": "Receiver not found", "status": 404}

    # Expire stale pending calls (never answered) older than 3 minutes
    stale = timezone.now() - timedelta(minutes=3)
    Call.objects.filter(
        Q(sender=receiver) | Q(receiver=receiver),
        status=Call.PENDING,
        timestamp__lt=stale,
    ).update(status=Call.ENDED)

    # Check if receiver is already in an active call (pending or accepted)
    active_call = Call.objects.filter(
        status__in=[Call.PENDING, Call.ACCEPTED],
    ).filter(Q(sender=receiver) | Q(receiver=receiver)).exists()
    if active_call:
        return {"error": "User is busy on another call", "status": 409}

    call = Call.objects.create(
        sender=req.user,
        receiver=receiver,
        call_type=call_type,
        status=Call.PENDING,
    )
    # Push incoming_call to receiver via WebSocket (offline receiver: no-op, no crash)
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"call_{receiver.username}",
                {
                    "type": "incoming_call",
                    "payload": {
                        "type": "incoming_call",
                        "call_id": call.id,
                        "sender": req.user.username,
                        "receiver": receiver.username,
                        "call_type": call_type,
                    },
                },
            )
        except Exception:
            # Receiver offline or channel error; call created, API succeeds
            pass
    return {
        "success": True,
        "call_id": call.id,
        "call_type": call.call_type,
        "sender": req.user.username,
        "receiver": receiver.username,
        "status": 201,
    }


@csrf_exempt
@login_required
async def initiate_call(request: HttpRequest):
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
        user_id = data.get("user_id")
        call_type = data.get("call_type", "audio")
        if not user_id:
            return JsonResponse({"success": False, "error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if call_type not in ("audio", "video"):
            return JsonResponse({"success": False, "error": "call_type must be 'audio' or 'video'"}, status=status.HTTP_400_BAD_REQUEST)
        result = await sync_to_async(_initiate_call_sync)(request, user_id, call_type)
        if "error" in result:
            return JsonResponse({"success": False, "error": result["error"]}, status=result.get("status", status.HTTP_400_BAD_REQUEST))
        return JsonResponse(
            {
                "success": True,
                "call_id": result["call_id"],
                "call_type": result["call_type"],
                "sender": result["sender"],
                "receiver": result["receiver"],
            },
            status=status.HTTP_201_CREATED,
        )
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)


def _accept_call_sync(req, call_id):
    try:
        call = Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        return {"error": "Call not found", "status": 404}
    if call.receiver != req.user:
        return {"error": "Only receiver can accept this call", "status": 403}
    if call.status != Call.PENDING:
        return {"error": f"Call is already {call.status}", "status": 400}
    call.status = Call.ACCEPTED
    call.save()
    return {
        "success": True,
        "call_id": call.id,
        "sender": call.sender.username,
        "receiver": call.receiver.username,
    }


@csrf_exempt
@login_required
async def accept_call(request: HttpRequest):
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        call_id = data.get("call_id")
        if call_id is None:
            return JsonResponse({"success": False, "error": "call_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        call_id = int(call_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "call_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    result = await sync_to_async(_accept_call_sync)(request, call_id)
    if "error" in result:
        return JsonResponse({"success": False, "error": result["error"]}, status=result.get("status", status.HTTP_400_BAD_REQUEST))
    # Notify sender that receiver accepted the call
    await sync_to_async(_notify_sender_call_accepted)(result["sender"], result["receiver"], call_id)
    return JsonResponse(
        {
            "success": True,
            "call_id": result["call_id"],
            "sender": result["sender"],
            "receiver": result["receiver"],
        },
        status=status.HTTP_200_OK,
    )


def _decline_call_sync(req, call_id):
    try:
        call = Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        return {"error": "Call not found", "status": 404}
    if call.receiver != req.user:
        return {"error": "Only receiver can decline this call", "status": 403}
    if call.status != Call.PENDING:
        return {"error": f"Call is already {call.status}", "status": 400}
    call.status = Call.DECLINED
    call.save()
    return {
        "success": True,
        "call_id": call.id,
        "sender": call.sender.username,
        "receiver": call.receiver.username,
    }


def _notify_sender_call_accepted(sender_username, receiver_username, call_id):
    """Send call_accepted to sender via WebSocket so caller knows receiver picked up."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"call_{sender_username}",
                {
                    "type": "call_accepted",
                    "payload": {
                        "type": "call_accepted",
                        "call_id": call_id,
                        "sender": sender_username,
                        "receiver": receiver_username,
                        "message": "Call received (accepted)",
                    },
                },
            )
            logger.info("Call accepted: sender=%s notified that receiver=%s accepted", sender_username, receiver_username)
        except Exception:
            pass


def _notify_sender_call_declined(sender_username, receiver_username, call_id):
    """Send call_declined to sender via WebSocket so caller knows receiver rejected."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"call_{sender_username}",
                {
                    "type": "call_declined",
                    "payload": {
                        "type": "call_declined",
                        "call_id": call_id,
                        "sender": sender_username,
                        "receiver": receiver_username,
                        "message": "Call declined",
                    },
                },
            )
            logger.info("Call declined: sender=%s notified that receiver=%s declined", sender_username, receiver_username)
        except Exception:
            pass


@csrf_exempt
@login_required
async def decline_call(request: HttpRequest):
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        call_id = data.get("call_id")
        if call_id is None:
            return JsonResponse({"success": False, "error": "call_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        call_id = int(call_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "call_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    result = await sync_to_async(_decline_call_sync)(request, call_id)
    if "error" in result:
        return JsonResponse({"success": False, "error": result["error"]}, status=result.get("status", status.HTTP_400_BAD_REQUEST))
    # Notify sender that receiver declined the call
    await sync_to_async(_notify_sender_call_declined)(result["sender"], result["receiver"], call_id)
    return JsonResponse(
        {
            "success": True,
            "call_id": result["call_id"],
            "sender": result["sender"],
            "receiver": result["receiver"],
        },
        status=status.HTTP_200_OK,
    )


def _end_call_sync(req, call_id):
    try:
        call = Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        return {"error": "Call not found", "status": 404}
    if call.sender != req.user and call.receiver != req.user:
        return {"error": "Only caller or receiver can end this call", "status": 403}
    if call.status == Call.ENDED:
        return {
            "success": True,
            "call_id": call.id,
            "sender": call.sender.username,
            "receiver": call.receiver.username,
        }
    call.status = Call.ENDED
    call.save()
    logger.info(
        "Call ended: call_id=%s sender=%s receiver=%s ended_by=%s",
        call.id, call.sender.username, call.receiver.username, req.user.username,
    )
    return {
        "success": True,
        "call_id": call.id,
        "sender": call.sender.username,
        "receiver": call.receiver.username,
    }


@csrf_exempt
@login_required
async def end_call(request: HttpRequest):
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        call_id = data.get("call_id")
        if call_id is None:
            return JsonResponse({"success": False, "error": "call_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        call_id = int(call_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "call_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    result = await sync_to_async(_end_call_sync)(request, call_id)
    if "error" in result:
        return JsonResponse({"success": False, "error": result["error"]}, status=result.get("status", status.HTTP_400_BAD_REQUEST))
    return JsonResponse(
        {
            "success": True,
            "call_id": result["call_id"],
            "sender": result["sender"],
            "receiver": result["receiver"],
        },
        status=status.HTTP_200_OK,
    )


def _get_pending_calls_sync(user):
    calls = Call.objects.filter(receiver=user, status=Call.PENDING).order_by("-timestamp")
    return [
        {
            "call_id": c.id,
            "sender": c.sender.username,
            "receiver": c.receiver.username,
            "call_type": c.call_type,
            "timestamp": c.timestamp.isoformat(),
        }
        for c in calls
    ]


def _get_active_calls_sync(user):
    """Return all active calls (pending or accepted) where user is sender or receiver.
    Use call_id from response with POST /messaging/endCall/ (or /calling/endCall/ if mounted there) to clear stuck calls and fix 409."""
    calls = (
        Call.objects.filter(Q(sender=user) | Q(receiver=user))
        .filter(status__in=[Call.PENDING, Call.ACCEPTED])
        .order_by("-timestamp")
    )
    return [
        {
            "call_id": c.id,
            "sender": c.sender.username,
            "receiver": c.receiver.username,
            "call_type": c.call_type,
            "status": c.status,
            "timestamp": c.timestamp.isoformat(),
        }
        for c in calls
    ]


@login_required
async def get_pending_calls(request: HttpRequest):
    if verifyGet(request):
        return verifyGet(request)
    result = await sync_to_async(_get_pending_calls_sync)(request.user)
    return JsonResponse(result, safe=False)


@login_required
async def get_active_calls(request: HttpRequest):
    """GET list of current user's active calls (pending/accepted). Use call_id with POST endCall/ to end them."""
    if verifyGet(request):
        return verifyGet(request)
    result = await sync_to_async(_get_active_calls_sync)(request.user)
    return JsonResponse(result, safe=False)


def _end_all_my_calls_sync(user):
    """End all active calls (pending/accepted) where current user is sender or receiver."""
    calls_before = list(
        Call.objects.filter(Q(sender=user) | Q(receiver=user))
        .filter(status__in=[Call.PENDING, Call.ACCEPTED])
        .values_list("id", "sender__username", "receiver__username")
    )
    updated = (
        Call.objects.filter(Q(sender=user) | Q(receiver=user))
        .filter(status__in=[Call.PENDING, Call.ACCEPTED])
        .update(status=Call.ENDED)
    )
    if updated:
        logger.info(
            "End all calls: user=%s ended_count=%s call_ids=%s",
            user.username, updated, [c[0] for c in calls_before],
        )
    return updated


@csrf_exempt
@login_required
async def end_all_my_calls(request: HttpRequest):
    """POST: End all of the current user's active calls. Returns how many were ended."""
    if verifyPost(request):
        return verifyPost(request)
    count = await sync_to_async(_end_all_my_calls_sync)(request.user)
    return JsonResponse(
        {"success": True, "ended_count": count, "message": f"Ended {count} call(s)."},
        status=status.HTTP_200_OK,
    )


# ==================== Group call APIs ====================

def _initiate_group_call_sync(req, user_ids, call_type):
    """Create a group call and invite users. Creator is auto-joined; others get incoming_group_call."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    if not user_ids or not isinstance(user_ids, list):
        return {"error": "user_ids must be a non-empty list", "status": 400}
    if call_type not in (GroupCall.AUDIO, GroupCall.VIDEO):
        return {"error": "call_type must be 'audio' or 'video'", "status": 400}
    creator = req.user
    # Remove self and duplicates
    usernames = list(dict.fromkeys(u for u in user_ids if isinstance(u, str) and u.strip() and u != creator.username))
    if not usernames:
        return {"error": "At least one other user_id is required", "status": 400}
    try:
        users = list(User.objects.filter(username__in=usernames))
    except Exception:
        return {"error": "Invalid user_ids", "status": 400}
    if len(users) != len(usernames):
        return {"error": "Some user_ids are invalid", "status": 400}

    group_call = GroupCall.objects.create(
        creator=creator,
        call_type=call_type,
        status=GroupCall.ACTIVE,
    )
    # Creator is first participant, joined
    GroupCallParticipant.objects.create(
        group_call=group_call,
        user=creator,
        status=GroupCallParticipant.JOINED,
        joined_at=timezone.now(),
    )
    for u in users:
        GroupCallParticipant.objects.create(
            group_call=group_call,
            user=u,
            status=GroupCallParticipant.INVITED,
        )

    channel_layer = get_channel_layer()
    if channel_layer:
        payload = {
            "type": "incoming_group_call",
            "call_id": group_call.id,
            "creator": creator.username,
            "call_type": group_call.call_type,
            "participant_usernames": usernames,
        }
        for username in usernames:
            try:
                async_to_sync(channel_layer.group_send)(
                    f"call_{username}",
                    {"type": "incoming_group_call", "payload": payload},
                )
            except Exception:
                pass
    logger.info(
        "Group call initiated: call_id=%s creator=%s invitees=%s",
        group_call.id, creator.username, usernames,
    )
    return {
        "success": True,
        "call_id": group_call.id,
        "creator": creator.username,
        "call_type": group_call.call_type,
        "participant_usernames": usernames,
        "status": 201,
    }


@csrf_exempt
@login_required
async def initiate_group_call(request: HttpRequest):
    """POST { "user_ids": ["user1","user2"], "call_type": "audio"|"video" }. Creates group call and notifies invitees."""
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    user_ids = data.get("user_ids")
    call_type = data.get("call_type", "audio")
    result = await sync_to_async(_initiate_group_call_sync)(request, user_ids, call_type)
    if "error" in result:
        return JsonResponse(
            {"success": False, "error": result["error"]},
            status=result.get("status", status.HTTP_400_BAD_REQUEST),
        )
    return JsonResponse(
        {
            "success": True,
            "call_id": result["call_id"],
            "creator": result["creator"],
            "call_type": result["call_type"],
            "participant_usernames": result["participant_usernames"],
        },
        status=status.HTTP_201_CREATED,
    )


def _join_group_call_sync(req, call_id):
    """Mark user as joined and broadcast participant_joined to group_call_{call_id}."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    try:
        group_call = GroupCall.objects.get(id=call_id)
    except GroupCall.DoesNotExist:
        return {"error": "Group call not found", "status": 404}
    if group_call.status != GroupCall.ACTIVE:
        return {"error": "Group call has ended", "status": 400}
    try:
        part = GroupCallParticipant.objects.get(group_call=group_call, user=req.user)
    except GroupCallParticipant.DoesNotExist:
        return {"error": "You are not a participant of this call", "status": 403}
    if part.status == GroupCallParticipant.JOINED:
        return {
            "success": True,
            "call_id": group_call.id,
            "creator": group_call.creator.username,
            "call_type": group_call.call_type,
            "participant_usernames": list(
                GroupCallParticipant.objects.filter(
                    group_call=group_call,
                    status=GroupCallParticipant.JOINED,
                ).values_list("user__username", flat=True),
            ),
        }
    part.status = GroupCallParticipant.JOINED
    part.joined_at = timezone.now()
    part.save(update_fields=["status", "joined_at"])

    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"group_call_{group_call.id}",
                {
                    "type": "participant_joined",
                    "payload": {
                        "type": "participant_joined",
                        "call_id": group_call.id,
                        "username": req.user.username,
                        "participant_usernames": list(
                            GroupCallParticipant.objects.filter(
                                group_call=group_call,
                                status=GroupCallParticipant.JOINED,
                            ).values_list("user__username", flat=True),
                        ),
                    },
                },
            )
        except Exception:
            pass
    logger.info("Group call join: call_id=%s user=%s", group_call.id, req.user.username)
    return {
        "success": True,
        "call_id": group_call.id,
        "creator": group_call.creator.username,
        "call_type": group_call.call_type,
        "participant_usernames": list(
            GroupCallParticipant.objects.filter(
                group_call=group_call,
                status=GroupCallParticipant.JOINED,
            ).values_list("user__username", flat=True),
        ),
    }


@csrf_exempt
@login_required
async def join_group_call(request: HttpRequest):
    """POST { "call_id": <id> }. Join the group call and notify others."""
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        call_id = data.get("call_id")
        if call_id is None:
            return JsonResponse({"success": False, "error": "call_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        call_id = int(call_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "call_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    result = await sync_to_async(_join_group_call_sync)(request, call_id)
    if "error" in result:
        return JsonResponse(
            {"success": False, "error": result["error"]},
            status=result.get("status", status.HTTP_400_BAD_REQUEST),
        )
    return JsonResponse(
        {
            "success": True,
            "call_id": result["call_id"],
            "creator": result["creator"],
            "call_type": result["call_type"],
            "participant_usernames": result["participant_usernames"],
        },
        status=status.HTTP_200_OK,
    )


def _leave_group_call_sync(req, call_id):
    """Mark user as left; if creator leaves, end the call for all."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    try:
        group_call = GroupCall.objects.get(id=call_id)
    except GroupCall.DoesNotExist:
        return {"error": "Group call not found", "status": 404}
    if group_call.status != GroupCall.ACTIVE:
        return {"error": "Group call has ended", "status": 400}
    try:
        part = GroupCallParticipant.objects.get(group_call=group_call, user=req.user)
    except GroupCallParticipant.DoesNotExist:
        return {"error": "You are not a participant of this call", "status": 403}
    if part.status == GroupCallParticipant.LEFT:
        return {"success": True, "call_id": group_call.id}

    part.status = GroupCallParticipant.LEFT
    part.save(update_fields=["status"])

    channel_layer = get_channel_layer()
    payload_left = {
        "type": "participant_left",
        "call_id": group_call.id,
        "username": req.user.username,
    }
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"group_call_{group_call.id}",
                {"type": "participant_left", "payload": payload_left},
            )
        except Exception:
            pass

    # If creator left, end the call for everyone
    if group_call.creator == req.user:
        group_call.status = GroupCall.ENDED
        group_call.save(update_fields=["status"])
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    f"group_call_{group_call.id}",
                    {
                        "type": "group_call_ended",
                        "payload": {
                            "type": "group_call_ended",
                            "call_id": group_call.id,
                            "reason": "creator_left",
                        },
                    },
                )
            except Exception:
                pass
        logger.info("Group call ended (creator left): call_id=%s", group_call.id)

    logger.info("Group call leave: call_id=%s user=%s", group_call.id, req.user.username)
    return {"success": True, "call_id": group_call.id}


@csrf_exempt
@login_required
async def leave_group_call(request: HttpRequest):
    """POST { "call_id": <id> }. Leave the group call; if creator leaves, call ends for all."""
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        call_id = data.get("call_id")
        if call_id is None:
            return JsonResponse({"success": False, "error": "call_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        call_id = int(call_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "call_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    result = await sync_to_async(_leave_group_call_sync)(request, call_id)
    if "error" in result:
        return JsonResponse(
            {"success": False, "error": result["error"]},
            status=result.get("status", status.HTTP_400_BAD_REQUEST),
        )
    return JsonResponse({"success": True, "call_id": result["call_id"]}, status=status.HTTP_200_OK)


def _end_group_call_sync(req, call_id):
    """Creator ends the group call for everyone."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    try:
        group_call = GroupCall.objects.get(id=call_id)
    except GroupCall.DoesNotExist:
        return {"error": "Group call not found", "status": 404}
    if group_call.creator != req.user:
        return {"error": "Only the creator can end the group call", "status": 403}
    if group_call.status != GroupCall.ENDED:
        group_call.status = GroupCall.ENDED
        group_call.save(update_fields=["status"])
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    f"group_call_{group_call.id}",
                    {
                        "type": "group_call_ended",
                        "payload": {
                            "type": "group_call_ended",
                            "call_id": group_call.id,
                            "reason": "ended_by_creator",
                        },
                    },
                )
            except Exception:
                pass
        logger.info("Group call ended by creator: call_id=%s", group_call.id)
    return {"success": True, "call_id": group_call.id}


@csrf_exempt
@login_required
async def end_group_call(request: HttpRequest):
    """POST { "call_id": <id> }. Creator only. Ends the group call for all participants."""
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        call_id = data.get("call_id")
        if call_id is None:
            return JsonResponse({"success": False, "error": "call_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        call_id = int(call_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "call_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    result = await sync_to_async(_end_group_call_sync)(request, call_id)
    if "error" in result:
        return JsonResponse(
            {"success": False, "error": result["error"]},
            status=result.get("status", status.HTTP_400_BAD_REQUEST),
        )
    return JsonResponse({"success": True, "call_id": result["call_id"]}, status=status.HTTP_200_OK)


def _get_active_group_calls_sync(user):
    """Return active group calls where user is creator or participant (invited or joined)."""
    q = Q(group_call__status=GroupCall.ACTIVE) & (
        Q(group_call__creator=user) | Q(user=user)
    )
    participants = (
        GroupCallParticipant.objects.filter(q)
        .select_related("group_call", "group_call__creator", "user")
        .order_by("-group_call__created_at")
    )
    seen = set()
    out = []
    for p in participants:
        gc = p.group_call
        if gc.id in seen:
            continue
        seen.add(gc.id)
        joined = list(
            GroupCallParticipant.objects.filter(
                group_call=gc,
                status=GroupCallParticipant.JOINED,
            ).values_list("user__username", flat=True),
        )
        invited = list(
            GroupCallParticipant.objects.filter(
                group_call=gc,
                status=GroupCallParticipant.INVITED,
            ).values_list("user__username", flat=True),
        )
        out.append({
            "call_id": gc.id,
            "creator": gc.creator.username,
            "call_type": gc.call_type,
            "status": gc.status,
            "created_at": gc.created_at.isoformat(),
            "participants_joined": joined,
            "participants_invited": invited,
        })
    return out


@login_required
async def get_active_group_calls(request: HttpRequest):
    """GET: List active group calls for the current user (invited or participant)."""
    if verifyGet(request):
        return verifyGet(request)
    result = await sync_to_async(_get_active_group_calls_sync)(request.user)
    return JsonResponse(result, safe=False)


def _get_callable_users_sync(user):
    """Return users with Profile, excluding self, for call UI. Includes is_busy flag."""
    profiles = Profile.objects.exclude(Employee_id=user).select_related("Employee_id", "Role")
    # Usernames that have any active call (pending or accepted)
    busy_usernames = set()
    for s, r in Call.objects.filter(status__in=[Call.PENDING, Call.ACCEPTED]).values_list(
        "sender__username", "receiver__username"
    ):
        busy_usernames.add(s)
        busy_usernames.add(r)
    return [
        {
            "username": p.Employee_id.username,
            "name": p.Name or p.Employee_id.username,
            "is_busy": p.Employee_id.username in busy_usernames,
        }
        for p in profiles
    ]


@login_required
async def get_callable_users(request: HttpRequest):
    if verifyGet(request):
        return verifyGet(request)
    result = await sync_to_async(_get_callable_users_sync)(request.user)
    return JsonResponse(result, safe=False)
# Create your views here.
