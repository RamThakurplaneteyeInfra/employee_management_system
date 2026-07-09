"""
Resolve DM per-employee, per-month scoring targets with system defaults as fallback.
"""

from __future__ import annotations

from .models import DmScoringTarget, Profile

DM_FUNCTIONS = frozenset({"DM"})

DEFAULT_DIGITAL_MEDIA_TARGET_COUNT = 10
DEFAULT_DIGITAL_CONTENT_TARGET_COUNT = 8

DM_MEDIA_MAX_MAIN_POINTS = 40.0
DM_CONTENT_MAX_MAIN_POINTS = 30.0

DM_TARGET_VIEW_ROLES = frozenset({"HR", "Hr", "MD"})
DM_TARGET_EDIT_ROLES = frozenset({"MD"})


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


def is_dm_profile(profile: Profile | None) -> bool:
    return bool(_profile_function_names_upper(profile) & DM_FUNCTIONS)


def default_dm_scoring_targets() -> dict:
    return {
        "digital_media_target_count": DEFAULT_DIGITAL_MEDIA_TARGET_COUNT,
        "digital_content_target_count": DEFAULT_DIGITAL_CONTENT_TARGET_COUNT,
        "digital_media_max_main_points": DM_MEDIA_MAX_MAIN_POINTS,
        "digital_content_max_main_points": DM_CONTENT_MAX_MAIN_POINTS,
        "dm_work_max_main_points": DM_MEDIA_MAX_MAIN_POINTS + DM_CONTENT_MAX_MAIN_POINTS,
    }


def _serialize_target_row(record: DmScoringTarget | None) -> dict | None:
    if record is None:
        return None
    return {
        "year": record.year,
        "month": record.month,
        "digital_media_target_count": record.digital_media_target_count,
        "digital_content_target_count": record.digital_content_target_count,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "set_by": record.set_by_id,
    }


def _custom_fields_from_record(custom: DmScoringTarget | None) -> set[str]:
    custom_fields: set[str] = set()
    if custom is None:
        return custom_fields
    if custom.digital_media_target_count is not None:
        custom_fields.add("digital_media_target_count")
    if custom.digital_content_target_count is not None:
        custom_fields.add("digital_content_target_count")
    return custom_fields


def _effective_targets_from_record(custom: DmScoringTarget | None, defaults: dict) -> dict:
    return {
        "digital_media_target_count": (
            custom.digital_media_target_count
            if custom is not None and custom.digital_media_target_count is not None
            else defaults["digital_media_target_count"]
        ),
        "digital_content_target_count": (
            custom.digital_content_target_count
            if custom is not None and custom.digital_content_target_count is not None
            else defaults["digital_content_target_count"]
        ),
    }


def dm_profiles_queryset():
    return (
        Profile.objects.filter(Employee_id__is_active=True, functions__function__in=list(DM_FUNCTIONS))
        .select_related("Role", "Employee_id")
        .prefetch_related("functions")
        .distinct()
        .order_by("Name")
    )


def resolve_dm_scoring_targets(
    user,
    *,
    year: int | None = None,
    month: int | None = None,
    profile: Profile | None = None,
    custom: DmScoringTarget | None = None,
) -> dict:
    defaults = default_dm_scoring_targets()
    if profile is None:
        profile = (
            Profile.objects.filter(Employee_id=user)
            .prefetch_related("functions")
            .first()
        )
    eligible = is_dm_profile(profile)

    if custom is None and profile is not None and year is not None and month is not None:
        custom = DmScoringTarget.objects.filter(profile=profile, year=year, month=month).first()

    effective = _effective_targets_from_record(custom, defaults)
    custom_fields = _custom_fields_from_record(custom)

    return {
        "eligible": eligible,
        "year": year,
        "month": month,
        "defaults": defaults,
        "custom": _serialize_target_row(custom),
        "custom_fields": sorted(custom_fields),
        "is_customized": bool(custom_fields),
        "digital_media_target_count": int(effective["digital_media_target_count"]),
        "digital_content_target_count": int(effective["digital_content_target_count"]),
        "digital_media_max_main_points": float(defaults["digital_media_max_main_points"]),
        "digital_content_max_main_points": float(defaults["digital_content_max_main_points"]),
    }


def build_dm_target_payload(profile: Profile, year: int, month: int) -> dict:
    targets = resolve_dm_scoring_targets(profile.Employee_id, year=year, month=month, profile=profile)
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
            "digital_media_target_count": targets["digital_media_target_count"],
            "digital_content_target_count": targets["digital_content_target_count"],
        },
        "max_main_points": {
            "digital_media": targets["digital_media_max_main_points"],
            "digital_content": targets["digital_content_max_main_points"],
            "dm_work_total": targets["digital_media_max_main_points"] + targets["digital_content_max_main_points"],
        },
    }


def user_can_view_dm_targets(user, get_user_role) -> bool:
    if not user or not user.is_authenticated:
        return False
    return (get_user_role(user) or "").strip() in DM_TARGET_VIEW_ROLES


def user_can_edit_dm_targets(user, get_user_role) -> bool:
    if not user or not user.is_authenticated:
        return False
    return (get_user_role(user) or "").strip() in DM_TARGET_EDIT_ROLES


__all__ = [
    "DM_FUNCTIONS",
    "default_dm_scoring_targets",
    "is_dm_profile",
    "dm_profiles_queryset",
    "resolve_dm_scoring_targets",
    "build_dm_target_payload",
    "user_can_view_dm_targets",
    "user_can_edit_dm_targets",
    "DEFAULT_DIGITAL_MEDIA_TARGET_COUNT",
    "DEFAULT_DIGITAL_CONTENT_TARGET_COUNT",
    "DM_MEDIA_MAX_MAIN_POINTS",
    "DM_CONTENT_MAX_MAIN_POINTS",
]

