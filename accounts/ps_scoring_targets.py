"""
Resolve P&S per-employee, per-month service-quantity targets with system defaults.
"""

from __future__ import annotations

from decimal import Decimal

from .models import Profile, PsScoringTarget

PS_FUNCTIONS = frozenset({"P&S"})

DEFAULT_MONTHLY_QUANTITY_TARGET = Decimal("100")
PS_SERVICE_MAX_MAIN_POINTS = 70.0

PS_TARGET_VIEW_ROLES = frozenset({"HR", "Hr", "MD"})
PS_TARGET_EDIT_ROLES = frozenset({"MD"})


def _profile_function_names_upper(profile: Profile | None) -> set[str]:
    if profile is None:
        return set()
    try:
        return {
            (f.function or "").strip().upper()
            for f in profile.functions.all()
            if f is not None and getattr(f, "function", None)
        }
    except Exception:
        return set()


def is_ps_profile(profile: Profile | None) -> bool:
    return "P&S" in _profile_function_names_upper(profile)


def default_ps_scoring_targets() -> dict:
    return {
        "monthly_quantity_target": float(DEFAULT_MONTHLY_QUANTITY_TARGET),
        "service_max_main_points": PS_SERVICE_MAX_MAIN_POINTS,
    }


def _serialize_target_row(record: PsScoringTarget | None) -> dict | None:
    if record is None:
        return None
    return {
        "year": record.year,
        "month": record.month,
        "monthly_quantity_target": (
            float(record.monthly_quantity_target)
            if record.monthly_quantity_target is not None
            else None
        ),
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "set_by": record.set_by_id,
    }


def _custom_fields_from_record(custom: PsScoringTarget | None) -> set[str]:
    if custom is None:
        return set()
    if custom.monthly_quantity_target is not None:
        return {"monthly_quantity_target"}
    return set()


def resolve_ps_scoring_targets(
    user,
    *,
    year: int | None = None,
    month: int | None = None,
    profile: Profile | None = None,
    custom: PsScoringTarget | None = None,
) -> dict:
    defaults = default_ps_scoring_targets()
    if profile is None:
        profile = (
            Profile.objects.filter(Employee_id=user)
            .prefetch_related("functions")
            .first()
        )
    eligible = is_ps_profile(profile)

    if custom is None and profile is not None and year is not None and month is not None:
        custom = PsScoringTarget.objects.filter(profile=profile, year=year, month=month).first()

    if custom is not None and custom.monthly_quantity_target is not None:
        monthly_target = Decimal(str(custom.monthly_quantity_target))
    else:
        monthly_target = DEFAULT_MONTHLY_QUANTITY_TARGET

    custom_fields = _custom_fields_from_record(custom)
    return {
        "eligible": eligible,
        "year": year,
        "month": month,
        "defaults": defaults,
        "custom": _serialize_target_row(custom),
        "custom_fields": sorted(custom_fields),
        "is_customized": bool(custom_fields),
        "monthly_quantity_target": float(monthly_target),
        "service_max_main_points": PS_SERVICE_MAX_MAIN_POINTS,
    }


def ps_profiles_queryset():
    return (
        Profile.objects.filter(Employee_id__is_active=True, functions__function="P&S")
        .select_related("Role", "Employee_id")
        .prefetch_related("functions")
        .distinct()
        .order_by("Name")
    )


def build_ps_target_payload(profile: Profile, year: int, month: int) -> dict:
    targets = resolve_ps_scoring_targets(profile.Employee_id, year=year, month=month, profile=profile)
    function_names = sorted(_profile_function_names_upper(profile))
    return {
        "employee_id": profile.Employee_id.username,
        "name": profile.Name,
        "employee_functions": function_names,
        "year": year,
        "month": month,
        "period": f"{year}-{month:02d}",
        "eligible": targets["eligible"],
        "defaults": targets["defaults"],
        "custom": targets["custom"],
        "custom_fields": targets["custom_fields"],
        "is_customized": targets["is_customized"],
        "effective_targets": {
            "monthly_quantity_target": targets["monthly_quantity_target"],
        },
        "max_main_points": {
            "service": targets["service_max_main_points"],
        },
    }


def user_can_view_ps_targets(user, get_user_role) -> bool:
    if not user or not user.is_authenticated:
        return False
    return (get_user_role(user) or "").strip() in PS_TARGET_VIEW_ROLES


def user_can_edit_ps_targets(user, get_user_role) -> bool:
    if not user or not user.is_authenticated:
        return False
    return (get_user_role(user) or "").strip() in PS_TARGET_EDIT_ROLES


__all__ = [
    "PS_FUNCTIONS",
    "DEFAULT_MONTHLY_QUANTITY_TARGET",
    "PS_SERVICE_MAX_MAIN_POINTS",
    "is_ps_profile",
    "default_ps_scoring_targets",
    "resolve_ps_scoring_targets",
    "ps_profiles_queryset",
    "build_ps_target_payload",
    "user_can_view_ps_targets",
    "user_can_edit_ps_targets",
]
