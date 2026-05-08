from django.db.models import Count, Exists, OuterRef, Q
from django.db import transaction
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .excel_bulk_import import parse_excel_workbook
from .permissions import CanAccessInfraProjectForms
from .models import (
    InfraProjectForm,
    InfraServiceType,
    ProjectCatalog,
    StructureEntry,
    StructureEntryServiceState,
)
from .serializers import (
    BoqStructureEntrySerializer,
    InfraProjectFormSerializer,
    InfraServiceTypeSerializer,
    LidarStructureEntrySerializer,
    ProjectCatalogSerializer,
    SarStructureEntrySerializer,
    UnifiedStructureEntrySerializer,
)
from .service_state_sync import delete_service_state_for_code


_ALL_MODULES = ("boq", "lidar", "sar")

_MODULE_BULK_SERIALIZER = {
    "boq": BoqStructureEntrySerializer,
    "lidar": LidarStructureEntrySerializer,
    "sar": SarStructureEntrySerializer,
}


def _bulk_structure_excel_upload_response(request, serializer_class):
    """
    Shared Excel bulk import: parse workbook, validate every row with serializer_class,
    then save all in one transaction (all-or-nothing on validation errors).
    """
    upload = request.FILES.get("file")
    selected_project_name = (request.data.get("project_name") or "").strip()
    if not upload:
        return Response({"detail": "Missing file field `file`."}, status=status.HTTP_400_BAD_REQUEST)
    name = (upload.name or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        return Response(
            {"detail": "Please upload an .xlsx (or .xlsm) file. Legacy .xls is not supported."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    raw = upload.read()
    rows, parse_err = parse_excel_workbook(raw)
    if parse_err:
        return Response({"detail": parse_err}, status=status.HTTP_400_BAD_REQUEST)

    row_errors: list[dict] = []
    pending_serializers: list = []
    for row in rows:
        excel_row = row.pop("_excel_row", None)
        if selected_project_name:
            row["project_name"] = selected_project_name
        ser = serializer_class(data=row)
        if not ser.is_valid():
            row_errors.append({"excel_row": excel_row, "errors": ser.errors})
        else:
            pending_serializers.append(ser)

    if row_errors:
        return Response(
            {
                "detail": "Fix the sheet and re-upload; no rows were saved.",
                "row_errors": row_errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        for ser in pending_serializers:
            ser.save()

    return Response(
        {"created": len(pending_serializers), "detail": "All rows imported successfully."},
        status=status.HTTP_201_CREATED,
    )


class BaseStructureEntryViewSet(viewsets.ModelViewSet):
    """
    All three module endpoints (BOQ/LiDAR/SAR) operate on the unified
    `StructureEntry` table, but each instance filters/writes only the
    columns owned by its module (controlled via `module_key`).

    Cross-module data is never destroyed: deleting an entry from one module
    only clears that module's status/remark and turns off its `has_*` flag;
    the underlying row is removed only when no module owns it anymore.
    """

    serializer_class = None
    queryset = StructureEntry.objects.all()
    module_key = None

    def _has_field(self) -> str:
        return f"has_{self.module_key}"

    def _status_field(self) -> str:
        return f"{self.module_key}_status"

    def _remark_field(self) -> str:
        return f"{self.module_key}_remark"

    def get_queryset(self):
        queryset = StructureEntry.objects.select_related("route_group").prefetch_related(
            "service_states__service_type"
        ).filter(
            **{self._has_field(): True}
        )
        project_name = (self.request.query_params.get("project_name") or "").strip()
        if project_name:
            queryset = queryset.filter(project_name__iexact=project_name)
        route_group = self.request.query_params.get("route_group")
        if route_group:
            queryset = queryset.filter(route_group_id=route_group)
        return queryset

    def perform_destroy(self, instance):
        """
        Smart delete: clear only this module's data on the row.
        If no module owns the row anymore, delete the row entirely.
        """
        with transaction.atomic():
            setattr(instance, self._has_field(), False)
            setattr(instance, self._status_field(), "")
            setattr(instance, self._remark_field(), "")
            delete_service_state_for_code(instance, self.module_key)
            instance.save(
                update_fields=[
                    self._has_field(),
                    self._status_field(),
                    self._remark_field(),
                    "updated_at",
                ]
            )
            still_owned_legacy = any(getattr(instance, f"has_{m}") for m in _ALL_MODULES)
            still_has_services = StructureEntryServiceState.objects.filter(
                structure_entry_id=instance.pk
            ).exists()
            if not still_owned_legacy and not still_has_services:
                instance.delete()

    @action(detail=False, methods=["get"], url_path="route-corridors")
    def route_corridors(self, request):
        qs = (
            self.get_queryset()
            .exclude(route_corridor="")
            .values_list("route_corridor", flat=True)
            .distinct()
            .order_by("route_corridor")
        )
        return Response(list(qs))

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload-excel",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def bulk_upload_excel(self, request):
        """Upload .xlsx: row 1 = headers, row 2+ = data → creates rows owned by this module (atomic)."""
        return _bulk_structure_excel_upload_response(request, self.serializer_class)

    @action(detail=False, methods=["delete"], url_path="delete-all")
    def delete_all(self, request):
        """
        Clear this module's ownership on every row it currently owns.
        Other modules' data on shared rows is preserved.
        Rows that become unowned by any module are deleted.
        """
        has_field = self._has_field()
        status_field = self._status_field()
        remark_field = self._remark_field()

        with transaction.atomic():
            owned_qs = StructureEntry.objects.filter(**{has_field: True})
            entry_ids = list(owned_qs.values_list("pk", flat=True))
            n = len(entry_ids)
            if n == 0:
                return Response(
                    {"deleted": 0, "detail": "No entries to delete."},
                    status=status.HTTP_200_OK,
                )
            owned_qs.update(
                **{has_field: False, status_field: "", remark_field: ""}
            )
            StructureEntryServiceState.objects.filter(
                structure_entry_id__in=entry_ids,
                service_type__code=self.module_key,
            ).delete()
            unowned_qs = (
                StructureEntry.objects.filter(
                    has_boq=False, has_lidar=False, has_sar=False
                )
                .annotate(_sc=Count("service_states"))
                .filter(_sc=0)
            )
            unowned_qs.delete()

        return Response(
            {"deleted": n, "detail": "All entries deleted."},
            status=status.HTTP_200_OK,
        )


class BoqStructureEntryViewSet(BaseStructureEntryViewSet):
    serializer_class = BoqStructureEntrySerializer
    module_key = "boq"


class LidarStructureEntryViewSet(BaseStructureEntryViewSet):
    serializer_class = LidarStructureEntrySerializer
    module_key = "lidar"


class SarStructureEntryViewSet(BaseStructureEntryViewSet):
    serializer_class = SarStructureEntrySerializer
    module_key = "sar"


class UnifiedStructureEntryViewSet(viewsets.ModelViewSet):
    """
    Single endpoint: shared row fields + inspection_status[] and remark[]
    (length 3, order [BOQ, LiDAR, SAR]). Legacy module URLs are unchanged.

    Responses also include ``services``: ``[{code, label, inspection_status, remark}, …]``.
    PATCH with ``services`` merges rows by ``code`` (see serializer docstring).
    """

    lookup_value_regex = "[0-9]+"
    serializer_class = UnifiedStructureEntrySerializer
    queryset = (
        StructureEntry.objects.select_related("route_group")
        .prefetch_related("service_states__service_type")
        .filter(
            Q(has_boq=True)
            | Q(has_lidar=True)
            | Q(has_sar=True)
            | Exists(
                StructureEntryServiceState.objects.filter(
                    structure_entry_id=OuterRef("pk"),
                )
            ),
        )
    )

    def get_queryset(self):
        qs = super().get_queryset()
        project_name = (self.request.query_params.get("project_name") or "").strip()
        if project_name:
            qs = qs.filter(project_name__iexact=project_name)
        route_group = self.request.query_params.get("route_group")
        if route_group:
            qs = qs.filter(route_group_id=route_group)
        return qs

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().partial_update(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload-excel",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def bulk_upload_excel(self, request):
        """
        Same Excel pipeline as module bulk-upload endpoints; pick ownership via ``module``.

        Multipart form fields:
        - file: required (.xlsx / .xlsm)
        - project_name: optional (applied to every row)
        - module: optional, one of boq | lidar | sar (default: boq). Determines which module
          owns imported rows (same serializers as /boq-entries/, /lidar-entries/, /sar-entries/).
        """
        raw_module = (
            (request.data.get("module") or request.query_params.get("module") or "boq")
            .strip()
            .lower()
        )
        serializer_class = _MODULE_BULK_SERIALIZER.get(raw_module)
        if not serializer_class:
            return Response(
                {
                    "detail": (
                        f"Invalid module {raw_module!r}. "
                        "Use one of: boq, lidar, sar (form field or query param `module`)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = _bulk_structure_excel_upload_response(request, serializer_class)
        if response.status_code == status.HTTP_201_CREATED:
            data = dict(response.data)
            data["module"] = raw_module
            return Response(data, status=response.status_code)
        return response


class InfraServiceTypeViewSet(viewsets.ModelViewSet):
    """
    Service types for structure-entry dropdowns.

    - GET list: active types only, unless ``?include_inactive=true``.
    - GET retrieve: any type by id (including inactive).
    - POST / PATCH / PUT / DELETE: authenticated users only.
    """

    serializer_class = InfraServiceTypeSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = InfraServiceType.objects.all().order_by("sort_order", "code")
        if self.action == "list":
            inc = self.request.query_params.get("include_inactive", "").lower()
            if inc not in ("1", "true", "yes"):
                qs = qs.filter(active=True)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]


class ProjectCatalogViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectCatalogSerializer
    queryset = ProjectCatalog.objects.all()
    http_method_names = ["get", "post", "head", "options", "delete"]


class InfraProjectFormViewSet(viewsets.ModelViewSet):
    """
    Separate endpoint for the project-selected numeric form (header + Entry[]).
    Uses atomic writes so header+entries are never partially saved.
    """

    permission_classes = [IsAuthenticated, CanAccessInfraProjectForms]
    serializer_class = InfraProjectFormSerializer
    queryset = InfraProjectForm.objects.prefetch_related("entries").select_related("project")

    def get_queryset(self):
        qs = super().get_queryset()
        projectname = (self.request.query_params.get("projectname") or "").strip()
        if projectname:
            qs = qs.filter(projectname__iexact=projectname)
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        dt = (self.request.query_params.get("date") or "").strip()
        if dt:
            qs = qs.filter(date=dt)
        return qs

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="by-project")
    def by_project(self, request):
        """
        Convenience read for UI: select project -> fetch latest matching form.
        Query params (any combination):
        - projectname=<text>
        - project=<id>
        - date=YYYY-MM-DD
        Returns latest by updated_at.
        """
        qs = self.get_queryset().order_by("-updated_at", "-created_at")
        obj = qs.first()
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ser = self.get_serializer(obj)
        return Response(ser.data, status=status.HTTP_200_OK)
