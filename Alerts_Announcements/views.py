"""
Alerts & Announcements API views. Base path: {{baseurl}}/alertsapi/
- AlertTypeViewSet: GET /alert-types/ (list, retrieve). Read-only.
- AlertViewSet: CRUD /alerts/; perform_create sets alert_creator from request.user.
- AnnouncementTypeViewSet: GET /announcement-types/ (list, retrieve). Read-only.
- AnnouncementViewSet: CRUD /announcements/.
"""
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny

from ems.auth_utils import CsrfExemptSessionAuthentication

from .models import Alert, AlertType, Announcement, AnnouncementType, Attention
from .serializers import (
    AlertSerializer,
    AlertTypeSerializer,
    AnnouncementSerializer,
    AnnouncementTypeSerializer,
    AttentionSerializer,
)
from rest_framework.exceptions import PermissionDenied
from accounts.filters import _get_user_role_sync
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class AlertTypeViewSet(ReadOnlyModelViewSet):
    """List and retrieve alert types (e.g. System, Security, Info)."""
    queryset = AlertType.objects.all().order_by("type_name")
    serializer_class = AlertTypeSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]


class AlertViewSet(ModelViewSet):
    """CRUD for Alerts. GET (list, retrieve) is open to all; POST, PUT, PATCH, DELETE require auth."""
    queryset = (
        Alert.objects.all()
        .select_related("alert_type", "alert_creator", "status", "resolved_by")
        .order_by("-created_at")
    )
    serializer_class = AlertSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        # alert_creator set from logged-in user; closed_by and resolved_by come from request body.
        serializer.save(alert_creator=self.request.user)


class AnnouncementTypeViewSet(ReadOnlyModelViewSet):
    """List and retrieve announcement types."""
    queryset = AnnouncementType.objects.all().order_by("type_name")
    serializer_class = AnnouncementTypeSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]


class AnnouncementViewSet(ModelViewSet):
    """CRUD for Announcements."""
    queryset = (
        Announcement.objects.all()
        .select_related("created_by", "type", "product")
        .order_by("-created_at")
    )
    serializer_class = AnnouncementSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AttentionViewSet(ModelViewSet):
    """
    Attention section:
    - MD/Admin/HR can access.
    - MD/Admin see all; HR sees all (or can be restricted) depending on get_queryset below.
    - Non-elevated users see only their own.
    - Deletion/update rules:
      - MD/Admin: can update/delete any.
      - HR: can update/delete only items they created.
    """

    serializer_class = AttentionSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_role(self, user):
        # role_name: "MD", "Admin", "HR", ...
        try:
            if not user or not getattr(user, "is_authenticated", False):
                return None
            if getattr(user, "is_superuser", False):
                return "Admin"
            return _get_user_role_sync(user)
        except Exception:
            return None

    def get_queryset(self):
        role = self._get_role(self.request.user)
        qs = (
            Attention.objects.select_related("attention_creator", "target_employee")
            .order_by("-created_at")
        )

        # For updates, allow editing any Attention record.
        # This enables PATCH/PUT to update fields other than `status` for any authenticated user.
        # We keep GET/list permissions unchanged below.
        if self.request.method in ("PATCH", "PUT"):
            return qs

        # MD/Admin/HR can see all attentions.
        if role in ("MD", "HR", "Admin"):
            return qs

        # Everyone else: only what they created.
        return qs.filter(attention_creator=self.request.user)

    def perform_create(self, serializer):
        role = self._get_role(self.request.user)
        attention = serializer.save(attention_creator=self.request.user)

        # Notify receiver about newly created Attention.
        # Safety: notification failures must never break Attention creation.
        try:
            receiver = getattr(attention, "target_employee", None)
            if not receiver:
                return

            # Create DB notification (optional; depends on notification_type row).
            from notifications.models import Notification, notification_type
            nt = None
            try:
                nt = notification_type.objects.get(type_name="Attention_Created")
            except notification_type.DoesNotExist:
                nt = None

            message = f"New attention: {getattr(attention, 'attention_title', '')}".strip()
            message = (message or "")[:100]

            if nt is not None:
                Notification.objects.create(
                    from_user=self.request.user,
                    receipient=receiver,
                    message=message,
                    type_of_notification=nt,
                )

            # WebSocket push (best-effort).
            channel_layer = get_channel_layer()
            if not channel_layer:
                return

            from accounts.filters import _get_users_Name_sync
            from_name = _get_users_Name_sync(self.request.user) or getattr(self.request.user, "username", "")

            async_to_sync(channel_layer.group_send)(
                f"user_{receiver.username}",
                {
                    "type": "send_notification",
                    "category": "Attention",
                    "title": "Attention added",
                    "from": from_name,
                    "message": message,
                    "extra": {"attention_id": attention.id},
                },
            )
        except Exception:
            # Ignore all notification errors to avoid impacting core Attention API functionality.
            return

    def perform_update(self, serializer):
        obj = self.get_object()
        # Allow any authenticated user to update any field allowed by the serializer.
        serializer.save()

    def perform_destroy(self, instance):
        # attention_creator FK uses to_field="username" → attention_creator_id is username, not User.pk.
        # Compare with User instance (or username), never request.user.id.
        is_creator = instance.attention_creator == self.request.user
        role = (self._get_role(self.request.user) or "").upper()
        if not is_creator and role not in ("MD", "HR", "ADMIN"):
            raise PermissionDenied("You are not allowed to delete this attention.")
        instance.delete()
