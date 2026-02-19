from asgiref.sync import sync_to_async
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpRequest
from rest_framework import status
from .models import Notification,notification_type
from .Serializers import NotificationSerializer


# ==================== get_notifications ====================
# Fetch notifications for logged-in user.
# URL: {{baseurl}}/notifications/notifications/
# Method: GET
@api_view(["GET"])
@permission_classes([IsAuthenticated])
async def get_notifications(request):
    def _fetch(user):
        qs = Notification.objects.filter(receipient=user).select_related("type_of_notification", "from_user").order_by("-created_at")
        return NotificationSerializer(qs, many=True).data

    data = await sync_to_async(_fetch)(request.user)
    return Response(data)


# ==================== mark_as_read ====================
# Mark a notification as read.
# URL: {{baseurl}}/notifications/notifications/read/<pk>/
# Method: POST
@api_view(["POST"])
@permission_classes([IsAuthenticated])
async def mark_as_read(request, pk):
    def _mark(user):
        notification = Notification.objects.get(pk=pk, receipient=user)
        notification.is_read = True
        notification.save()

    await sync_to_async(_mark)(request.user)
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
            "chat": {
                "url": "ws://HOST/ws/chat/<chat_id>/",
                "description": "Real-time chat. chat_id: group (G12345) or individual (C12345678). Requires auth.",
            },
            "notifications": {
                "url": "ws://HOST/ws/notifications/",
                "description": "User notifications stream. Requires auth. Sends: message posted, task assigned, group created, slot booked, meeting scheduled.",
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
