"""
Meeting performance points from BookSlot participation (SlotMembers + creator).

Scoring rules:
- Indoor meeting: +0.25 per meeting, main capped at 3.5 per calendar month
- Outdoor room (name "Outdoor", case-insensitive): +0.5 per meeting, main capped at 3.5 per month
- Points above each monthly cap count as monthly_bonus (not lost)
- Total monthly main cap: 7.0 (3.5 indoor + 3.5 outdoor); quarter/year sums monthly main + bonus
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile

from .models import BookSlot

User = get_user_model()

POINTS_INDOOR_MEETING = Decimal("0.25")
POINTS_OUTDOOR_MEETING = Decimal("0.5")
MONTHLY_MAX_INDOOR_POINTS = Decimal("3.5")
MONTHLY_MAX_OUTDOOR_POINTS = Decimal("3.5")
MONTHLY_MAX_MEETING_POINTS = MONTHLY_MAX_INDOOR_POINTS + MONTHLY_MAX_OUTDOOR_POINTS

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


def _is_outdoor_room(room) -> bool:
    if room is None:
        return False
    return str(getattr(room, "name", "") or "").strip().lower() == "outdoor"


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


def _slots_for_user_period(user, year: int, month: int | None, quarter: int | None):
    qs = (
        BookSlot.objects.filter(Q(slotmembers__member=user) | Q(created_by=user))
        .select_related("room", "status")
        .exclude(status__status_name__iexact="Cancelled")
        .distinct()
    )
    if month is not None:
        qs = qs.filter(date__year=year, date__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(date__year=year)
    return qs.order_by("date", "id")


def _split_main_and_bonus(gross: Decimal, cap: Decimal) -> tuple[Decimal, Decimal]:
    main = min(gross, cap)
    bonus = gross - main
    return main, bonus


def build_meeting_points(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    monthly_counts: dict[tuple[int, int], dict[str, int]] = defaultdict(
        lambda: {"indoor_meetings": 0, "outdoor_meetings": 0}
    )

    for slot in _slots_for_user_period(user, year, month, quarter):
        if slot.date is None:
            continue
        key = (slot.date.year, slot.date.month)
        if _is_outdoor_room(slot.room):
            monthly_counts[key]["outdoor_meetings"] += 1
        else:
            monthly_counts[key]["indoor_meetings"] += 1

    months_in_period = _months_in_period(year, month, quarter)
    indoor_total = 0
    outdoor_total = 0
    gross_indoor_points = Decimal("0")
    gross_outdoor_points = Decimal("0")
    main_indoor_points = Decimal("0")
    main_outdoor_points = Decimal("0")
    bonus_indoor_points = Decimal("0")
    bonus_outdoor_points = Decimal("0")

    for month_key in months_in_period:
        counts = monthly_counts.get(month_key, {"indoor_meetings": 0, "outdoor_meetings": 0})
        indoor = counts["indoor_meetings"]
        outdoor = counts["outdoor_meetings"]
        indoor_total += indoor
        outdoor_total += outdoor
        month_indoor_pts = Decimal(indoor) * POINTS_INDOOR_MEETING
        month_outdoor_pts = Decimal(outdoor) * POINTS_OUTDOOR_MEETING
        gross_indoor_points += month_indoor_pts
        gross_outdoor_points += month_outdoor_pts
        month_main_indoor, month_bonus_indoor = _split_main_and_bonus(
            month_indoor_pts, MONTHLY_MAX_INDOOR_POINTS
        )
        month_main_outdoor, month_bonus_outdoor = _split_main_and_bonus(
            month_outdoor_pts, MONTHLY_MAX_OUTDOOR_POINTS
        )
        main_indoor_points += month_main_indoor
        main_outdoor_points += month_main_outdoor
        bonus_indoor_points += month_bonus_indoor
        bonus_outdoor_points += month_bonus_outdoor

    gross_total = gross_indoor_points + gross_outdoor_points
    main_total = main_indoor_points + main_outdoor_points
    bonus_total = bonus_indoor_points + bonus_outdoor_points
    months_count = len(months_in_period)
    max_main_points = float(MONTHLY_MAX_MEETING_POINTS * months_count)
    max_indoor_points = float(MONTHLY_MAX_INDOOR_POINTS * months_count)
    max_outdoor_points = float(MONTHLY_MAX_OUTDOOR_POINTS * months_count)

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
        "points_per_indoor_meeting": float(POINTS_INDOOR_MEETING),
        "points_per_outdoor_meeting": float(POINTS_OUTDOOR_MEETING),
        "max_main_points": max_main_points,
        "max_bonus_points": None,
        "max_points": max_main_points,
        "max_indoor_points": max_indoor_points,
        "max_outdoor_points": max_outdoor_points,
        "monthly_max_points": float(MONTHLY_MAX_MEETING_POINTS),
        "monthly_max_indoor_points": float(MONTHLY_MAX_INDOOR_POINTS),
        "monthly_max_outdoor_points": float(MONTHLY_MAX_OUTDOOR_POINTS),
        "months_in_period": months_count,
        "counts": {
            "indoor_meetings": indoor_total,
            "outdoor_meetings": outdoor_total,
            "total_meetings": indoor_total + outdoor_total,
        },
        "points": {
            "indoor_gross": float(gross_indoor_points),
            "outdoor_gross": float(gross_outdoor_points),
            "indoor": float(main_indoor_points),
            "outdoor": float(main_outdoor_points),
            "indoor_bonus": float(bonus_indoor_points),
            "outdoor_bonus": float(bonus_outdoor_points),
            "raw_total": float(gross_total),
        },
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(main_total + bonus_total, 2)),
    }


__all__ = [
    "build_meeting_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
]
