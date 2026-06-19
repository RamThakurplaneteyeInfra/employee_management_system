"""
Client profile performance points from ClientProfile (created_by).

Applies only when the employee's Profile.functions contains MMR or RG.

Monthly scoring (30 points total, 10 per component):
- Proposal stage product_value: ₹50,00,000 = 10 main; excess = bonus.
- Profile count (created in month): 5 profiles = 10 main; excess = bonus.
- Proforma stage product_value: ₹11,00,000 = 10 main; excess = bonus.

Quarter / year totals sum monthly main_score and monthly_bonus across months in the period.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile
from CustomerPanel.customer_panel_scoring import MMR_RG_FUNCTIONS

from .models import ClientProfile

User = get_user_model()

PROPOSAL_STAGE_NAME = "Proposal"
PROFORMA_STAGE_NAME = "Proforma"

MONTHLY_MAX_COMPONENT_POINTS = Decimal("10")
MONTHLY_MAX_TOTAL_POINTS = MONTHLY_MAX_COMPONENT_POINTS * 3

PROPOSAL_TARGET_AMOUNT = Decimal("5000000")
PROFORMA_TARGET_AMOUNT = Decimal("1100000")
PROFILE_COUNT_TARGET = 5

_FY_QUARTER_MONTHS = {
    1: (4, 5, 6),
    2: (7, 8, 9),
    3: (10, 11, 12),
    4: (1, 2, 3),
}


def _fy_quarter_date_filter(year: int, quarter: int) -> Q:
    months = _FY_QUARTER_MONTHS[quarter]
    if quarter == 4:
        return Q(created_at__year=year + 1, created_at__month__in=months)
    return Q(created_at__year=year, created_at__month__in=months)


def _period_label(year: int, month: int | None, quarter: int | None) -> str:
    if month is not None:
        return f"{year}-{month:02d}"
    if quarter is not None:
        return f"FY{year}-Q{quarter}"
    return str(year)


def _period_range_label(year: int, month: int | None, quarter: int | None) -> str | None:
    if month is not None:
        return f"{year}-{month:02d}"
    if quarter is None:
        return None
    if quarter == 1:
        return f"{year}-04 to {year}-06"
    if quarter == 2:
        return f"{year}-07 to {year}-09"
    if quarter == 3:
        return f"{year}-10 to {year}-12"
    return f"{year + 1}-01 to {year + 1}-03"


def _period_type(month: int | None, quarter: int | None) -> str:
    if month is not None:
        return "month"
    if quarter is not None:
        return "quarter"
    return "year"


def _months_in_period(year: int, month: int | None, quarter: int | None) -> list[tuple[int, int]]:
    if month is not None:
        return [(year, month)]
    if quarter is not None:
        cal_year = year + 1 if quarter == 4 else year
        return [(cal_year, m) for m in _FY_QUARTER_MONTHS[quarter]]
    return [(year, m) for m in range(1, 13)]


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


def _is_mmr_rg_user(profile: Profile | None) -> bool:
    return bool(_profile_function_names_upper(profile) & MMR_RG_FUNCTIONS)


def _profile_month_key(profile: ClientProfile) -> tuple[int, int] | None:
    created = profile.created_at
    if created is None:
        return None
    if timezone.is_aware(created):
        created = timezone.localtime(created)
    return created.year, created.month


def _stage_name(profile: ClientProfile) -> str:
    status = getattr(profile, "status", None)
    return (getattr(status, "name", None) or "").strip()


def _profiles_for_creator(user, year: int, month: int | None, quarter: int | None):
    qs = ClientProfile.objects.filter(created_by=user).select_related("status").order_by("created_at", "id")
    if month is not None:
        qs = qs.filter(created_at__year=year, created_at__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(created_at__year=year)
    return qs


def _month_amount_for_stage(profiles, stage_name: str) -> Decimal:
    stage_key = stage_name.strip().lower()
    total = Decimal("0")
    for profile in profiles:
        if _stage_name(profile).lower() != stage_key:
            continue
        if profile.product_value is not None:
            total += profile.product_value
    return total


def _month_scores_for_amount(amount: Decimal, target_amount: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    if amount <= 0 or target_amount <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    raw_points = (amount / target_amount) * MONTHLY_MAX_COMPONENT_POINTS
    main = min(raw_points, MONTHLY_MAX_COMPONENT_POINTS)
    bonus = raw_points - main
    return main, bonus, main + bonus


def _month_scores_for_count(count: int) -> tuple[Decimal, Decimal, Decimal]:
    if count <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    raw_points = (Decimal(count) / Decimal(PROFILE_COUNT_TARGET)) * MONTHLY_MAX_COMPONENT_POINTS
    main = min(raw_points, MONTHLY_MAX_COMPONENT_POINTS)
    bonus = raw_points - main
    return main, bonus, main + bonus


def _component_payload(
    *,
    key: str,
    label: str,
    main: Decimal,
    bonus: Decimal,
    counts: dict,
) -> dict:
    total = main + bonus
    return {
        "key": key,
        "label": label,
        "main_score": float(round(main, 2)),
        "monthly_bonus": float(round(bonus, 2)),
        "total_points": float(round(total, 2)),
        "max_main_points": float(MONTHLY_MAX_COMPONENT_POINTS),
        "counts": counts,
    }


def build_client_profile_points(
    user, year: int, month: int | None = None, quarter: int | None = None
) -> dict:
    profile = (
        Profile.objects.filter(Employee_id=user)
        .select_related("Role")
        .prefetch_related("functions")
        .first()
    )
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)

    eligible = _is_mmr_rg_user(profile)
    months_in_period = _months_in_period(year, month, quarter)
    months_count = len(months_in_period)

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "eligible_functions": sorted(list(_profile_function_names_upper(profile) & MMR_RG_FUNCTIONS)),
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "monthly_max_points": float(MONTHLY_MAX_TOTAL_POINTS),
        "monthly_max_component_points": float(MONTHLY_MAX_COMPONENT_POINTS),
        "max_main_points": float(MONTHLY_MAX_TOTAL_POINTS * months_count),
        "max_bonus_points": None,
        "max_points": float(MONTHLY_MAX_TOTAL_POINTS * months_count),
        "months_in_period": months_count,
        "proposal_target_amount": float(PROPOSAL_TARGET_AMOUNT),
        "proforma_target_amount": float(PROFORMA_TARGET_AMOUNT),
        "profile_count_target": PROFILE_COUNT_TARGET,
        "components": {
            "proposal_value": _component_payload(
                key="proposal_value",
                label="Proposal stage value",
                main=Decimal("0"),
                bonus=Decimal("0"),
                counts={"profiles": 0, "total_amount": 0.0},
            ),
            "profile_count": _component_payload(
                key="profile_count",
                label="Profiles added",
                main=Decimal("0"),
                bonus=Decimal("0"),
                counts={"profiles": 0},
            ),
            "proforma_value": _component_payload(
                key="proforma_value",
                label="Proforma stage value",
                main=Decimal("0"),
                bonus=Decimal("0"),
                counts={"profiles": 0, "total_amount": 0.0},
            ),
        },
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "events": [],
    }

    if not eligible:
        return base

    monthly_profiles: dict[tuple[int, int], list] = defaultdict(list)
    for client_profile in _profiles_for_creator(user, year, month, quarter):
        month_key = _profile_month_key(client_profile)
        if month_key is None:
            continue
        monthly_profiles[month_key].append(client_profile)

    proposal_main = Decimal("0")
    proposal_bonus = Decimal("0")
    proposal_profile_count = 0
    proposal_amount_total = Decimal("0")

    count_main = Decimal("0")
    count_bonus = Decimal("0")
    profiles_added_total = 0

    proforma_main = Decimal("0")
    proforma_bonus = Decimal("0")
    proforma_profile_count = 0
    proforma_amount_total = Decimal("0")

    events: list[dict] = []

    for month_key in months_in_period:
        profiles = monthly_profiles.get(month_key, [])
        y, m = month_key

        proposal_amount = _month_amount_for_stage(profiles, PROPOSAL_STAGE_NAME)
        proposal_profiles = sum(1 for p in profiles if _stage_name(p).lower() == PROPOSAL_STAGE_NAME.lower())
        p_main, p_bonus, _ = _month_scores_for_amount(proposal_amount, PROPOSAL_TARGET_AMOUNT)
        proposal_main += p_main
        proposal_bonus += p_bonus
        proposal_profile_count += proposal_profiles
        proposal_amount_total += proposal_amount

        profile_count = len(profiles)
        c_main, c_bonus, _ = _month_scores_for_count(profile_count)
        count_main += c_main
        count_bonus += c_bonus
        profiles_added_total += profile_count

        proforma_amount = _month_amount_for_stage(profiles, PROFORMA_STAGE_NAME)
        proforma_profiles = sum(1 for p in profiles if _stage_name(p).lower() == PROFORMA_STAGE_NAME.lower())
        f_main, f_bonus, _ = _month_scores_for_amount(proforma_amount, PROFORMA_TARGET_AMOUNT)
        proforma_main += f_main
        proforma_bonus += f_bonus
        proforma_profile_count += proforma_profiles
        proforma_amount_total += proforma_amount

        if month is not None or profiles:
            events.append(
                {
                    "event_type": "monthly_score",
                    "month": f"{y}-{m:02d}",
                    "proposal_value": {
                        "profiles": proposal_profiles,
                        "total_amount": float(round(proposal_amount, 2)),
                        "main_score": float(round(p_main, 2)),
                        "monthly_bonus": float(round(p_bonus, 2)),
                    },
                    "profile_count": {
                        "profiles": profile_count,
                        "main_score": float(round(c_main, 2)),
                        "monthly_bonus": float(round(c_bonus, 2)),
                    },
                    "proforma_value": {
                        "profiles": proforma_profiles,
                        "total_amount": float(round(proforma_amount, 2)),
                        "main_score": float(round(f_main, 2)),
                        "monthly_bonus": float(round(f_bonus, 2)),
                    },
                }
            )

    main_total = proposal_main + count_main + proforma_main
    bonus_total = proposal_bonus + count_bonus + proforma_bonus
    total_points = main_total + bonus_total

    return {
        **base,
        "components": {
            "proposal_value": _component_payload(
                key="proposal_value",
                label="Proposal stage value",
                main=proposal_main,
                bonus=proposal_bonus,
                counts={
                    "profiles": proposal_profile_count,
                    "total_amount": float(round(proposal_amount_total, 2)),
                },
            ),
            "profile_count": _component_payload(
                key="profile_count",
                label="Profiles added",
                main=count_main,
                bonus=count_bonus,
                counts={"profiles": profiles_added_total},
            ),
            "proforma_value": _component_payload(
                key="proforma_value",
                label="Proforma stage value",
                main=proforma_main,
                bonus=proforma_bonus,
                counts={
                    "profiles": proforma_profile_count,
                    "total_amount": float(round(proforma_amount_total, 2)),
                },
            ),
        },
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
        "events": events,
    }


__all__ = [
    "build_client_profile_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
    "PROPOSAL_TARGET_AMOUNT",
    "PROFORMA_TARGET_AMOUNT",
    "PROFILE_COUNT_TARGET",
    "MONTHLY_MAX_COMPONENT_POINTS",
    "MONTHLY_MAX_TOTAL_POINTS",
]
