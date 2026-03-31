"""
MD / Admin: send a meet request to one employee via existing Notification + WebSocket flow.
POST /notifications/md/meet/ — no new DB tables (uses notifications.Notification + types).
"""
import logging
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.filters import _get_user_role_sync, _get_users_Name_sync
from ems.RequiredImports import (
    Response,
    api_view,
    permission_classes,
    status,
    IsAuthenticated,
)
from ems.channel_groups import user_group_name
from ems.utils import gmt_to_ist_str

from .models import Notification, notification_type

logger = logging.getLogger(__name__)

User = get_user_model()

MEET_CATEGORY = "MeetRequest"


def _caller_may_initiate_meet(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    role = (_get_user_role_sync(user) or "").strip()
    return role in ("MD", "Admin")


def _resolve_target_user(data) -> User | None:
    if not data:
        return None
    uid = data.get("user_id")
    uname = data.get("username")
    if uid is not None and str(uid).strip() != "":
        try:
            pk = int(uid)
            return User.objects.filter(pk=pk).first()
        except (TypeError, ValueError):
            return None
    if uname is not None and str(uname).strip() != "":
        return User.objects.filter(username=str(uname).strip()).first()
    return None


def _send_meet_ws_and_db(from_user: User, recipient: User, message: str, title: str) -> dict:
    """
    Mirror QuaterlyReports.signals._send_notification_and_ws: DB row + group_send.
    Never deletes data. Failures are isolated (log + continue where safe).
    """
    msg_trim = (message[:97] + "...") if len(message) > 100 else message
    notification_obj = None
    nt = None
    try:
        nt, _ = notification_type.objects.get_or_create(
            type_name=MEET_CATEGORY,
            defaults={"type_name": MEET_CATEGORY},
        )
    except Exception as e:
        logger.warning("MeetRequest: notification_type get_or_create failed: %s", e)

    if nt:
        try:
            notification_obj = Notification.objects.create(
                from_user=from_user,
                receipient=recipient,
                message=msg_trim,
                type_of_notification=nt,
            )
        except Exception as e:
            logger.warning("MeetRequest: Notification create failed: %s", e)

    request_id = str(uuid.uuid4())
    if notification_obj:
        request_id = str(notification_obj.pk)

    time_str = None
    if notification_obj:
        time_str = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
    else:
        time_str = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")

    from_display = _get_users_Name_sync(from_user) or getattr(from_user, "username", "") or ""

    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                user_group_name(recipient.username),
                {
                    "type": "send_notification",
                    "category": MEET_CATEGORY,
                    "title": title,
                    "from": from_display,
                    "message": msg_trim,
                    "extra": {
                        "time": time_str,
                        "request_id": request_id,
                        "from_username": getattr(from_user, "username", None),
                        "to_username": getattr(recipient, "username", None),
                    },
                },
            )
        except Exception as e:
            logger.warning("MeetRequest: WebSocket group_send failed: %s", e)

    return {
        "request_id": request_id,
        "notification_id": notification_obj.pk if notification_obj else None,
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def md_meet_notify(request):
    """
    POST /notifications/md/meet/
    Body: { "username": "<employee_username>" } or { "user_id": <int> }
    Only MD, Admin, or superuser. Sends WS + optional Notification row (existing tables only).
    """
    if not _caller_may_initiate_meet(request.user):
        return Response(
            {"success": False, "message": "Only MD or Admin can send meet requests"},
            status=status.HTTP_403_FORBIDDEN,
        )

    data = request.data if isinstance(request.data, dict) else {}
    target = _resolve_target_user(data)
    if not target:
        return Response(
            {"success": False, "message": "Provide username or user_id for the employee"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if target.pk == request.user.pk:
        return Response(
            {"success": False, "message": "Cannot send a meet request to yourself"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    caller_name = _get_users_Name_sync(request.user) or request.user.username
    title = "Meet request"
    message = f"{caller_name} is requesting a meeting with you."

    try:
        meta = _send_meet_ws_and_db(request.user, target, message, title)
    except Exception as e:
        logger.exception("MeetRequest: unexpected error: %s", e)
        return Response(
            {"success": False, "message": "Could not send meet request"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "success": True,
            "message": "Meet notification sent",
            "request_id": meta["request_id"],
            "notification_id": meta["notification_id"],
            "target_username": target.username,
        },
        status=status.HTTP_201_CREATED,
    )
