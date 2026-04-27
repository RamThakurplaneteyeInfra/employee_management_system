from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from ems.auth_utils import CsrfExemptSessionAuthentication

from .models import AnnouncementPost
from .serializers import AnnouncementPostSerializer
from .permissions import AnnouncementPostPermission


class AnnouncementPostViewSet(ModelViewSet):
    queryset = AnnouncementPost.objects.all().select_related("created_by").order_by("-created_at")
    serializer_class = AnnouncementPostSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated, AnnouncementPostPermission]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

