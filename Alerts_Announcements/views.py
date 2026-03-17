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

from .models import Alert, AlertType, Announcement, AnnouncementType
from .serializers import (
    AlertSerializer,
    AlertTypeSerializer,
    AnnouncementSerializer,
    AnnouncementTypeSerializer,
)


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
