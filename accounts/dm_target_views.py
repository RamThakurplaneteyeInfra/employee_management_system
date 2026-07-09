"""
MD-managed per-employee, per-month DM scoring targets API.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.filters import _get_user_role_sync
from accounts.models import DmScoringTarget, Profile

from .mmr_rg_scoring_targets import parse_target_year_month
from .dm_scoring_targets import (
    build_dm_target_payload,
    default_dm_scoring_targets,
    dm_profiles_queryset,
    is_dm_profile,
    user_can_edit_dm_targets,
    user_can_view_dm_targets,
)

_TARGET_FIELDS = (
    "digital_media_target_count",
    "digital_content_target_count",
)


def _forbidden(detail: str = "You do not have permission to access DM scoring targets."):
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


def _get_dm_profile(username: str) -> Profile | None:
    profile = (
        Profile.objects.filter(
            Employee_id__username=username,
            Employee_id__is_active=True,
        )
        .select_related("Role", "Employee_id")
        .prefetch_related("functions")
        .first()
    )
    if profile is None or not is_dm_profile(profile):
        return None
    return profile


def _parse_target_payload(data: dict) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."
    parsed: dict = {}
    for field in _TARGET_FIELDS:
        if field not in data:
            continue
        raw = data.get(field)
        if raw is None:
            parsed[field] = None
            continue
        try:
            count = int(raw)
        except (TypeError, ValueError):
            return None, f"{field} must be a positive integer."
        if count <= 0:
            return None, f"{field} must be a positive integer."
        parsed[field] = count
    if not parsed:
        return None, "Provide at least one target field to update."
    return parsed, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_dm_scoring_targets(request):
    """
    List DM employees with targets for a specific month.
    GET /accounts/dm-scoring-targets/?year=2026&month=7
    MD and HR only.
    """
    if not user_can_view_dm_targets(request.user, _get_user_role_sync):
        return _forbidden()

    period = _parse_period_from_request(request)
    if period is None:
        return _period_required_response()
    year, month = period

    employees = [build_dm_target_payload(profile, year, month) for profile in dm_profiles_queryset()]
    defaults = default_dm_scoring_targets()
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
def dm_scoring_target_detail(request, employee_id: str):
    """
    GET /accounts/dm-scoring-targets/<employee_id>/?year=2026&month=7  — MD/HR
    PUT/PATCH /accounts/dm-scoring-targets/<employee_id>/?year=2026&month=7 — MD only
    """
    username = (employee_id or "").strip()
    if not username:
        return Response({"detail": "employee_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    period = _parse_period_from_request(request)
    if period is None:
        return _period_required_response()
    year, month = period

    if request.method == "GET":
        if not user_can_view_dm_targets(request.user, _get_user_role_sync):
            return _forbidden()
        profile = _get_dm_profile(username)
        if profile is None:
            return Response({"detail": "DM employee not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_dm_target_payload(profile, year, month))

    if not user_can_edit_dm_targets(request.user, _get_user_role_sync):
        return _forbidden("Only MD can set DM scoring targets.")

    profile = _get_dm_profile(username)
    if profile is None:
        return Response({"detail": "DM employee not found."}, status=status.HTTP_404_NOT_FOUND)

    parsed, err = _parse_target_payload(request.data)
    if err is not None:
        return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        record, _created = DmScoringTarget.objects.get_or_create(profile=profile, year=year, month=month)
        if request.method == "PUT":
            for field in _TARGET_FIELDS:
                setattr(record, field, parsed.get(field))
        else:
            for field, value in parsed.items():
                setattr(record, field, value)
        record.set_by = request.user
        record.save()

    return Response(build_dm_target_payload(profile, year, month))

