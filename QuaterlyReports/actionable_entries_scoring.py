"""
Creator actionable entry performance points from FunctionsEntries.

Applies only when the employee's Profile.functions contains any of:
- NPD
- HC
- IP

Scoring rules (per calendar month):
- Each actionable entry where the user is Creator and final_Status == COMPLETED: +4 points.
- Monthly main_score capped at 20; points above 20 go to monthly_bonus.
- Quarter / year totals sum monthly main_score and monthly_bonus across months in the period.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile

from .models import FunctionsEntries

User = get_user_model()

POINTS_PER_COMPLETED_ENTRY = Decimal("4")
MONTHLY_MAX_MAIN_POINTS = Decimal("20")

SPECIAL_FUNCTIONS = frozenset({"NPD", "HC", "IP"})

_FY_QUARTER_MONTHS = {
    1: (4, 5, 6),
    2: (7, 8, 9),
    3: (10, 11, 12),
    4: (1, 2, 3),
}


def _fy_quarter_date_filter(year: int, quarter: int) -> Q:
    months = _FY_QUARTER_MONTHS[quarter]
    if quarter == 4:
        return Q(date__year=year + 1, date__month__in=months)
    return Q(date__year=year, date__month__in=months)


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


def _is_special_user(profile: Profile | None) -> bool:
    return bool(_profile_function_names_upper(profile) & SPECIAL_FUNCTIONS)


def _completed_entries_for_creator(user, year: int, month: int | None, quarter: int | None):
    qs = (
        FunctionsEntries.objects.filter(
            Creator=user,
            final_Status__status_name="COMPLETED",
        )
        .select_related("final_Status")
        .order_by("date", "time", "id")
    )
    if month is not None:
        qs = qs.filter(date__year=year, date__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(date__year=year)
    return qs


def _build_events_for_month(entries) -> list[dict]:
    events = []
    main_so_far = Decimal("0")
    for entry in entries:
        pts = POINTS_PER_COMPLETED_ENTRY
        if main_so_far + pts <= MONTHLY_MAX_MAIN_POINTS:
            points_type = "main"
            main_so_far += pts
        else:
            points_type = "bonus"
        events.append(
            {
                "entry_id": entry.pk,
                "date": entry.date.isoformat() if entry.date else None,
                "points_type": points_type,
                "points": float(pts),
            }
        )
    return events


def build_actionable_entries_points(
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

    eligible = _is_special_user(profile)
    months_in_period = _months_in_period(year, month, quarter)
    months_count = len(months_in_period)

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "eligible_functions": sorted(list(_profile_function_names_upper(profile) & SPECIAL_FUNCTIONS)),
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "points_per_completed_entry": float(POINTS_PER_COMPLETED_ENTRY),
        "monthly_max_main_points": float(MONTHLY_MAX_MAIN_POINTS),
        "max_main_points": float(MONTHLY_MAX_MAIN_POINTS * months_count),
        "max_bonus_points": None,
        "max_points": float(MONTHLY_MAX_MAIN_POINTS * months_count),
        "months_in_period": months_count,
        "counts": {"completed_entries": 0},
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "events": [],
    }

    if not eligible:
        return base

    monthly_entries: dict[tuple[int, int], list] = defaultdict(list)
    for entry in _completed_entries_for_creator(user, year, month, quarter):
        if entry.date is None:
            continue
        monthly_entries[(entry.date.year, entry.date.month)].append(entry)

    main_total = Decimal("0")
    bonus_total = Decimal("0")
    completed_total = 0
    events: list[dict] = []

    for month_key in months_in_period:
        entries = monthly_entries.get(month_key, [])
        count = len(entries)
        completed_total += count
        raw = POINTS_PER_COMPLETED_ENTRY * count
        month_main = min(raw, MONTHLY_MAX_MAIN_POINTS)
        month_bonus = raw - month_main
        main_total += month_main
        bonus_total += month_bonus
        if month is not None or count > 0:
            events.extend(_build_events_for_month(entries))

    total_points = main_total + bonus_total
    return {
        **base,
        "counts": {"completed_entries": completed_total},
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
        "events": events,
    }


__all__ = [
    "build_actionable_entries_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
    "POINTS_PER_COMPLETED_ENTRY",
    "MONTHLY_MAX_MAIN_POINTS",
]

