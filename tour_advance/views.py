from django.db.models import Prefetch, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile
from ems.auth_utils import CsrfExemptSessionAuthentication
from ems.s3_utils import delete_file_from_files

from .models import TourAdvanceMember, TourAdvanceRequest
from .permissions import IsAdminOrMD, is_admin_or_md
from .s3_helpers import upload_response_payload, upload_tour_advance_file, validate_upload_file
from .serializers import (
    EmployeeLookupSerializer,
    TourAdvanceReadSerializer,
    TourAdvanceWriteSerializer,
)

_LIST_ORDER = ("-created_at", "-id")


def _base_queryset():
    """Single optimized queryset with all relations prefetched for list/detail."""
    return TourAdvanceRequest.objects.select_related(
        "primary_employee__accounts_profile",
        "created_by__accounts_profile",
    ).prefetch_related(
        Prefetch(
            "member_links",
            queryset=TourAdvanceMember.objects.select_related(
                "member__accounts_profile"
            ),
        ),
        "attachments",
    )


def _visibility_queryset(user, scope):
    qs = _base_queryset()
    if scope == "all":
        return qs
    return qs.filter(Q(created_by=user) | Q(members=user)).distinct()


def _apply_list_filters(qs, request):
    status_val = (request.query_params.get("status") or "").strip()
    if status_val:
        qs = qs.filter(status=status_val)
    employee_id = (request.query_params.get("employeeId") or "").strip()
    if employee_id:
        qs = qs.filter(primary_employee_id=employee_id)
    date_from = (request.query_params.get("from") or "").strip()
    if date_from:
        qs = qs.filter(start_date__gte=date_from)
    date_to = (request.query_params.get("to") or "").strip()
    if date_to:
        qs = qs.filter(start_date__lte=date_to)
    return qs


class TourAdvanceRequestViewSet(viewsets.ModelViewSet):
    """
    Tour advance requests — separate from eventsapi/tours/ (team tour events).

    List endpoints:
      GET /api/tour-advance/requests/all/  — Admin/MD: every request
      GET /api/tour-advance/requests/my/     — Employee: creator or assigned member
      GET /api/tour-advance/requests/        — Alias: all for Admin/MD, my for others
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        scope = "all" if is_admin_or_md(user) else "my"
        return _visibility_queryset(user, scope).order_by(*_LIST_ORDER)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TourAdvanceWriteSerializer
        return TourAdvanceReadSerializer

    def _list_response(self, request, scope):
        qs = _apply_list_filters(_visibility_queryset(request.user, scope), request)
        qs = qs.order_by(*_LIST_ORDER)
        data = TourAdvanceReadSerializer(qs, many=True, context={"request": request}).data
        return Response(data)

    def list(self, request, *args, **kwargs):
        scope = "all" if is_admin_or_md(request.user) else "my"
        return self._list_response(request, scope)

    @action(
        detail=False,
        methods=["get"],
        url_path="all",
        permission_classes=[IsAuthenticated, IsAdminOrMD],
    )
    def list_all(self, request):
        """Admin/MD: all tour advance requests."""
        return self._list_response(request, "all")

    @action(detail=False, methods=["get"], url_path="my")
    def list_my(self, request):
        """Any user: requests they created or are assigned to."""
        return self._list_response(request, "my")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TourAdvanceReadSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TourAdvanceReadSerializer(instance, context={"request": request}).data
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if is_admin_or_md(user):
            pass
        elif instance.created_by_id == user.id:
            if instance.status != TourAdvanceRequest.Status.PENDING:
                return Response(
                    {"detail": "Only pending requests can be deleted."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response(
                {"detail": "You do not have permission to delete this request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        s3_keys = list(instance.attachments.values_list("s3_key", flat=True))
        instance.delete()
        for key in s3_keys:
            delete_file_from_files(key)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["post"],
        url_path="uploadFile",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_file(self, request):
        """POST multipart field `file` → S3 key + metadata (client sends fileUrl on create)."""
        file_obj = request.FILES.get("file")
        err = validate_upload_file(file_obj)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        try:
            s3_key = upload_tour_advance_file(file_obj)
        except Exception as exc:
            return Response(
                {"error": f"Upload failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            upload_response_payload(file_obj, s3_key),
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="employees",
        permission_classes=[IsAuthenticated, IsAdminOrMD],
    )
    def employees(self, request):
        """Admin/MD: search employees by id or name for dropdown."""
        q = (request.query_params.get("q") or "").strip()
        qs = Profile.objects.select_related("Department").all()
        if q:
            qs = qs.filter(
                Q(Employee_id_id__icontains=q) | Q(Name__icontains=q)
            )
        qs = qs.order_by("Name")[:50]
        return Response(EmployeeLookupSerializer(qs, many=True).data)
