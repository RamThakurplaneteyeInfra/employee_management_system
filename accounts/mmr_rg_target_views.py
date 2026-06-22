"""
MD-managed per-employee, per-month MMR/RG scoring targets API.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.filters import _get_user_role_sync
from accounts.models import MmrRgScoringTarget, Profile

from .mmr_rg_scoring_targets import (
    build_mmr_rg_target_payload,
    default_mmr_rg_scoring_targets,
    is_mmr_rg_profile,
    mmr_rg_profiles_queryset,
    parse_target_year_month,
    user_can_edit_mmr_rg_targets,
    user_can_view_mmr_rg_targets,
)

_TARGET_FIELDS = (
    "customer_panel_target_amount",
    "proposal_target_amount",
    "profile_count_target",
    "proforma_target_amount",
)


def _forbidden(detail: str = "You do not have permission to access MMR/RG scoring targets."):
    return Response({"detail": detail}, status=status.HTTP_403_FORBIDDEN)


def _parse_period_from_request(request) -> tuple[int, int] | None:
    return parse_target_year_month(
        request.query_params.get("year"),
        request.query_params.get("month"),
    )


def _period_required_response():
    return Response(
        {"detail": "Query parameters 'year' and 'month' are required (e.g. ?year=2026&month=6)."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _get_mmr_rg_profile(username: str) -> Profile | None:
    profile = (
        Profile.objects.filter(
            Employee_id__username=username,
            Employee_id__is_active=True,
        )
        .select_related("Role", "Employee_id")
        .prefetch_related("functions")
        .first()
    )
    if profile is None or not is_mmr_rg_profile(profile):
        return None
    return profile


def _parse_decimal(value, field_name: str):
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.") from None
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return parsed


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
        if field == "profile_count_target":
            try:
                count = int(raw)
            except (TypeError, ValueError):
                return None, "profile_count_target must be a positive integer."
            if count <= 0:
                return None, "profile_count_target must be a positive integer."
            parsed[field] = count
            continue
        try:
            parsed[field] = _parse_decimal(raw, field)
        except ValueError as exc:
            return None, str(exc)
    if not parsed:
        return None, "Provide at least one target field to update."
    return parsed, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_mmr_rg_scoring_targets(request):
    """
    List MMR/RG employees with targets for a specific month.
    GET /accounts/mmr-rg-scoring-targets/?year=2026&month=6
    MD and HR only.
    """
    if not user_can_view_mmr_rg_targets(request.user, _get_user_role_sync):
        return _forbidden()

    period = _parse_period_from_request(request)
    if period is None:
        return _period_required_response()
    year, month = period

    employees = [
        build_mmr_rg_target_payload(profile, year, month)
        for profile in mmr_rg_profiles_queryset()
    ]
    defaults = default_mmr_rg_scoring_targets()
    return Response(
        {
            "year": year,
            "month": month,
            "period": f"{year}-{month:02d}",
            "count": len(employees),
            "defaults": {
                key: float(defaults[key]) if isinstance(defaults[key], Decimal) else defaults[key]
                for key in defaults
            },
            "employees": employees,
        }
    )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def mmr_rg_scoring_target_detail(request, employee_id: str):
    """
    GET /accounts/mmr-rg-scoring-targets/<employee_id>/?year=2026&month=6  — MD/HR
    PUT/PATCH /accounts/mmr-rg-scoring-targets/<employee_id>/?year=2026&month=6 — MD only
    """
    username = (employee_id or "").strip()
    if not username:
        return Response({"detail": "employee_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    period = _parse_period_from_request(request)
    if period is None:
        return _period_required_response()
    year, month = period

    if request.method == "GET":
        if not user_can_view_mmr_rg_targets(request.user, _get_user_role_sync):
            return _forbidden()
        profile = _get_mmr_rg_profile(username)
        if profile is None:
            return Response(
                {"detail": "MMR/RG employee not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(build_mmr_rg_target_payload(profile, year, month))

    if not user_can_edit_mmr_rg_targets(request.user, _get_user_role_sync):
        return _forbidden("Only MD can set MMR/RG scoring targets.")

    profile = _get_mmr_rg_profile(username)
    if profile is None:
        return Response(
            {"detail": "MMR/RG employee not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    parsed, err = _parse_target_payload(request.data)
    if err is not None:
        return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        record, _created = MmrRgScoringTarget.objects.get_or_create(
            profile=profile,
            year=year,
            month=month,
        )
        if request.method == "PUT":
            for field in _TARGET_FIELDS:
                setattr(record, field, parsed.get(field))
        else:
            for field, value in parsed.items():
                setattr(record, field, value)
        record.set_by = request.user
        record.save()

    return Response(build_mmr_rg_target_payload(profile, year, month))


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def reset_mmr_rg_scoring_target(request, employee_id: str):
    """
    DELETE /accounts/mmr-rg-scoring-targets/<employee_id>/reset/?year=2026&month=6
    Remove custom targets for one month (revert to defaults). MD only.

    Optional: ?year=2026 without month deletes all custom rows for that calendar year.
    """
    if not user_can_edit_mmr_rg_targets(request.user, _get_user_role_sync):
        return _forbidden("Only MD can reset MMR/RG scoring targets.")

    profile = _get_mmr_rg_profile((employee_id or "").strip())
    if profile is None:
        return Response(
            {"detail": "MMR/RG employee not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    raw_year = request.query_params.get("year")
    raw_month = request.query_params.get("month")
    if raw_year is None:
        return _period_required_response()

    try:
        year = int(raw_year)
    except (TypeError, ValueError):
        return Response({"detail": "year must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)

    if raw_month is None:
        deleted, _ = MmrRgScoringTarget.objects.filter(profile=profile, year=year).delete()
        return Response(
            {
                "detail": f"Removed {deleted} custom target row(s) for {profile.Employee_id.username} in {year}.",
                "employee_id": profile.Employee_id.username,
                "year": year,
                "deleted_count": deleted,
            }
        )

    period = parse_target_year_month(raw_year, raw_month)
    if period is None:
        return Response(
            {"detail": "month must be between 1 and 12."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    year, month = period
    MmrRgScoringTarget.objects.filter(profile=profile, year=year, month=month).delete()
    return Response(build_mmr_rg_target_payload(profile, year, month))
