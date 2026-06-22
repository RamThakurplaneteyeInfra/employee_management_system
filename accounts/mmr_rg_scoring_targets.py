"""
Resolve MMR/RG per-employee, per-month scoring targets with system defaults as fallback.
"""
from __future__ import annotations

from decimal import Decimal

from .models import MmrRgScoringTarget, Profile

MMR_RG_FUNCTIONS = frozenset({"MMR", "RG"})
DEFAULT_CUSTOMER_PANEL_TARGET_AMOUNT = Decimal("500000")
DEFAULT_PROPOSAL_TARGET_AMOUNT = Decimal("5000000")
DEFAULT_PROFILE_COUNT_TARGET = 5
DEFAULT_PROFORMA_TARGET_AMOUNT = Decimal("1100000")
CUSTOMER_PANEL_MAX_MAIN_POINTS = Decimal("40")

MMR_RG_TARGET_VIEW_ROLES = frozenset({"HR", "Hr", "MD"})
MMR_RG_TARGET_EDIT_ROLES = frozenset({"MD"})


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


def is_mmr_rg_profile(profile: Profile | None) -> bool:
    return bool(_profile_function_names_upper(profile) & MMR_RG_FUNCTIONS)


def default_mmr_rg_scoring_targets() -> dict:
    return {
        "customer_panel_target_amount": DEFAULT_CUSTOMER_PANEL_TARGET_AMOUNT,
        "proposal_target_amount": DEFAULT_PROPOSAL_TARGET_AMOUNT,
        "profile_count_target": DEFAULT_PROFILE_COUNT_TARGET,
        "proforma_target_amount": DEFAULT_PROFORMA_TARGET_AMOUNT,
        "customer_panel_max_main_points": float(CUSTOMER_PANEL_MAX_MAIN_POINTS),
    }


def parse_target_year_month(raw_year, raw_month) -> tuple[int, int] | None:
    try:
        year = int(raw_year)
        month = int(raw_month)
    except (TypeError, ValueError):
        return None
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        return None
    return year, month


def _serialize_target_row(record: MmrRgScoringTarget | None) -> dict | None:
    if record is None:
        return None
    return {
        "year": record.year,
        "month": record.month,
        "customer_panel_target_amount": (
            float(record.customer_panel_target_amount)
            if record.customer_panel_target_amount is not None
            else None
        ),
        "proposal_target_amount": (
            float(record.proposal_target_amount)
            if record.proposal_target_amount is not None
            else None
        ),
        "profile_count_target": record.profile_count_target,
        "proforma_target_amount": (
            float(record.proforma_target_amount)
            if record.proforma_target_amount is not None
            else None
        ),
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "set_by": record.set_by_id,
    }


def _custom_fields_from_record(custom: MmrRgScoringTarget | None) -> set[str]:
    custom_fields: set[str] = set()
    if custom is None:
        return custom_fields
    if custom.customer_panel_target_amount is not None:
        custom_fields.add("customer_panel_target_amount")
    if custom.proposal_target_amount is not None:
        custom_fields.add("proposal_target_amount")
    if custom.profile_count_target is not None:
        custom_fields.add("profile_count_target")
    if custom.proforma_target_amount is not None:
        custom_fields.add("proforma_target_amount")
    return custom_fields


def _effective_targets_from_record(custom: MmrRgScoringTarget | None, defaults: dict) -> dict:
    return {
        "customer_panel_target_amount": (
            custom.customer_panel_target_amount
            if custom is not None and custom.customer_panel_target_amount is not None
            else defaults["customer_panel_target_amount"]
        ),
        "proposal_target_amount": (
            custom.proposal_target_amount
            if custom is not None and custom.proposal_target_amount is not None
            else defaults["proposal_target_amount"]
        ),
        "profile_count_target": (
            custom.profile_count_target
            if custom is not None and custom.profile_count_target is not None
            else defaults["profile_count_target"]
        ),
        "proforma_target_amount": (
            custom.proforma_target_amount
            if custom is not None and custom.proforma_target_amount is not None
            else defaults["proforma_target_amount"]
        ),
    }


def load_mmr_rg_targets_for_months(
    profile: Profile | None, month_keys: list[tuple[int, int]]
) -> dict[tuple[int, int], MmrRgScoringTarget]:
    if profile is None or not month_keys:
        return {}
    month_key_set = set(month_keys)
    years = {year for year, _ in month_key_set}
    rows = MmrRgScoringTarget.objects.filter(profile=profile, year__in=years)
    return {
        (row.year, row.month): row
        for row in rows
        if (row.year, row.month) in month_key_set
    }


def resolve_mmr_rg_scoring_targets(
    user,
    *,
    year: int | None = None,
    month: int | None = None,
    profile: Profile | None = None,
    custom: MmrRgScoringTarget | None = None,
) -> dict:
    defaults = default_mmr_rg_scoring_targets()
    if profile is None:
        profile = (
            Profile.objects.filter(Employee_id=user)
            .prefetch_related("functions")
            .first()
        )
    eligible = is_mmr_rg_profile(profile)

    if custom is None and profile is not None and year is not None and month is not None:
        custom = MmrRgScoringTarget.objects.filter(
            profile=profile, year=year, month=month
        ).first()

    effective = _effective_targets_from_record(custom, defaults)
    custom_fields = _custom_fields_from_record(custom)

    return {
        "eligible": eligible,
        "year": year,
        "month": month,
        "defaults": {
            key: (
                float(defaults[key])
                if isinstance(defaults[key], Decimal)
                else defaults[key]
            )
            for key in (
                "customer_panel_target_amount",
                "proposal_target_amount",
                "profile_count_target",
                "proforma_target_amount",
                "customer_panel_max_main_points",
            )
        },
        "custom": _serialize_target_row(custom),
        "custom_fields": sorted(custom_fields),
        "is_customized": bool(custom_fields),
        "customer_panel_target_amount": effective["customer_panel_target_amount"],
        "proposal_target_amount": effective["proposal_target_amount"],
        "profile_count_target": effective["profile_count_target"],
        "proforma_target_amount": effective["proforma_target_amount"],
    }


def mmr_rg_profiles_queryset():
    return (
        Profile.objects.filter(Employee_id__is_active=True, functions__function__in=list(MMR_RG_FUNCTIONS))
        .select_related("Role", "Employee_id")
        .prefetch_related("functions")
        .distinct()
        .order_by("Name")
    )


def build_mmr_rg_target_payload(profile: Profile, year: int, month: int) -> dict:
    targets = resolve_mmr_rg_scoring_targets(profile.Employee_id, year=year, month=month, profile=profile)
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
            "customer_panel_target_amount": float(targets["customer_panel_target_amount"]),
            "proposal_target_amount": float(targets["proposal_target_amount"]),
            "profile_count_target": targets["profile_count_target"],
            "proforma_target_amount": float(targets["proforma_target_amount"]),
        },
    }


def user_can_view_mmr_rg_targets(user, get_user_role) -> bool:
    if not user or not user.is_authenticated:
        return False
    return (get_user_role(user) or "").strip() in MMR_RG_TARGET_VIEW_ROLES


def user_can_edit_mmr_rg_targets(user, get_user_role) -> bool:
    if not user or not user.is_authenticated:
        return False
    return (get_user_role(user) or "").strip() in MMR_RG_TARGET_EDIT_ROLES
