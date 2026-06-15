"""
Project phase checklist performance points from DeadlineProjectPhase.checklist.

Employee / Intern:
- 17.5 points per completed checklist; each calendar month capped at 70 (4 items).

Team Lead:
- 10 points per completed checklist on phases where phase.team_lead_id matches the TL;
  each calendar month capped at 70 (7 items). Completer (employeeIds) does not matter.

Quarter / year totals sum monthly capped scores (quarter max 210, year max 840).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model

from accounts.filters import _get_user_role_sync
from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile

from .models import DeadlineProjectPhase
from .permissions import resolve_deadline_employee_id

User = get_user_model()

EMPLOYEE_POINTS_PER_CHECKLIST = Decimal("17.5")
EMPLOYEE_FULL_SCORE_CHECKLISTS = 4

TEAMLEAD_POINTS_PER_CHECKLIST = Decimal("10")
TEAMLEAD_FULL_SCORE_CHECKLISTS = 7

MONTHLY_MAX_POINTS = Decimal("70")
MONTHS_PER_QUARTER = 3
MONTHS_PER_YEAR = 12

_FY_QUARTER_MONTHS = {
    1: (4, 5, 6),
    2: (7, 8, 9),
    3: (10, 11, 12),
    4: (1, 2, 3),
}


def _role_name(user) -> str:
    return (_get_user_role_sync(user) or "").strip()


def _is_team_lead_role(role: str) -> bool:
    return role in ("TeamLead", "Teamlead")


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
    return [(year, m) for m in range(1, MONTHS_PER_YEAR + 1)]


def _max_points_for_period(year: int, month: int | None, quarter: int | None) -> float:
    months_count = len(_months_in_period(year, month, quarter))
    return float(MONTHLY_MAX_POINTS * months_count)


def _parse_checked_date(raw) -> date | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw.strip()[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _date_in_period(checked_date: date | None, year: int, month: int | None, quarter: int | None) -> bool:
    if checked_date is None:
        return False
    if month is not None:
        return checked_date.year == year and checked_date.month == month
    if quarter is not None:
        months = _FY_QUARTER_MONTHS[quarter]
        expected_year = year + 1 if quarter == 4 else year
        return checked_date.year == expected_year and checked_date.month in months
    return checked_date.year == year


def _normalize_employee_ids(raw) -> list[int]:
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    ids = []
    for value in raw:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def _iter_phase_checklist_items():
    phases = (
        DeadlineProjectPhase.objects.filter(archived=False, project__archived=False)
        .only("checklist", "team_lead_id")
        .iterator()
    )
    for phase in phases:
        for item in phase.checklist or []:
            if isinstance(item, dict):
                yield phase.team_lead_id, item


def _role_for_employee_id(emp_id: int) -> str:
    user = User.objects.filter(username=str(emp_id)).first()
    if user is None:
        return ""
    return _role_name(user)


def _assigned_for_employee(employee_id: int) -> int:
    assigned = 0
    for _, item in _iter_phase_checklist_items():
        if employee_id in _normalize_employee_ids(item.get("employeeIds")):
            assigned += 1
    return assigned


def _completed_for_ids(
    id_set: set[int],
    year: int,
    month: int | None,
    quarter: int | None,
) -> int:
    if not id_set:
        return 0
    completed = 0
    for _, item in _iter_phase_checklist_items():
        if not item.get("checked"):
            continue
        ids = _normalize_employee_ids(item.get("employeeIds"))
        if not any(emp_id in id_set for emp_id in ids):
            continue
        checked_date = _parse_checked_date(item.get("checkedDate"))
        if not _date_in_period(checked_date, year, month, quarter):
            continue
        completed += 1
    return completed


def _phases_as_team_lead(team_lead_id: int | None) -> int:
    if team_lead_id is None:
        return 0
    return DeadlineProjectPhase.objects.filter(
        archived=False,
        project__archived=False,
        team_lead_id=team_lead_id,
    ).count()


def _completed_breakdown_for_phase_team_lead(
    team_lead_id: int | None,
    year: int,
    month: int | None,
    quarter: int | None,
) -> dict[str, int]:
    if team_lead_id is None:
        return {
            "team_lead": 0,
            "employees": 0,
            "interns": 0,
            "aggregated_total": 0,
        }

    team_lead = 0
    employees = 0
    interns = 0
    aggregated = 0

    for phase_team_lead_id, item in _iter_phase_checklist_items():
        if phase_team_lead_id != team_lead_id:
            continue
        if not item.get("checked"):
            continue
        checked_date = _parse_checked_date(item.get("checkedDate"))
        if not _date_in_period(checked_date, year, month, quarter):
            continue
        aggregated += 1
        ids = set(_normalize_employee_ids(item.get("employeeIds")))
        if team_lead_id in ids:
            team_lead += 1
        for emp_id in ids:
            if emp_id == team_lead_id:
                continue
            role = _role_for_employee_id(emp_id)
            if role == "Intern":
                interns += 1
            elif role == "Employee":
                employees += 1

    return {
        "team_lead": team_lead,
        "employees": employees,
        "interns": interns,
        "aggregated_total": aggregated,
    }


def _monthly_capped_score(completed: int, points_per_checklist: Decimal) -> Decimal:
    raw = Decimal(completed) * points_per_checklist
    return min(MONTHLY_MAX_POINTS, raw)


def _score_from_monthly_caps(
    monthly_counts: list[int],
    points_per_checklist: Decimal,
) -> Decimal:
    total = Decimal("0")
    for count in monthly_counts:
        total += _monthly_capped_score(count, points_per_checklist)
    return total


def _employee_monthly_counts(
    id_set: set[int],
    year: int,
    month: int | None,
    quarter: int | None,
) -> list[int]:
    return [
        _completed_for_ids(id_set, cal_year, cal_month, None)
        for cal_year, cal_month in _months_in_period(year, month, quarter)
    ]


def _team_lead_monthly_counts(
    team_lead_id: int | None,
    year: int,
    month: int | None,
    quarter: int | None,
) -> list[int]:
    if team_lead_id is None:
        return [0] * len(_months_in_period(year, month, quarter))
    return [
        _completed_breakdown_for_phase_team_lead(team_lead_id, cal_year, cal_month, None)["aggregated_total"]
        for cal_year, cal_month in _months_in_period(year, month, quarter)
    ]


def build_checklist_points(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    employee_id = resolve_deadline_employee_id(user)
    role = _role_name(user)
    profile = Profile.objects.filter(Employee_id=user).select_related("Role").first()
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None) or role

    period_max = _max_points_for_period(year, month, quarter)
    months_count = len(_months_in_period(year, month, quarter))

    base = {
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
        "monthly_max_points": float(MONTHLY_MAX_POINTS),
        "max_points": period_max,
        "months_in_period": months_count,
    }

    if _is_team_lead_role(role):
        tl_id = employee_id
        breakdown = _completed_breakdown_for_phase_team_lead(tl_id, year, month, quarter)
        monthly_counts = _team_lead_monthly_counts(tl_id, year, month, quarter)
        total = _score_from_monthly_caps(monthly_counts, TEAMLEAD_POINTS_PER_CHECKLIST)
        return {
            **base,
            "role_type": "team_lead",
            "points_per_checklist": float(TEAMLEAD_POINTS_PER_CHECKLIST),
            "full_score_at_checklists": TEAMLEAD_FULL_SCORE_CHECKLISTS,
            "phase_stats": {
                "phases_as_team_lead": _phases_as_team_lead(tl_id),
            },
            "completed_by": breakdown,
            "counts": {
                "completed_checklists": breakdown["aggregated_total"],
                "assigned_checklists": None,
            },
            "main_score": float(round(total, 2)),
            "monthly_bonus": 0.0,
            "total_points": float(round(total, 2)),
        }

    role_type = "intern" if role == "Intern" else "employee"
    id_set = {employee_id} if employee_id is not None else set()
    completed = _completed_for_ids(id_set, year, month, quarter)
    assigned = _assigned_for_employee(employee_id) if employee_id is not None else 0
    monthly_counts = _employee_monthly_counts(id_set, year, month, quarter)
    total = _score_from_monthly_caps(monthly_counts, EMPLOYEE_POINTS_PER_CHECKLIST)
    return {
        **base,
        "role_type": role_type,
        "points_per_checklist": float(EMPLOYEE_POINTS_PER_CHECKLIST),
        "full_score_at_checklists": EMPLOYEE_FULL_SCORE_CHECKLISTS,
        "counts": {
            "completed_checklists": completed,
            "assigned_checklists": assigned,
        },
        "main_score": float(round(total, 2)),
        "monthly_bonus": 0.0,
        "total_points": float(round(total, 2)),
    }


__all__ = [
    "build_checklist_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
]
