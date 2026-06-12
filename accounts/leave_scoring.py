"""
Monthly leave event counts and performance points from LeaveApplicationData.

Scoring rules:
- Monthly free allowance of 2.0 day-units per calendar month (half day = 0.5, full day = 1.0).
  Example: 2 half days + 1 full day uses the full allowance (0.5 + 0.5 + 1.0 = 2.0).
- Half day (MD-approved, after allowance exhausted): -0.5
- Full day (MD-approved, after allowance exhausted): -1.0
- No MD-approved half/full leave in a calendar month: +2.0 bonus (mirrors monthly allowance).
- Unapproved absent scoring is temporarily disabled (see ENABLE_UNAPPROVED_ABSENT_SCORING).
"""
from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import LeaveApplicationData, Profile

User = get_user_model()

POINTS_HALF_DAY = Decimal("-0.5")
POINTS_FULL_DAY = Decimal("-1")
POINTS_UNAPPROVED_ABSENT = Decimal("-1.5")
ENABLE_UNAPPROVED_ABSENT_SCORING = False
MONTHLY_FREE_LEAVE_ALLOWANCE = Decimal("2")
NO_LEAVE_MONTHLY_BONUS = Decimal("2")
HALF_DAY_UNITS = Decimal("0.5")
FULL_DAY_UNITS = Decimal("1")

# Financial year quarters (April start). `year` = FY start calendar year (April year).
_FY_QUARTER_MONTHS = {
    1: (4, 5, 6),   # Apr–Jun
    2: (7, 8, 9),   # Jul–Sep
    3: (10, 11, 12),  # Oct–Dec
    4: (1, 2, 3),   # Jan–Mar (next calendar year)
}


def _fy_quarter_date_filter(year: int, quarter: int) -> Q:
    months = _FY_QUARTER_MONTHS[quarter]
    if quarter == 4:
        return Q(start_date__year=year + 1, start_date__month__in=months)
    return Q(start_date__year=year, start_date__month__in=months)


def _applied_date(application: LeaveApplicationData) -> date:
    if application.applied_at:
        return application.applied_at.astimezone(timezone.get_current_timezone()).date()
    return application.application_date


def _is_md_approved(application: LeaveApplicationData) -> bool:
    md = getattr(application, "MD_approval", None)
    return bool(md and getattr(md, "name", None) == "Approved")


def _leave_type_name(application: LeaveApplicationData) -> str:
    lt = getattr(application, "leave_type", None)
    return (getattr(lt, "name", None) or "").strip()


def _is_late_application(application: LeaveApplicationData) -> bool:
    return _applied_date(application) > application.start_date


def _duration_whole_days(application: LeaveApplicationData) -> int:
    raw = float(application.duration_of_days or 1)
    return max(1, int(math.ceil(raw)))


def _month_key(start_date: date) -> tuple[int, int]:
    return start_date.year, start_date.month


def _leave_allowance_units(event_type: str) -> Decimal:
    return HALF_DAY_UNITS if event_type == "half_day" else FULL_DAY_UNITS


def _apply_on_time_approved_leave_scoring(
    application: LeaveApplicationData,
    base_event: dict,
    counts: dict,
    penalized: dict,
    events: list,
    *,
    event_type: str,
    points_value: Decimal,
    monthly_allowance_used: dict[tuple[int, int], Decimal],
):
    count_key = "half_day" if event_type == "half_day" else "full_day"
    counts[count_key] += 1

    key = _month_key(application.start_date)
    used = monthly_allowance_used.get(key, Decimal("0"))
    units = _leave_allowance_units(event_type)
    if used + units <= MONTHLY_FREE_LEAVE_ALLOWANCE:
        monthly_allowance_used[key] = used + units
        counts["waived"] += 1
        counts["waived_units"] += float(units)
        events.append(
            {
                **base_event,
                "event_type": event_type,
                "points": 0.0,
                "waived": True,
                "allowance_units": float(units),
                "allowance_used_after": float(used + units),
            }
        )
        return

    penalized[count_key] += 1
    events.append(
        {
            **base_event,
            "event_type": event_type,
            "points": float(points_value),
            "waived": False,
            "allowance_units": float(units),
            "allowance_used_after": float(used),
        }
    )


def _apply_late_leave_scoring(
    application: LeaveApplicationData,
    base_event: dict,
    counts: dict,
    penalized: dict,
    events: list,
):
    """
  Late / unapproved: 1× unapproved (-1.5) plus (duration - 1) full-day units (-1 each).
  Example: 3-day late leave → full_day=2, unapproved_absent=1 → -3.5 total.
    """
    whole_days = _duration_whole_days(application)
    extra_full_days = max(0, whole_days - 1)
    if extra_full_days:
        penalized["full_day"] += extra_full_days
    counts["unapproved_absent"] += 1
    total = float(extra_full_days * POINTS_FULL_DAY + POINTS_UNAPPROVED_ABSENT)
    events.append(
        {
            **base_event,
            "event_type": "unapproved_absent",
            "duration_days": whole_days,
            "full_day_units": extra_full_days,
            "unapproved_units": 1,
            "points": total,
        }
    )


def _applications_for_period(user, year: int, month: int | None, quarter: int | None):
    qs = LeaveApplicationData.objects.filter(applicant=user).select_related(
        "leave_type", "MD_approval"
    )
    if month is not None:
        qs = qs.filter(start_date__year=year, start_date__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(start_date__year=year)
    return qs.order_by("start_date", "id")


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
        months = _FY_QUARTER_MONTHS[quarter]
        cal_year = year + 1 if quarter == 4 else year
        return [(cal_year, m) for m in months]
    return [(year, m) for m in range(1, 13)]


def _apply_no_leave_month_bonuses(
    months_in_period: list[tuple[int, int]],
    months_with_half_full: set[tuple[int, int]],
    events: list,
) -> tuple[float, int]:
    bonus_total = Decimal("0")
    bonus_month_count = 0
    for month_key in months_in_period:
        if month_key in months_with_half_full:
            continue
        bonus_total += NO_LEAVE_MONTHLY_BONUS
        bonus_month_count += 1
        y, m = month_key
        events.append(
            {
                "event_type": "no_leave_bonus",
                "month": f"{y}-{m:02d}",
                "points": float(NO_LEAVE_MONTHLY_BONUS),
            }
        )
    return float(bonus_total), bonus_month_count


def build_leave_points(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    counts = {
        "half_day": 0,
        "full_day": 0,
        "unapproved_absent": 0,
        "waived": 0,
        "waived_units": 0.0,
        "no_leave_months": 0,
    }
    penalized = {
        "half_day": 0,
        "full_day": 0,
    }
    events = []
    monthly_allowance_used: dict[tuple[int, int], Decimal] = {}
    months_with_half_full: set[tuple[int, int]] = set()

    for application in _applications_for_period(user, year, month, quarter):
        lt_name = _leave_type_name(application)
        md_approved = _is_md_approved(application)
        base_event = {
            "leave_id": application.id,
            "start_date": application.start_date.isoformat(),
            "applied_date": _applied_date(application).isoformat(),
            "leave_type": lt_name or None,
        }

        if ENABLE_UNAPPROVED_ABSENT_SCORING and _is_late_application(application):
            _apply_late_leave_scoring(application, base_event, counts, penalized, events)
        elif md_approved and lt_name == "Half_day":
            months_with_half_full.add(_month_key(application.start_date))
            _apply_on_time_approved_leave_scoring(
                application,
                base_event,
                counts,
                penalized,
                events,
                event_type="half_day",
                points_value=POINTS_HALF_DAY,
                monthly_allowance_used=monthly_allowance_used,
            )
        elif md_approved and lt_name == "Full_day":
            months_with_half_full.add(_month_key(application.start_date))
            _apply_on_time_approved_leave_scoring(
                application,
                base_event,
                counts,
                penalized,
                events,
                event_type="full_day",
                points_value=POINTS_FULL_DAY,
                monthly_allowance_used=monthly_allowance_used,
            )

    no_leave_bonus, no_leave_month_count = _apply_no_leave_month_bonuses(
        _months_in_period(year, month, quarter),
        months_with_half_full,
        events,
    )
    counts["no_leave_months"] = no_leave_month_count

    # Gross monthly leave points (all half/full leaves, before free allowance).
    points = {
        "half_day": float(counts["half_day"] * POINTS_HALF_DAY),
        "full_day": float(counts["full_day"] * POINTS_FULL_DAY),
        "unapproved_absent": float(counts["unapproved_absent"] * POINTS_UNAPPROVED_ABSENT),
        "no_leave_bonus": no_leave_bonus,
    }
    net_points = {
        "half_day": float(penalized["half_day"] * POINTS_HALF_DAY),
        "full_day": float(penalized["full_day"] * POINTS_FULL_DAY),
        "unapproved_absent": float(counts["unapproved_absent"] * POINTS_UNAPPROVED_ABSENT),
        "no_leave_bonus": no_leave_bonus,
    }
    total_points = sum(net_points.values())
    counts["waived_units"] = round(counts["waived_units"], 2)

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
        "monthly_free_allowance": float(MONTHLY_FREE_LEAVE_ALLOWANCE),
        "no_leave_monthly_bonus": float(NO_LEAVE_MONTHLY_BONUS),
        "counts": counts,
        "points": points,
        "total_points": round(total_points, 2),
        "events": events,
    }


def parse_leave_points_period(request):
    """
    Parse year + optional month or quarter from query params.
    Returns (year, month, quarter, error_response_dict_or_none).
    """
    raw_year = (request.query_params.get("year") or "").strip()
    raw_month = (request.query_params.get("month") or "").strip()
    raw_quarter = (request.query_params.get("quarter") or "").strip()

    if not raw_year:
        return None, None, None, {"detail": "Query parameter year is required."}

    try:
        year = int(raw_year)
    except (TypeError, ValueError):
        return None, None, None, {"detail": "year must be an integer."}

    month = None
    quarter = None

    if raw_month:
        if raw_quarter:
            return None, None, None, {"detail": "Use either month or quarter, not both."}
        try:
            month = int(raw_month)
        except (TypeError, ValueError):
            return None, None, None, {"detail": "month must be an integer."}
        if month < 1 or month > 12:
            return None, None, None, {"detail": "month must be between 1 and 12."}
    elif raw_quarter:
        try:
            quarter = int(raw_quarter)
        except (TypeError, ValueError):
            return None, None, None, {"detail": "quarter must be an integer."}
        if quarter < 1 or quarter > 4:
            return None, None, None, {"detail": "quarter must be between 1 and 4."}

    return year, month, quarter, None


def resolve_leave_points_user(request, on_leave_checker, get_user_role):
    """
    Target employee for leave points.
    Default: request.user. Optional ?employee= or ?username= for HR/Admin/MD/TeamLead.
    """
    raw = (request.query_params.get("employee") or request.query_params.get("username") or "").strip()
    if not raw or raw == request.user.username:
        return request.user, None

    if not on_leave_checker(request.user):
        return None, {"detail": "You do not have permission to view another employee's leave points."}

    target = User.objects.filter(username=raw).first()
    if not target:
        return None, {"detail": "Employee not found."}

    role = (get_user_role(request.user) or "").strip()
    if role in ("TeamLead", "Teamlead"):
        is_team_member = Profile.objects.filter(Employee_id=target, Teamlead=request.user).exists()
        if not is_team_member:
            return None, {"detail": "You may only view leave points for your team members."}

    return target, None
