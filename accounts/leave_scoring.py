"""
Monthly leave event counts and performance points from LeaveApplicationData.

Scoring rules:
- Half day (approved, applied on/before leave date): -0.5
- Full day (approved, applied on/before leave date): -1.0
- Unapproved absent (applied after leave start_date): -1.5 once, plus -1 per
  additional full day (3-day late leave → 2 full + 1 unapproved = -3.5)
- Alternate assigned & accepted on applicant's leave: +0.25
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
POINTS_ALTERNATE_ACCEPTED = Decimal("0.25")

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


def _alternate_accepted(application: LeaveApplicationData) -> bool:
    if not application.alternative_id:
        return False
    alt = getattr(application, "alternative_approval", None)
    return bool(alt and getattr(alt, "name", None) == "Approved")


def _duration_whole_days(application: LeaveApplicationData) -> int:
    raw = float(application.duration_of_days or 1)
    return max(1, int(math.ceil(raw)))


def _apply_late_leave_scoring(application: LeaveApplicationData, base_event: dict, counts: dict, events: list):
    """
  Late / unapproved: 1× unapproved (-1.5) plus (duration - 1) full-day units (-1 each).
  Example: 3-day late leave → full_day=2, unapproved_absent=1 → -3.5 total.
    """
    whole_days = _duration_whole_days(application)
    extra_full_days = max(0, whole_days - 1)
    if extra_full_days:
        counts["full_day"] += extra_full_days
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
        "leave_type", "MD_approval", "alternative_approval"
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


def build_leave_points(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    counts = {
        "half_day": 0,
        "full_day": 0,
        "unapproved_absent": 0,
        "alternate_assigned_accepted": 0,
    }
    events = []

    for application in _applications_for_period(user, year, month, quarter):
        lt_name = _leave_type_name(application)
        late = _is_late_application(application)
        md_approved = _is_md_approved(application)
        base_event = {
            "leave_id": application.id,
            "start_date": application.start_date.isoformat(),
            "applied_date": _applied_date(application).isoformat(),
            "leave_type": lt_name or None,
        }

        if late:
            _apply_late_leave_scoring(application, base_event, counts, events)
        elif md_approved and lt_name == "Half_day":
            counts["half_day"] += 1
            events.append({**base_event, "event_type": "half_day", "points": float(POINTS_HALF_DAY)})
        elif md_approved and lt_name == "Full_day":
            counts["full_day"] += 1
            events.append({**base_event, "event_type": "full_day", "points": float(POINTS_FULL_DAY)})

        if _alternate_accepted(application):
            counts["alternate_assigned_accepted"] += 1
            events.append(
                {
                    **base_event,
                    "event_type": "alternate_assigned_accepted",
                    "points": float(POINTS_ALTERNATE_ACCEPTED),
                }
            )

    points = {
        "half_day": float(counts["half_day"] * POINTS_HALF_DAY),
        "full_day": float(counts["full_day"] * POINTS_FULL_DAY),
        "unapproved_absent": float(counts["unapproved_absent"] * POINTS_UNAPPROVED_ABSENT),
        "alternate_assigned_accepted": float(
            counts["alternate_assigned_accepted"] * POINTS_ALTERNATE_ACCEPTED
        ),
    }
    total_points = sum(points.values())

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
