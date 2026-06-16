from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ems.auth_utils import CsrfExemptSessionAuthentication

from accounts.leave_views import _get_user_role_sync, _user_can_view_on_leave

from .certification_scoring import (
    build_certification_points,
    parse_leave_points_period,
    resolve_leave_points_user,
)
from .models import EmployeeCertificate
from .permissions import CertificatePermission, is_hr
from .serializers import (
    EmployeeCertificateCreateSerializer,
    EmployeeCertificateReadSerializer,
    EmployeeCertificateUpdateSerializer,
    _resolve_owner_user,
)
from .grouped import grouped_list_from_certificates, grouped_single_for_user
from .services import BATCH_MAX_FILES, create_certificates_batch, parse_batch_items


def _base_queryset():
    return EmployeeCertificate.objects.select_related(
        "employee__accounts_profile",
        "uploaded_by__accounts_profile",
    )


def _visible_queryset(user):
    qs = _base_queryset().filter(is_active=True)
    if is_hr(user):
        return qs
    return qs.filter(employee=user)


def _apply_list_filters(qs, request, user):
    employee_id = (request.query_params.get("employee") or request.query_params.get("employeeId") or "").strip()
    if employee_id:
        if not is_hr(user):
            if employee_id != user.username:
                return qs.none()
        qs = qs.filter(employee__username=employee_id)
    include_inactive = (request.query_params.get("include_inactive") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    if include_inactive and is_hr(user):
        qs = _base_queryset()
        if employee_id:
            qs = qs.filter(employee__username=employee_id)
    return qs


class EmployeeCertificateViewSet(viewsets.ModelViewSet):
    """
    Employee certificates (separate app; does not modify accounts/recruitment).

    - Employee/creator: full CRUD on own active certificates.
    - HR: full CRUD on all certificates; filter ?employee=EMP001
    - DELETE: soft-deactivate only (is_active=False); DB row and S3 file kept.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [CertificatePermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return _apply_list_filters(_visible_queryset(self.request.user), self.request, self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return EmployeeCertificateCreateSerializer
        if self.action in ("update", "partial_update"):
            return EmployeeCertificateUpdateSerializer
        return EmployeeCertificateReadSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().order_by("-created_at", "-id")
        data = EmployeeCertificateReadSerializer(qs, many=True, context={"request": request}).data
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            EmployeeCertificateReadSerializer(instance, context={"request": request}).data
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            EmployeeCertificateReadSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if not instance.is_active:
            return Response(
                {"detail": "Certificate is inactive. HR may restore via admin or re-upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            EmployeeCertificateReadSerializer(instance, context={"request": request}).data
        )

    def destroy(self, request, *args, **kwargs):
        """Soft-delete only: never removes DB rows or S3 objects."""
        instance = self.get_object()
        if not instance.is_active:
            return Response(status=status.HTTP_204_NO_CONTENT)
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get", "post"],
        url_path="batch",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_batch(self, request):
        """
        Upload multiple certificates in one request (multipart/form-data).

        Repeat per file (same order):
          - file (required)
          - title (optional; one value applies to all, or one per file)
          - description (optional; same rules as title)
        Optional: employeeId (HR only, applies to entire batch)
        """
        if request.method == "GET":
            return Response(
                {
                    "detail": "Submit with POST using multipart/form-data.",
                    "method": "POST",
                    "content_type": "multipart/form-data",
                    "fields": {
                        "file": "repeat once per certificate (required)",
                        "title": "optional; 0, 1, or same count as file",
                        "description": "optional; 0, 1, or same count as file",
                        "employeeId": "HR only — owner for all files in batch",
                    },
                    "max_files_per_request": BATCH_MAX_FILES,
                    "response_shape": {
                        "id": "employee username",
                        "name": "employee full name",
                        "created": "number of certificates uploaded",
                        "certificate": [{"id": 1, "title": "", "desc": "", "link": "presigned url"}],
                    },
                },
                status=status.HTTP_200_OK,
            )

        try:
            employee_id, items = parse_batch_items(request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = _resolve_owner_user(employee_id or None, request)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        try:
            created = create_certificates_batch(owner, request.user, items)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if created:
            ids = [c.pk for c in created]
            created = list(_base_queryset().filter(pk__in=ids).order_by("-created_at", "-id"))

        grouped = grouped_single_for_user(owner, created)
        grouped["created"] = len(grouped["certificate"])
        return Response(grouped, status=status.HTTP_201_CREATED)

    def _grouped_queryset(self, request):
        return _apply_list_filters(
            _visible_queryset(request.user), request, request.user
        ).order_by("employee__username", "-created_at", "-id")

    @action(detail=False, methods=["get"], url_path="me")
    def my_grouped(self, request):
        """
        Logged-in employee: { id, name, certificate: [{ id, title, desc, link }, ...] }.
        """
        qs = (
            _base_queryset()
            .filter(is_active=True, employee=request.user)
            .order_by("-created_at", "-id")
        )
        return Response(grouped_single_for_user(request.user, qs))

    @action(detail=False, methods=["get"], url_path="grouped")
    def list_grouped(self, request):
        """
        Grouped by employee: { id, name, certificate: [...] }.

        - No query param + HR: all employees with certificates.
        - ?id=30013 or ?employee=30013: one employee (HR any; others only own id).
        - No query param + employee: same as /me/.
        """
        employee_id = (
            request.query_params.get("id")
            or request.query_params.get("employee")
            or request.query_params.get("employeeId")
            or ""
        ).strip()

        if employee_id:
            if not is_hr(request.user) and employee_id != request.user.username:
                return Response(
                    {"detail": "You can only view your own certificates."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            user = get_object_or_404(User, username=employee_id)
            qs = (
                _apply_list_filters(_base_queryset(), request, request.user)
                .filter(employee=user, is_active=True)
                .order_by("-created_at", "-id")
            )
            return Response(grouped_single_for_user(user, qs))

        if is_hr(request.user):
            qs = self._grouped_queryset(request)
            return Response(grouped_list_from_certificates(qs))

        return Response(
            grouped_single_for_user(
                request.user,
                _base_queryset()
                .filter(is_active=True, employee=request.user)
                .order_by("-created_at", "-id"),
            )
        )

    @action(detail=False, methods=["get"], url_path="certification-points")
    def certification_points(self, request):
        """
        Certification performance points for an employee.
        GET /api/certificates/certification-points/?year=2026&month=6
        Main +5 if any cert in month; +5 bonus per additional cert in same month.
        Optional: ?employee=<username> (HR / Admin / MD / TeamLead for team members)
        """
        year, month, quarter, period_err = parse_leave_points_period(request)
        if period_err is not None:
            return Response(period_err, status=status.HTTP_400_BAD_REQUEST)

        target_user, user_err = resolve_leave_points_user(
            request, _user_can_view_on_leave, _get_user_role_sync
        )
        if user_err is not None:
            err_status = (
                status.HTTP_404_NOT_FOUND
                if "not found" in user_err["detail"].lower()
                else status.HTTP_403_FORBIDDEN
            )
            return Response(user_err, status=err_status)

        data = build_certification_points(target_user, year, month=month, quarter=quarter)
        return Response(data)
