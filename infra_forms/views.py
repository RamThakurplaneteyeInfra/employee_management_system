from django.db import transaction
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .excel_bulk_import import parse_excel_workbook
from .permissions import CanAccessInfraProjectForms
from .models import (
    BoqStructureEntry,
    InfraProjectForm,
    LidarStructureEntry,
    ProjectCatalog,
    SarStructureEntry,
)
from .serializers import (
    BoqStructureEntrySerializer,
    InfraProjectFormSerializer,
    LidarStructureEntrySerializer,
    ProjectCatalogSerializer,
    SarStructureEntrySerializer,
)


class BaseStructureEntryViewSet(viewsets.ModelViewSet):
    """One ViewSet per module table; `queryset`, `serializer_class`, and `module_key` are set on subclass."""

    serializer_class = None
    queryset = None
    module_key = None

    def get_queryset(self):
        queryset = self.queryset.select_related("route_group")
        project_name = (self.request.query_params.get("project_name") or "").strip()
        if project_name:
            queryset = queryset.filter(project_name__iexact=project_name)
        route_group = self.request.query_params.get("route_group")
        if route_group:
            queryset = queryset.filter(route_group_id=route_group)
        return queryset

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
        """Upload .xlsx: row 1 = headers, row 2+ = data → creates rows in this module's table (atomic)."""
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

        serializer_class = self.serializer_class
        row_errors: list[dict] = []
        pending_serializers: list = []
        for row in rows:
            excel_row = row.pop("_excel_row", None)
            if selected_project_name:
                # Project selected at UI level overrides/sets project for all imported rows.
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

    @action(detail=False, methods=["delete"], url_path="delete-all")
    def delete_all(self, request):
        """Delete every row in this module's table (ignores ?route_group= query filters)."""
        model = self.queryset.model
        qs = model.objects.all()
        n = qs.count()
        if n == 0:
            return Response({"deleted": 0, "detail": "No entries to delete."}, status=status.HTTP_200_OK)
        qs.delete()
        return Response({"deleted": n, "detail": "All entries deleted."}, status=status.HTTP_200_OK)


class BoqStructureEntryViewSet(BaseStructureEntryViewSet):
    serializer_class = BoqStructureEntrySerializer
    queryset = BoqStructureEntry.objects.all()
    module_key = "boq"


class LidarStructureEntryViewSet(BaseStructureEntryViewSet):
    serializer_class = LidarStructureEntrySerializer
    queryset = LidarStructureEntry.objects.all()
    module_key = "lidar"


class SarStructureEntryViewSet(BaseStructureEntryViewSet):
    serializer_class = SarStructureEntrySerializer
    queryset = SarStructureEntry.objects.all()
    module_key = "sar"


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
