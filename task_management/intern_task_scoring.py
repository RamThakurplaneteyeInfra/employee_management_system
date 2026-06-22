"""
Intern task completion performance points (replaces project checklist scoring for interns).

Data source: tasks created by the intern (same pool as GET /tasks/viewTasks/) with status
COMPLETED. Completion month is taken from TaskStatusChangeLogs.last_edit.

Scoring rules (per calendar month):
- 21 completed tasks = 70 main_score (proportional below target).
- Each task beyond 21 in the same month adds monthly_bonus at the same per-task rate (70/21).
- Quarter / year totals sum monthly main_score and monthly_bonus across months in the period.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile

from .models import Task, TaskStatus

User = get_user_model()

INTERN_ROLE_NAME = "Intern"
MONTHLY_TARGET_TASKS = 21
MONTHLY_MAX_MAIN_POINTS = Decimal("70")
POINTS_PER_TASK = MONTHLY_MAX_MAIN_POINTS / Decimal(MONTHLY_TARGET_TASKS)

_FY_QUARTER_MONTHS = {
    1: (4, 5, 6),
    2: (7, 8, 9),
    3: (10, 11, 12),
    4: (1, 2, 3),
}


def _fy_quarter_date_filter(year: int, quarter: int) -> Q:
    months = _FY_QUARTER_MONTHS[quarter]
    if quarter == 4:
        return Q(
            status_change_logs__last_edit__year=year + 1,
            status_change_logs__last_edit__month__in=months,
        )
    return Q(status_change_logs__last_edit__year=year, status_change_logs__last_edit__month__in=months)


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


def _is_intern_profile(profile: Profile | None) -> bool:
    if profile is None:
        return False
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)
    return (role_name or "").strip() == INTERN_ROLE_NAME


def _completed_status_id() -> int | None:
    status = TaskStatus.objects.filter(status_name__iexact="COMPLETED").first()
    return status.pk if status else None


def _completed_tasks_for_creator(user, year: int, month: int | None, quarter: int | None):
    completed_id = _completed_status_id()
    if completed_id is None:
        return Task.objects.none()

    qs = (
        Task.objects.filter(created_by=user, status_id=completed_id)
        .select_related("status_change_logs")
        .filter(status_change_logs__isnull=False)
    )
    if month is not None:
        qs = qs.filter(
            status_change_logs__last_edit__year=year,
            status_change_logs__last_edit__month=month,
        )
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(status_change_logs__last_edit__year=year)
    return qs.order_by("status_change_logs__last_edit", "task_id")


def _month_scores_for_count(count: int) -> tuple[Decimal, Decimal, Decimal]:
    if count <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    if count <= MONTHLY_TARGET_TASKS:
        main = (Decimal(count) / Decimal(MONTHLY_TARGET_TASKS)) * MONTHLY_MAX_MAIN_POINTS
        return main, Decimal("0"), main
    main = MONTHLY_MAX_MAIN_POINTS
    bonus = (Decimal(count) - Decimal(MONTHLY_TARGET_TASKS)) * POINTS_PER_TASK
    return main, bonus, main + bonus


def build_intern_task_points(
    user, year: int, month: int | None = None, quarter: int | None = None
) -> dict:
    profile = Profile.objects.filter(Employee_id=user).select_related("Role").first()
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)

    eligible = _is_intern_profile(profile)
    months_in_period = _months_in_period(year, month, quarter)
    months_count = len(months_in_period)

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "task_source": "created_tasks",
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "monthly_target_tasks": MONTHLY_TARGET_TASKS,
        "monthly_max_main_points": float(MONTHLY_MAX_MAIN_POINTS),
        "points_per_task": float(round(POINTS_PER_TASK, 4)),
        "max_main_points": float(MONTHLY_MAX_MAIN_POINTS * months_count),
        "max_bonus_points": None,
        "months_in_period": months_count,
        "counts": {"completed_tasks": 0},
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "monthly_breakdown": [],
        "events": [],
    }

    if not eligible:
        return base

    monthly_tasks: dict[tuple[int, int], list[Task]] = defaultdict(list)
    for task in _completed_tasks_for_creator(user, year, month, quarter):
        log = getattr(task, "status_change_logs", None)
        completed_at = getattr(log, "last_edit", None)
        if completed_at is None:
            continue
        monthly_tasks[(completed_at.year, completed_at.month)].append(task)

    main_total = Decimal("0")
    bonus_total = Decimal("0")
    completed_total = 0
    monthly_breakdown: list[dict] = []
    events: list[dict] = []

    for month_key in months_in_period:
        tasks = monthly_tasks.get(month_key, [])
        count = len(tasks)
        completed_total += count
        month_main, month_bonus, month_total = _month_scores_for_count(count)
        main_total += month_main
        bonus_total += month_bonus
        cal_year, cal_month = month_key
        monthly_breakdown.append(
            {
                "year": cal_year,
                "month": cal_month,
                "completed_tasks": count,
                "main_score": float(round(month_main, 2)),
                "monthly_bonus": float(round(month_bonus, 2)),
                "total_points": float(round(month_total, 2)),
            }
        )
        for task in tasks:
            log = task.status_change_logs
            events.append(
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "completed_at": log.last_edit.isoformat() if log and log.last_edit else None,
                }
            )

    total_points = main_total + bonus_total
    return {
        **base,
        "counts": {"completed_tasks": completed_total},
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
        "monthly_breakdown": monthly_breakdown,
        "events": events,
    }


__all__ = [
    "INTERN_ROLE_NAME",
    "MONTHLY_TARGET_TASKS",
    "MONTHLY_MAX_MAIN_POINTS",
    "build_intern_task_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
]
