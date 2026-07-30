from django.db import transaction
from django.db.models import Prefetch, Q

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeadlineProject, DeadlineProjectPhase
from .permissions import (
    can_edit_project,
    can_md_approve_checklist,
    is_global_privileged_deadline_user,
    resolve_deadline_employee_id,
)
from accounts.leave_views import _get_user_role_sync, _user_can_view_on_leave
from .checklist_md_approval import (
    apply_md_approval_to_item,
    count_md_approval_checklists,
    index_checklist_md_by_id,
    merge_preserved_md_fields,
)
from .checklist_scoring import (
    build_checklist_points,
    parse_leave_points_period,
    resolve_leave_points_user,
)
from .serializers import (
    ChecklistMdApprovalInputSerializer,
    ProjectInputSerializer,
    ProjectOutputSerializer,
)


# ---------------------------------------------------------------------------
# Base class — intercepts all exceptions so we NEVER return 403
# ---------------------------------------------------------------------------

class No403APIView(APIView):
    def handle_exception(self, exc):
        if isinstance(exc, NotAuthenticated):
            return Response(
                {"success": False, "message": "Login required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if isinstance(exc, PermissionDenied):
            return Response(
                {"success": False, "message": "You are not authorized to perform this action"},
                status=status.HTTP_200_OK,
            )
        if isinstance(exc, NotFound):
            return Response(
                {"success": False, "message": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if isinstance(exc, (DRFValidationError, ParseError)):
            detail = getattr(exc, "detail", None)
            body = {"success": False, "message": "Invalid payload"}
            if detail:
                body["errors"] = detail
            return Response(body, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(exc, APIException) and getattr(exc, "status_code", None) == 403:
            return Response(
                {"success": False, "message": "You are not authorized to perform this action"},
                status=status.HTTP_200_OK,
            )
        return super().handle_exception(exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_queryset():
    """Optimized queryset shared by list + detail."""
    active_phases = DeadlineProjectPhase.objects.filter(
        archived=False,
    ).order_by("sort_order", "created_at")

    return (
        DeadlineProject.objects
        .filter(archived=False)
        .select_related("created_by")
        .prefetch_related(
            Prefetch("phases", queryset=active_phases, to_attr="active_phases"),
        )
    )


def _serialize_project(project, *, request=None):
    """Render a single project through the output serializer."""
    if request is not None:
        return ProjectOutputSerializer(project, context={"request": request}).data
    return ProjectOutputSerializer(project).data


def _user_can_view_project(request, project):
    """
    Read access:
    - superuser / MD / Admin: any project
    - creator: own project
    - else: at least one non-archived phase with team_lead_id or member_ids match
    """
    user = getattr(request, "user", None)
    if is_global_privileged_deadline_user(user):
        return True
    if project.created_by_id == getattr(user, "id", None):
        return True
    employee_id = resolve_deadline_employee_id(user)
    if employee_id is None:
        return False
    return project.phases.filter(archived=False).filter(
        Q(team_lead_id=employee_id) | Q(member_ids__contains=[employee_id])
    ).exists()


def _create_phases(project, phases_data, *, previous_by_id=None):
    """Create phases — team_lead_id and member_ids are plain fields (no FK constraint)."""
    previous_by_id = previous_by_id or {}
    for idx, phase_data in enumerate(phases_data):
        checklist = []
        for item in phase_data.get("checklist", []) or []:
            if not isinstance(item, dict):
                continue
            incoming = dict(item)
            prev = previous_by_id.get(str(incoming.get("id") or ""))
            merge_preserved_md_fields(incoming, prev)
            checklist.append(incoming)
        DeadlineProjectPhase.objects.create(
            project=project,
            title=phase_data["title"],
            date=phase_data.get("date"),
            phase_status=phase_data.get("phase_status", "PENDING"),
            team_lead_id=phase_data.get("team_lead_id"),
            member_ids=phase_data.get("member_ids", []),
            checklist=checklist,
            notes=phase_data.get("notes", ""),
            sort_order=idx,
        )


# ---------------------------------------------------------------------------
# List + Create   — GET  /deadline/projects/
#                  — POST /deadline/projects/
# ---------------------------------------------------------------------------

class ProjectListCreateView(No403APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _base_queryset()

        user = request.user
        if not is_global_privileged_deadline_user(user):
            employee_id = resolve_deadline_employee_id(user)
            if employee_id is None:
                return Response(
                    {"success": False, "message": "Could not resolve employee id from user"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            qs = qs.filter(
                Q(created_by_id=user.id)
                | Q(phases__archived=False, phases__team_lead_id=employee_id)
                | Q(phases__archived=False, phases__member_ids__contains=[employee_id])
            ).distinct()

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        status_filter = request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)

        branch_filter = request.query_params.get("branch", "").strip()
        if branch_filter:
            qs = qs.filter(branch__icontains=branch_filter)

        data = ProjectOutputSerializer(qs, many=True, context={"request": request}).data
        return Response({"success": True, "data": data})

    def post(self, request):
        if not can_edit_project(request.user):
            return Response(
                {"success": False, "message": "You are not authorized to perform this action"},
                status=status.HTTP_200_OK,
            )

        ser = ProjectInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        with transaction.atomic():
            project = DeadlineProject.objects.create(
                title=d["title"],
                branch=d.get("branch", ""),
                description=d.get("description", ""),
                status=d.get("status", "PLANNING"),
                deadline=d.get("deadline"),
                created_by=request.user,
            )

            _create_phases(project, d.get("phases", []))

        project = _base_queryset().get(pk=project.pk)
        return Response(
            {"success": True, "data": _serialize_project(project, request=request)},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Detail / Update / Soft-Delete — GET    /deadline/projects/<id>/
#                                — PATCH  /deadline/projects/<id>/
#                                — DELETE /deadline/projects/<id>/
# ---------------------------------------------------------------------------

class ProjectDetailView(No403APIView):
    permission_classes = [IsAuthenticated]

    def _get_project(self, pk):
        try:
            return _base_queryset().get(pk=pk)
        except (DeadlineProject.DoesNotExist, ValueError):
            return None

    # ---- GET (retrieve) ---------------------------------------------------

    def get(self, request, pk):
        project = self._get_project(pk)
        if not project:
            return Response(
                {"success": False, "message": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not _user_can_view_project(request, project):
            return Response(
                {"success": False, "message": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"success": True, "data": _serialize_project(project, request=request)})

    # ---- PATCH (update) ---------------------------------------------------

    def patch(self, request, pk):
        project = self._get_project(pk)
        if not project:
            return Response(
                {"success": False, "message": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not can_edit_project(request.user, project):
            return Response(
                {"success": False, "message": "You are not authorized to perform this action"},
                status=status.HTTP_200_OK,
            )

        ser = ProjectInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        with transaction.atomic():
            if "title" in d:
                project.title = d["title"]
            if "branch" in d:
                project.branch = d["branch"]
            if "description" in d:
                project.description = d["description"]
            if "status" in d:
                project.status = d["status"]
            if "deadline" in d:
                project.deadline = d["deadline"]
            project.save()

            if "phases" in d:
                # Soft-archive ALL old phases, then recreate from payload.
                # Preserve MD approval fields by checklist item id across recreate.
                active = list(project.phases.filter(archived=False))
                previous_by_id = index_checklist_md_by_id(active)
                project.phases.filter(archived=False).update(archived=True)
                _create_phases(project, d["phases"], previous_by_id=previous_by_id)

        project = _base_queryset().get(pk=project.pk)
        return Response({"success": True, "data": _serialize_project(project, request=request)})

    # ---- DELETE (soft-archive) --------------------------------------------

    def delete(self, request, pk):
        project = self._get_project(pk)
        if not project:
            return Response(
                {"success": False, "message": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not can_edit_project(request.user, project):
            return Response(
                {"success": False, "message": "You are not authorized to perform this action"},
                status=status.HTTP_200_OK,
            )

        project.archived = True
        project.save(update_fields=["archived", "updated_at"])
        return Response({"success": True, "data": {"id": project.pk}})


# ---------------------------------------------------------------------------
# Checklist MD approval —
# POST /deadline/projects/<pk>/phases/<phase_id>/checklist/<index>/md-approval/
# ---------------------------------------------------------------------------

class ChecklistMdApprovalView(No403APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, phase_id, index):
        """
        MD-only: set checklist item mdApproval to Approved or Incomplete.
        Points are allocated only after Approved (by checkedDate month).
        """
        if not can_md_approve_checklist(request.user):
            return Response(
                {"success": False, "message": "Only MD can approve checklist items"},
                status=status.HTTP_200_OK,
            )

        try:
            project = _base_queryset().get(pk=pk)
        except (DeadlineProject.DoesNotExist, ValueError):
            return Response(
                {"success": False, "message": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            phase = project.phases.get(pk=phase_id, archived=False)
        except (DeadlineProjectPhase.DoesNotExist, ValueError):
            return Response(
                {"success": False, "message": "Phase not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        ser = ChecklistMdApprovalInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        md_approval = ser.validated_data["mdApproval"]
        md_note = ser.validated_data.get("mdNote") or ""

        checklist = list(phase.checklist or [])
        if index < 0 or index >= len(checklist):
            return Response(
                {"success": False, "message": "Checklist item index out of range"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = checklist[index]
        if not isinstance(item, dict):
            return Response(
                {"success": False, "message": "Invalid checklist item"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            apply_md_approval_to_item(
                item,
                md_approval=md_approval,
                md_note=md_note,
                approved_by=str(getattr(request.user, "username", "") or ""),
            )
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        checklist[index] = item
        phase.checklist = checklist
        phase.save(update_fields=["checklist", "updated_at"])

        project = _base_queryset().get(pk=project.pk)
        return Response(
            {
                "success": True,
                "data": {
                    "projectId": project.pk,
                    "phaseId": phase.pk,
                    "checklistIndex": index,
                    "item": item,
                    "project": _serialize_project(project, request=request),
                },
            }
        )


# ---------------------------------------------------------------------------
# Pending MD approval count —
# GET /deadline/projects/checklist-pending-md-approval/count/
# ---------------------------------------------------------------------------

class ChecklistPendingMdApprovalCountView(No403APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        MD-only: counts of checked checklist items Pending / Incomplete.
        GET /deadline/projects/checklist-pending-md-approval/count/
        """
        if not can_md_approve_checklist(request.user):
            return Response(
                {"success": False, "message": "Only MD can view pending checklist approval count"},
                status=status.HTTP_200_OK,
            )
        counts = count_md_approval_checklists()
        return Response(
            {
                "success": True,
                "count": counts["pending"],
                "pending": counts["pending"],
                "incomplete": counts["incomplete"],
            }
        )


# ---------------------------------------------------------------------------
# Checklist points — GET /deadline/projects/checklist-points/
# ---------------------------------------------------------------------------

class ChecklistPointsView(No403APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Checklist performance points from project phase checklists.
        GET /deadline/projects/checklist-points/?year=2026&month=4
        Optional: ?employee=<username>
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

        data = build_checklist_points(target_user, year, month=month, quarter=quarter)
        return Response(data)
