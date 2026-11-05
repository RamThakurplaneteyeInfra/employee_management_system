"""Daily work project assignment and employee reports."""

from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.auth_utils import CsrfExemptSessionAuthentication

from .categories import UPDATE_KEYS, empty_updates, reporting_for_profile
from .models import DailyProject, DailyWorkReport, DailyWorkReportSeen
from .services import (
    apply_assignments,
    assignment_payload,
    can_delete_project,
    can_manage_any_project,
    can_manage_project,
    display_name,
    is_team_lead_user,
    list_people,
    profile_for_user,
    user_is_assigned,
)


def _error(message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"success": False, "error": message}, status=http_status)


def _validation_message(exc) -> str:
    detail = getattr(exc, "detail", exc)
    if isinstance(detail, dict):
        parts = []
        for key, value in detail.items():
            text = value
            if isinstance(value, (list, tuple)):
                text = " ".join(str(item) for item in value)
            parts.append(f"{key}: {text}")
        return " ".join(parts)
    if isinstance(detail, (list, tuple)):
        return " ".join(str(item) for item in detail)
    return str(detail)


def _projects_for_lead(user):
    qs = DailyProject.objects.prefetch_related("assignments")
    if can_manage_any_project(user):
        return qs
    return qs.filter(team_lead=user)


def _normalize_updates(payload) -> dict:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("updates must be an object.")
    unknown = [key for key in payload.keys() if key not in UPDATE_KEYS]
    if unknown:
        raise ValueError(f"Unknown update fields: {unknown}.")
    normalized = empty_updates()
    for key in UPDATE_KEYS:
        raw_items = payload.get(key, [])
        if raw_items is None:
            raw_items = []
        if not isinstance(raw_items, list):
            raise ValueError(f"{key} must be a list.")
        cleaned = []
        for item in raw_items:
            if not isinstance(item, dict) or "work" not in item:
                raise ValueError(f"{key} items must be objects with a work field.")
            text = str(item.get("work") or "").strip()
            if text:
                cleaned.append({"work": text})
        normalized[key] = cleaned
    return normalized


def _report_payload(report: DailyWorkReport, *, is_seen: bool = True) -> dict:
    return {
        "id": report.id,
        "date": report.report_date.isoformat(),
        "employee_id": report.employee_id,
        "employee_name": report.employee_name,
        "employee_category": report.employee_category,
        "project_id": report.project_id,
        "project_name": report.project.project_name,
        "updates": report.updates or empty_updates(),
        "status": report.status,
        "is_seen": is_seen,
    }


def _visible_reports_qs(user):
    """Every authenticated employee can read reports for every project."""
    return DailyWorkReport.objects.select_related("project", "employee")


def _seen_report_ids(viewer, report_ids) -> set[int]:
    if not report_ids:
        return set()
    return set(
        DailyWorkReportSeen.objects.filter(
            viewer=viewer,
            report_id__in=report_ids,
        ).values_list("report_id", flat=True)
    )


def _is_report_seen(report: DailyWorkReport, viewer, seen_ids: set[int]) -> bool:
    # Own submissions never count as unseen for the author.
    if report.employee_id == viewer.id:
        return True
    return report.id in seen_ids


def _reports_grouped_by_project(reports, viewer) -> list[dict]:
    """Group submitted reports under each project (project-first, not employee-first)."""
    seen_ids = _seen_report_ids(viewer, [report.id for report in reports])
    groups = {}
    order = []
    for report in reports:
        key = report.project_id
        if key not in groups:
            groups[key] = {
                "project_id": report.project_id,
                "project_name": report.project.project_name,
                "team_lead_id": report.project.team_lead_id,
                "can_delete": can_delete_project(viewer, report.project),
                "report_count": 0,
                "unseen_count": 0,
                "reports": [],
            }
            order.append(key)
        is_seen = _is_report_seen(report, viewer, seen_ids)
        item = _report_payload(report, is_seen=is_seen)
        groups[key]["reports"].append(item)
        groups[key]["report_count"] = len(groups[key]["reports"])
        if not is_seen:
            groups[key]["unseen_count"] += 1
    return [groups[key] for key in order]


class EmployeeListView(APIView):
    """Registered EMS employees for the team-lead picker. Interns are excluded."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Empty list for non-leads (avoid 403 → frontend logout on Daily Work open).
        if not is_team_lead_user(request.user):
            return Response({"employees": []})
        return Response({"employees": list_people(interns=False)})


class InternListView(APIView):
    """Registered EMS interns for the team-lead picker."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_team_lead_user(request.user):
            return Response({"interns": []})
        return Response({"interns": list_people(interns=True)})


class ProjectListCreateView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Employees often open Daily Work and hit this URL. Return [] instead of
        # 403 so the frontend does not treat it as a forced logout.
        if not is_team_lead_user(request.user):
            return Response([])
        projects = [
            assignment_payload(project, viewer=request.user)
            for project in _projects_for_lead(request.user)
        ]
        return Response(projects)

    def post(self, request):
        if not is_team_lead_user(request.user):
            return _error("Team Lead access only.", status.HTTP_403_FORBIDDEN)
        body = request.data if isinstance(request.data, dict) else {}
        name = str(body.get("project_name") or "").strip()
        if not name:
            return _error("project_name is required.")
        description = str(body.get("project_description") or "").strip()
        status_value = str(body.get("status") or DailyProject.Status.ACTIVE).strip().lower()
        if status_value not in DailyProject.Status.values:
            return _error("status must be active or inactive.")
        try:
            with transaction.atomic():
                project = DailyProject.objects.create(
                    project_name=name,
                    project_description=description,
                    team_lead=request.user,
                    status=status_value,
                )
                apply_assignments(
                    project,
                    _present_list(body, "employees", default=[]),
                    _present_list(body, "interns", default=[]),
                )
        except ValidationError as exc:
            return _error(_validation_message(exc))
        project = DailyProject.objects.prefetch_related("assignments").get(pk=project.pk)
        return Response(
            assignment_payload(project, viewer=request.user),
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(
            DailyProject.objects.prefetch_related("assignments"),
            pk=project_id,
        )
        if not can_manage_project(request.user, project):
            return _error("You can only view projects you lead.", status.HTTP_403_FORBIDDEN)
        return Response(assignment_payload(project, viewer=request.user))

    def patch(self, request, project_id):
        project = get_object_or_404(
            DailyProject.objects.prefetch_related("assignments"),
            pk=project_id,
        )
        if not can_manage_project(request.user, project):
            return _error(
                "You can only manage projects you lead.",
                status.HTTP_403_FORBIDDEN,
            )
        body = request.data if isinstance(request.data, dict) else {}
        if "project_name" in body:
            name = str(body.get("project_name") or "").strip()
            if not name:
                return _error("project_name is required.")
            project.project_name = name
        if "project_description" in body:
            project.project_description = str(body.get("project_description") or "").strip()
        if "status" in body:
            status_value = str(body.get("status") or "").strip().lower()
            if status_value not in DailyProject.Status.values:
                return _error("status must be active or inactive.")
            project.status = status_value
        try:
            with transaction.atomic():
                project.save()
                apply_assignments(
                    project,
                    _present_list(body, "employees"),
                    _present_list(body, "interns"),
                )
        except ValidationError as exc:
            return _error(_validation_message(exc))
        project = DailyProject.objects.prefetch_related("assignments").get(pk=project.pk)
        return Response(assignment_payload(project, viewer=request.user))

    def delete(self, request, project_id):
        """Creator or MD only. Removes the project, its assignments, and its reports."""
        project = get_object_or_404(DailyProject, pk=project_id)
        if not can_delete_project(request.user, project):
            return _error(
                "Only the project creator or MD can delete this project.",
                status.HTTP_403_FORBIDDEN,
            )
        project_name = project.project_name
        with transaction.atomic():
            # Reports PROTECT the project FK; clear them (seen rows CASCADE) first.
            DailyWorkReport.objects.filter(project=project).delete()
            project.delete()
        return Response(
            {
                "success": True,
                "deleted": True,
                "project_id": project_id,
                "project_name": project_name,
                "message": "Project deleted.",
            },
            status=status.HTTP_200_OK,
        )


class MyProjectListView(APIView):
    """Projects the logged-in employee or intern can report on."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = profile_for_user(request.user)
        category, allowed_fields, _restricted = reporting_for_profile(profile)
        projects = (
            DailyProject.objects.filter(
                assignments__user=request.user,
                status=DailyProject.Status.ACTIVE,
            )
            .distinct()
            .order_by("project_name", "id")
        )
        return Response(
            {
                "employee_id": request.user.id,
                "employee_name": display_name(request.user),
                "employee_category": category,
                "allowed_update_fields": allowed_fields,
                "projects": [
                    {
                        "project_id": project.id,
                        "project_name": project.project_name,
                        "project_description": project.project_description,
                        "status": project.status,
                    }
                    for project in projects
                ],
            }
        )


class DailyReportView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _visible_reports_qs(request.user)
        project_id = (request.query_params.get("project_id") or "").strip()
        report_date = (request.query_params.get("date") or "").strip()
        employee_id = (request.query_params.get("employee_id") or "").strip()

        if project_id:
            if not project_id.isdigit():
                return _error("project_id must be an integer.")
            qs = qs.filter(project_id=int(project_id))
        if employee_id:
            if not employee_id.isdigit():
                return _error("employee_id must be an integer.")
            qs = qs.filter(employee_id=int(employee_id))
        if report_date:
            parsed = _parse_date(report_date)
            if parsed is None:
                return _error("date must be YYYY-MM-DD.")
            qs = qs.filter(report_date=parsed)
        rows = list(
            qs.order_by("project__project_name", "project_id", "-report_date", "employee_name", "id")
        )
        seen_ids = _seen_report_ids(request.user, [report.id for report in rows])
        # Default: project-wise. Pass flat=1 for the previous employee-level list.
        if (request.query_params.get("flat") or "").strip().lower() in ("1", "true", "yes"):
            payload = [
                _report_payload(
                    report,
                    is_seen=_is_report_seen(report, request.user, seen_ids),
                )
                for report in rows
            ]
            unseen_count = sum(1 for item in payload if not item["is_seen"])
            return Response(
                {
                    "success": True,
                    "result_count": len(payload),
                    "unseen_count": unseen_count,
                    "reports": payload,
                }
            )
        projects = _reports_grouped_by_project(rows, request.user)
        return Response(
            {
                "success": True,
                "result_count": len(rows),
                "unseen_count": sum(group["unseen_count"] for group in projects),
                "projects": projects,
            }
        )

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        if "employee_id" in body and str(body.get("employee_id")).strip() not in (
            "",
            str(request.user.id),
        ):
            return _error(
                "You can only submit your own daily report.",
                status.HTTP_403_FORBIDDEN,
            )
        project_id = body.get("project_id")
        if isinstance(project_id, bool) or not isinstance(project_id, (int, str)):
            return _error("project_id is required.")
        if not str(project_id).strip().isdigit():
            return _error("project_id must be an integer.")
        project = DailyProject.objects.filter(pk=int(project_id)).first()
        if project is None:
            return _error("Project not found.", status.HTTP_404_NOT_FOUND)
        if project.status != DailyProject.Status.ACTIVE:
            return _error("This project is not active.")
        if not user_is_assigned(project, request.user):
            return _error(
                "Only assigned members can submit reports for this project.",
                status.HTTP_403_FORBIDDEN,
            )
        parsed_date = _parse_date(str(body.get("date") or ""))
        if parsed_date is None:
            return _error("date must be YYYY-MM-DD.")

        profile = profile_for_user(request.user)
        category, _allowed_fields, _restricted = reporting_for_profile(profile)
        try:
            updates = _normalize_updates(body.get("updates"))
        except ValueError as exc:
            return _error(str(exc))

        report, created = DailyWorkReport.objects.update_or_create(
            employee=request.user,
            project=project,
            report_date=parsed_date,
            defaults={
                "employee_name": display_name(request.user),
                "employee_category": category,
                "updates": updates,
                "status": DailyWorkReport.Status.SUBMITTED,
            },
        )
        # Resubmit clears prior "seen" so co-members get a fresh unseen badge.
        if not created:
            DailyWorkReportSeen.objects.filter(report=report).delete()
        report = DailyWorkReport.objects.select_related("project").get(pk=report.pk)
        return Response(
            _report_payload(report, is_seen=True),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MarkReportsSeenView(APIView):
    """Mark other people's reports as seen for the logged-in viewer."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        report_ids = body.get("report_ids")
        project_id = body.get("project_id")
        report_date = body.get("date")

        visible = _visible_reports_qs(request.user).exclude(employee=request.user)
        if report_ids is not None:
            if not isinstance(report_ids, list) or not report_ids:
                return _error("report_ids must be a non-empty list of integers.")
            parsed_ids = []
            for item in report_ids:
                if isinstance(item, bool) or not isinstance(item, (int, str)) or not str(item).strip().isdigit():
                    return _error("report_ids must be a non-empty list of integers.")
                parsed_ids.append(int(item))
            visible = visible.filter(id__in=parsed_ids)
        else:
            if project_id is not None:
                if isinstance(project_id, bool) or not str(project_id).strip().isdigit():
                    return _error("project_id must be an integer.")
                visible = visible.filter(project_id=int(project_id))
            if report_date is not None:
                parsed = _parse_date(str(report_date))
                if parsed is None:
                    return _error("date must be YYYY-MM-DD.")
                visible = visible.filter(report_date=parsed)
            if project_id is None and report_date is None:
                return _error("Provide report_ids, or project_id and/or date.")

        targets = list(visible.values_list("id", flat=True))
        for report_id in targets:
            DailyWorkReportSeen.objects.get_or_create(
                report_id=report_id,
                viewer=request.user,
            )
        remaining = (
            _visible_reports_qs(request.user)
            .exclude(employee=request.user)
            .exclude(seen_by__viewer=request.user)
            .count()
        )
        return Response(
            {
                "success": True,
                "marked_count": len(targets),
                "unseen_count": remaining,
            }
        )


class UnseenReportCountView(APIView):
    """Badge count of co-member reports the viewer has not opened yet."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _visible_reports_qs(request.user).exclude(employee=request.user)
        project_id = (request.query_params.get("project_id") or "").strip()
        report_date = (request.query_params.get("date") or "").strip()
        if project_id:
            if not project_id.isdigit():
                return _error("project_id must be an integer.")
            qs = qs.filter(project_id=int(project_id))
        if report_date:
            parsed = _parse_date(report_date)
            if parsed is None:
                return _error("date must be YYYY-MM-DD.")
            qs = qs.filter(report_date=parsed)
        unseen_count = qs.exclude(seen_by__viewer=request.user).count()
        return Response({"success": True, "unseen_count": unseen_count})


def _present_list(body, key, default=None):
    """Return the list when the key was sent. Missing key keeps the current list."""
    if key not in body:
        return default
    value = body.get(key)
    if value is None:
        return []
    return value


def _parse_date(value: str):
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None
