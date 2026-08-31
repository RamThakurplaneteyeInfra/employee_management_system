"""
Farm Core / Infra Core service scoring from completed FarmServiceTask rows.

Replaces checklist for employees whose Profile.Branch is Farm Core or Infra Core
and who have any of: NPD, NPC, HC, IP.

Rules:
- Credit: request created_by OR task team_members (deduped once per task)
- Count: parent tasks with status=True (subtasks ignored)
- Points: 10 per completed task
- Monthly main caps (tasks): NPD/HC/IP → 5 (50 pts); NPC → 7 (70 pts)
- Overflow above monthly main cap → monthly_bonus
- Period date: task.completed_at (set when status becomes true)
- Department filter: Farm Core → farm requests; Infra Core → infra requests
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile

from .models import FarmServiceRequest, FarmServiceTask

User = get_user_model()

POINTS_PER_TASK = Decimal("10")
CORE_BRANCHES = frozenset({"Farm Core", "Infra Core"})
ELIGIBLE_FUNCTIONS = frozenset({"NPD", "NPC", "HC", "IP"})
NPD_HC_IP_FUNCTIONS = frozenset({"NPD", "HC", "IP"})
NPC_FUNCTIONS = frozenset({"NPC"})

NPD_HC_IP_MONTHLY_TASK_CAP = 5
NPC_MONTHLY_TASK_CAP = 7

_FY_QUARTER_MONTHS = {
    1: (4, 5, 6),
    2: (7, 8, 9),
    3: (10, 11, 12),
    4: (1, 2, 3),
}

_BRANCH_TO_DEPARTMENT = {
    "farm core": FarmServiceRequest.DEPARTMENT_FARM,
    "infra core": FarmServiceRequest.DEPARTMENT_INFRA,
}


def _function_names_upper(profile: Profile | None) -> set[str]:
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


def _branch_name(profile: Profile | None) -> str:
    if profile is None:
        return ""
    branch = getattr(profile, "Branch", None)
    return (getattr(branch, "branch_name", None) or "").strip()


def is_core_service_profile(profile: Profile | None) -> bool:
    if profile is None:
        return False
    branch = _branch_name(profile)
    if branch not in CORE_BRANCHES:
        return False
    return bool(_function_names_upper(profile) & ELIGIBLE_FUNCTIONS)


def _monthly_task_cap(function_names: set[str]) -> int:
    # Prefer NPD/HC/IP cap when both special sets are present (matches scoring group priority).
    if function_names & NPD_HC_IP_FUNCTIONS:
        return NPD_HC_IP_MONTHLY_TASK_CAP
    if function_names & NPC_FUNCTIONS:
        return NPC_MONTHLY_TASK_CAP
    return NPD_HC_IP_MONTHLY_TASK_CAP


def _department_for_branch(branch_name: str) -> str | None:
    return _BRANCH_TO_DEPARTMENT.get(branch_name.strip().lower())


def _months_in_period(year: int, month: int | None, quarter: int | None) -> list[tuple[int, int]]:
    if month is not None:
        return [(year, month)]
    if quarter is not None:
        cal_year = year + 1 if quarter == 4 else year
        return [(cal_year, m) for m in _FY_QUARTER_MONTHS[quarter]]
    return [(year, m) for m in range(1, 13)]


def _period_type(month: int | None, quarter: int | None) -> str:
    if month is not None:
        return "month"
    if quarter is not None:
        return "quarter"
    return "year"


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


def _fy_quarter_completed_at_filter(year: int, quarter: int) -> Q:
    months = _FY_QUARTER_MONTHS[quarter]
    if quarter == 4:
        return Q(completed_at__year=year + 1, completed_at__month__in=months)
    return Q(completed_at__year=year, completed_at__month__in=months)


def _local_date(dt) -> date | None:
    if dt is None:
        return None
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.date()


def _completed_tasks_for_user(
    user,
    year: int,
    month: int | None,
    quarter: int | None,
    *,
    department: str | None,
):
    """Completed parent tasks credited to creator or team member (once per task)."""
    qs = (
        FarmServiceTask.objects.filter(status=True, completed_at__isnull=False)
        .filter(Q(request__created_by=user) | Q(team_members=user))
        .select_related("request")
        .prefetch_related("team_members")
        .distinct()
    )
    if department:
        qs = qs.filter(request__department=department)
    if month is not None:
        qs = qs.filter(completed_at__year=year, completed_at__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_completed_at_filter(year, quarter))
    else:
        qs = qs.filter(completed_at__year=year)
    return qs.order_by("completed_at", "id")


def _credit_roles_for_task(task: FarmServiceTask, user) -> list[str]:
    roles: list[str] = []
    if task.request.created_by_id == user.pk:
        roles.append("creator")
    if any(member.pk == user.pk for member in task.team_members.all()):
        roles.append("team_member")
    return roles


def _split_main_and_bonus(gross: Decimal, cap: Decimal) -> tuple[Decimal, Decimal]:
    main = min(gross, cap)
    return main, gross - main


def build_core_service_points(
    user, year: int, month: int | None = None, quarter: int | None = None
) -> dict:
    profile = (
        Profile.objects.filter(Employee_id=user)
        .select_related("Role", "Branch")
        .prefetch_related("functions")
        .first()
    )
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)
    function_names = _function_names_upper(profile)
    branch_name = _branch_name(profile)
    eligible = is_core_service_profile(profile)
    task_cap = _monthly_task_cap(function_names) if eligible else NPD_HC_IP_MONTHLY_TASK_CAP
    monthly_points_cap = POINTS_PER_TASK * Decimal(task_cap)
    department = _department_for_branch(branch_name) if eligible else None

    months = _months_in_period(year, month, quarter)
    months_count = len(months)
    period_max = float(monthly_points_cap * months_count)

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "branch": branch_name or None,
        "department": department,
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "months_in_period": months_count,
        "points_per_task": float(POINTS_PER_TASK),
        "monthly_task_cap": task_cap,
        "monthly_max_points": float(monthly_points_cap),
        "max_main_points": period_max,
        "max_bonus_points": None,
        "max_points": period_max,
        "counts": {"completed_tasks": 0},
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "by_month": [],
        "events": [],
    }

    if not eligible:
        return base

    tasks = list(
        _completed_tasks_for_user(
            user, year, month, quarter, department=department
        )
    )
    by_month_count: dict[tuple[int, int], int] = defaultdict(int)
    events: list[dict] = []

    for task in tasks:
        completed_on = _local_date(task.completed_at)
        if completed_on is None:
            continue
        key = (completed_on.year, completed_on.month)
        by_month_count[key] += 1
        events.append(
            {
                "task_id": task.pk,
                "request_id": task.request_id,
                "task_name": task.task_name,
                "completed_on": completed_on.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "department": getattr(task.request, "department", None),
                "credit_as": _credit_roles_for_task(task, user),
                "points": float(POINTS_PER_TASK),
            }
        )

    main_total = Decimal("0")
    bonus_total = Decimal("0")
    month_rows: list[dict] = []
    completed_total = 0

    for y, m in months:
        count = by_month_count.get((y, m), 0)
        completed_total += count
        gross = Decimal(count) * POINTS_PER_TASK
        main, bonus = _split_main_and_bonus(gross, monthly_points_cap)
        main_total += main
        bonus_total += bonus
        month_rows.append(
            {
                "year": y,
                "month": m,
                "period": f"{y}-{m:02d}",
                "completed_tasks": count,
                "raw_points": float(round(gross, 2)),
                "main_score": float(round(main, 2)),
                "monthly_bonus": float(round(bonus, 2)),
            }
        )

    base.update(
        {
            "counts": {"completed_tasks": completed_total},
            "main_score": float(round(main_total, 2)),
            "monthly_bonus": float(round(bonus_total, 2)),
            "total_points": float(round(main_total + bonus_total, 2)),
            "by_month": month_rows,
            "events": events,
        }
    )
    return base


__all__ = [
    "POINTS_PER_TASK",
    "CORE_BRANCHES",
    "ELIGIBLE_FUNCTIONS",
    "is_core_service_profile",
    "build_core_service_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
]
