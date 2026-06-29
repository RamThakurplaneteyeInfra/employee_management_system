from datetime import datetime

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ems.auth_utils import CsrfExemptSessionAuthentication

from .models import AnnouncementPost
from .permissions import AnnouncementPostPermission
from .serializers import AnnouncementPostSerializer


def _parse_list_date(request):
    """List date from ?date=YYYY-MM-DD, else today in Asia/Kolkata."""
    raw = request.query_params.get("date")
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            pass
    return timezone.localdate()


def _parse_pagination_params(request):
    """
    Optional limit/offset pagination (backward-compatible).
    Enabled when either query param is present.
    """
    raw_limit = request.query_params.get("limit")
    raw_offset = request.query_params.get("offset")
    paginate_enabled = raw_limit is not None or raw_offset is not None

    if not paginate_enabled:
        return 0, 0, False

    default_limit = 30
    max_limit = 100

    try:
        limit = int(raw_limit) if raw_limit is not None else default_limit
    except (TypeError, ValueError):
        limit = default_limit

    try:
        offset = int(raw_offset) if raw_offset is not None else 0
    except (TypeError, ValueError):
        offset = 0

    if limit < 1:
        limit = default_limit
    if limit > max_limit:
        limit = max_limit
    if offset < 0:
        offset = 0

    return limit, offset, True


def _paginated_response(items, total, limit, offset):
    next_offset = offset + limit if (offset + limit) < total else None
    prev_offset = offset - limit if offset - limit >= 0 else None
    return {
        "items": items,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "next_offset": next_offset,
            "prev_offset": prev_offset,
            "has_next": next_offset is not None,
            "has_prev": offset > 0,
        },
    }


class AnnouncementPostViewSet(ModelViewSet):
    queryset = AnnouncementPost.objects.all().select_related("created_by").order_by("-created_at")
    serializer_class = AnnouncementPostSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated, AnnouncementPostPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            qs = qs.filter(announcement_date=_parse_list_date(self.request))
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        limit, offset, paginate = _parse_pagination_params(request)

        if paginate:
            total = queryset.count()
            page = queryset[offset : offset + limit]
            data = self.get_serializer(page, many=True).data
            return Response(_paginated_response(data, total, limit, offset))

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
