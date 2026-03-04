from datetime import timedelta

from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.conf import settings

from ems.RequiredImports import (
    api_view,
    permission_classes,
    IsAuthenticated,
    AllowAny,
    Response,
    HttpRequest,
    status,
    date,
)
from .models import Notification, notification_type
from .Serializers import NotificationSerializer


# ==================== get_notifications ====================
# Fetch notifications for logged-in user.
# URL: {{baseurl}}/notifications/notifications/
# Method: GET
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    # print("get notifications not from cache")
    qs = Notification.objects.filter(receipient=request.user).select_related("type_of_notification", "from_user__accounts_profile", "receipient__accounts_profile").order_by("-created_at")
    data = NotificationSerializer(qs, many=True).data
    return Response(data)


# ==================== mark_as_read ====================
# Mark a notification as read.
# URL: {{baseurl}}/notifications/notifications/read/<pk>/
# Method: POST
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_as_read(request, pk):
    # print("mark as read not from cache")
    notification = Notification.objects.get(pk=pk)
    notification.is_read = True
    notification.save()
    return Response({"status": "read"})

# ==================== websocket_info ====================
# WebSocket connection info for testing.
# URL: {{baseurl}}/notifications/ws-info/
# Method: GET
@api_view(["GET"])
@permission_classes([AllowAny])
def websocket_info(request):
    """Returns WebSocket URLs and usage for testing."""
    return Response({
        "websockets": {
            "notifications": {
                "url": "ws://HOST/ws/notifications/",
                "description": "User notifications stream. Requires auth. Sends: task assigned, group message, private message, group created, slot booked, meeting scheduled.",
            },
        },
        "triggers": [
            "Message posted (group/private)",
            "New task assigned to user",
            "User added to group",
            "Slot booked with user as member",
            "Meeting scheduled by MD with user",
        ],
    })
    
# ==================== get_notification_types ====================
# Fetch all notification types from the database.
# URL: {{baseurl}}/notifications/types/
# Method: GET
@api_view(["GET"])
@permission_classes([AllowAny])
def get_notification_types(request):
    """Returns list of notification types. Uses @api_view so DRF sets .accepted_renderer on Response."""
    try:
        types = list(notification_type.objects.all().values())
        return Response(types)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== cron: delete old seen notifications ====================
# Delete all seen (is_read=True) notifications created more than 1 day ago.
# Intended for cron; permissionless (AllowAny).
# URL: {{baseurl}}/notifications/cron/delete-seen-older-than-day/
# Method: GET
def _cron_key_valid(request):
    """Return True if request has valid X-CRON-KEY header (env: X_CRON_KEY)."""
    key = (request.META.get("HTTP_X_CRON_KEY") or "").strip()
    expected = getattr(settings, "X_CRON_KEY", "") or ""
    return bool(expected) and constant_time_compare(key, expected)


@api_view(["GET"])
@permission_classes([AllowAny])
def cron_delete_seen_older_than_day(request):
    """Delete seen notifications older than 1 day. Returns count deleted. Requires X-CRON-KEY header."""
    if not _cron_key_valid(request):
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    cutoff = timezone.now() - timedelta(days=1)
    qs = Notification.objects.filter(is_read=True, created_at__lt=cutoff)
    count, _ = qs.delete()
    return Response({"deleted": count})


# ==================== cron: delete old unseen notifications ====================
# Delete all unseen (is_read=False) notifications created more than 1 week ago.
# Intended for cron; permissionless (AllowAny).
# URL: {{baseurl}}/notifications/cron/delete-unseen-older-than-week/
# Method: GET
@api_view(["GET"])
@permission_classes([AllowAny])
def cron_delete_unseen_older_than_week(request):
    """Delete unseen notifications older than 7 days. Returns count deleted. Requires X-CRON-KEY header."""
    if not _cron_key_valid(request):
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    cutoff = timezone.now() - timedelta(days=7)
    qs = Notification.objects.filter(is_read=False, created_at__lt=cutoff)
    count, _ = qs.delete()
    return Response({"deleted": count})
