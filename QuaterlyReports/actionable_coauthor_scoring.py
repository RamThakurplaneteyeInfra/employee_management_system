"""
Co-author actionable entry performance points from FunctionsEntries.

Scoring rules (per calendar month):
- Each entry where the user is co_author and approved_by_coauthor=True: +2 points.
- Monthly main_score capped at 10; points above 10 go to monthly_bonus.
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

POINTS_PER_APPROVED_ENTRY = Decimal("2")
MONTHLY_MAX_MAIN_POINTS = Decimal("10")

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


def _approved_entries_for_coauthor(user, year: int, month: int | None, quarter: int | None):
    qs = FunctionsEntries.objects.filter(
        co_author=user,
        approved_by_coauthor=True,
    ).select_related("Creator__accounts_profile")
    if month is not None:
        qs = qs.filter(date__year=year, date__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(date__year=year)
    return qs.order_by("date", "time", "id")


def _month_scores_for_count(count: int) -> tuple[Decimal, Decimal, Decimal]:
    if count <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    raw = POINTS_PER_APPROVED_ENTRY * count
    main = min(raw, MONTHLY_MAX_MAIN_POINTS)
    bonus = raw - main
    return main, bonus, main + bonus


def _creator_display(entry) -> str:
    creator = getattr(entry, "Creator", None)
    if creator is None:
        return ""
    profile = getattr(creator, "accounts_profile", None)
    if profile and getattr(profile, "Name", None):
        return profile.Name
    return creator.username


def _build_events_for_month(entries) -> list[dict]:
    events = []
    main_so_far = Decimal("0")
    for entry in entries:
        pts = POINTS_PER_APPROVED_ENTRY
        if main_so_far + pts <= MONTHLY_MAX_MAIN_POINTS:
            points_type = "main"
            main_so_far += pts
        else:
            points_type = "bonus"
        events.append(
            {
                "entry_id": entry.pk,
                "creator_id": entry.Creator_id,
                "creator_name": _creator_display(entry),
                "date": entry.date.isoformat() if entry.date else None,
                "points_type": points_type,
                "points": float(pts),
            }
        )
    return events


def build_actionable_coauthor_points(
    user, year: int, month: int | None = None, quarter: int | None = None
) -> dict:
    monthly_entries: dict[tuple[int, int], list] = defaultdict(list)
    for entry in _approved_entries_for_coauthor(user, year, month, quarter):
        if entry.date is None:
            continue
        monthly_entries[(entry.date.year, entry.date.month)].append(entry)

    months_in_period = _months_in_period(year, month, quarter)
    main_total = Decimal("0")
    bonus_total = Decimal("0")
    approved_total = 0
    events: list[dict] = []

    for month_key in months_in_period:
        entries = monthly_entries.get(month_key, [])
        count = len(entries)
        approved_total += count
        month_main, month_bonus, _ = _month_scores_for_count(count)
        main_total += month_main
        bonus_total += month_bonus
        if month is not None or count > 0:
            events.extend(_build_events_for_month(entries))

    total_points = main_total + bonus_total
    months_count = len(months_in_period)
    max_main = float(MONTHLY_MAX_MAIN_POINTS * months_count)

    profile = Profile.objects.filter(Employee_id=user).select_related("Role").first()
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)

    return {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "points_per_approved_entry": float(POINTS_PER_APPROVED_ENTRY),
        "monthly_max_main_points": float(MONTHLY_MAX_MAIN_POINTS),
        "max_main_points": max_main,
        "max_bonus_points": None,
        "max_points": max_main,
        "months_in_period": months_count,
        "counts": {"approved_entries": approved_total},
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
        "events": events,
    }


__all__ = [
    "build_actionable_coauthor_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
    "POINTS_PER_APPROVED_ENTRY",
    "MONTHLY_MAX_MAIN_POINTS",
]
