"""
MD-managed per-employee, per-month P&S service scoring targets API.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.filters import _get_user_role_sync
from accounts.models import Profile, PsScoringTarget
from accounts.mmr_rg_scoring_targets import parse_target_year_month
from accounts.ps_scoring_targets import (
    build_ps_target_payload,
    default_ps_scoring_targets,
    is_ps_profile,
    ps_profiles_queryset,
    user_can_edit_ps_targets,
    user_can_view_ps_targets,
)
from accounts.ps_service_scoring import build_ps_service_points
from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user


def _forbidden(detail: str = "You do not have permission to access P&S scoring targets."):
    return Response({"detail": detail}, status=status.HTTP_403_FORBIDDEN)


def _parse_period_from_request(request) -> tuple[int, int] | None:
    return parse_target_year_month(
        request.query_params.get("year"),
        request.query_params.get("month"),
    )


def _period_required_response():
    return Response(
        {"detail": "Query parameters 'year' and 'month' are required (e.g. ?year=2026&month=7)."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _get_ps_profile(username: str) -> Profile | None:
    profile = (
        Profile.objects.filter(
            Employee_id__username=username,
            Employee_id__is_active=True,
        )
        .select_related("Role", "Employee_id")
        .prefetch_related("functions")
        .first()
    )
    if profile is None or not is_ps_profile(profile):
        return None
    return profile


def _parse_target_payload(data: dict) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."
    if "monthly_quantity_target" not in data:
        return None, "Provide monthly_quantity_target."
    raw = data.get("monthly_quantity_target")
    if raw is None:
        return {"monthly_quantity_target": None}, None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None, "monthly_quantity_target must be a positive number."
    if value <= 0:
        return None, "monthly_quantity_target must be a positive number."
    return {"monthly_quantity_target": value}, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_ps_scoring_targets(request):
    """
    List P&S employees with monthly service targets.
    GET /accounts/ps-scoring-targets/?year=2026&month=7
    """
    if not user_can_view_ps_targets(request.user, _get_user_role_sync):
        return _forbidden()

    period = _parse_period_from_request(request)
    if period is None:
        return _period_required_response()
    year, month = period

    employees = [build_ps_target_payload(profile, year, month) for profile in ps_profiles_queryset()]
    defaults = default_ps_scoring_targets()
    return Response(
        {
            "year": year,
            "month": month,
            "period": f"{year}-{month:02d}",
            "count": len(employees),
            "defaults": defaults,
            "employees": employees,
        }
    )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def ps_scoring_target_detail(request, employee_id: str):
    """
    GET /accounts/ps-scoring-targets/<employee_id>/?year=2026&month=7  — MD/HR
    PUT/PATCH /accounts/ps-scoring-targets/<employee_id>/?year=2026&month=7 — MD only
    Body: { "monthly_quantity_target": 120 }
    """
    username = (employee_id or "").strip()
    if not username:
        return Response({"detail": "employee_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    period = _parse_period_from_request(request)
    if period is None:
        return _period_required_response()
    year, month = period

    if request.method == "GET":
        if not user_can_view_ps_targets(request.user, _get_user_role_sync):
            return _forbidden()
        profile = _get_ps_profile(username)
        if profile is None:
            return Response({"detail": "P&S employee not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_ps_target_payload(profile, year, month))

    if not user_can_edit_ps_targets(request.user, _get_user_role_sync):
        return _forbidden("Only MD can set P&S scoring targets.")

    profile = _get_ps_profile(username)
    if profile is None:
        return Response({"detail": "P&S employee not found."}, status=status.HTTP_404_NOT_FOUND)

    parsed, err = _parse_target_payload(request.data)
    if err is not None:
        return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        record, _created = PsScoringTarget.objects.get_or_create(
            profile=profile, year=year, month=month
        )
        record.monthly_quantity_target = parsed["monthly_quantity_target"]
        record.set_by = request.user
        record.save()

    return Response(build_ps_target_payload(profile, year, month))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ps_service_points(request):
    """
    P&S service performance points for an employee.
    GET /accounts/ps-service-points/?year=2026&month=7
    """
    year, month, quarter, period_err = parse_leave_points_period(request)
    if period_err:
        return Response({"detail": period_err}, status=status.HTTP_400_BAD_REQUEST)

    target_user, user_err = resolve_leave_points_user(
        request,
        request.query_params.get("employee_id") or request.query_params.get("username"),
    )
    if user_err:
        return Response({"detail": user_err}, status=status.HTTP_400_BAD_REQUEST)

    data = build_ps_service_points(target_user, year, month=month, quarter=quarter)
    return Response(data)
