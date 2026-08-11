"""
Admin task completion performance points (replaces project checklist scoring for Admin role).

Data source: tasks assigned to the admin with status COMPLETED. Completion month is taken
from TaskStatusChangeLogs.last_edit.

Scoring rules (per calendar month):
- 10 Day tasks: 10 main points each; main capped at 3 tasks (30/month); overflow is bonus at 10 each.
- 1 Day tasks: 1 main point each; main capped at 20 tasks (20/month); overflow is bonus at 1 each.
- Combined task main cap: 50/month.
- Quarter / year totals sum monthly main_score and monthly_bonus across months in the period.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.models import Profile

from task_management.models import Task, TaskStatus

User = get_user_model()

ADMIN_ROLE_NAME = "Admin"
TEN_DAY_TYPE_NAME = "10 Day"
ONE_DAY_TYPE_NAME = "1 Day"

TEN_DAY_POINTS = Decimal("10")
TEN_DAY_MONTHLY_MAIN_CAP = 3
TEN_DAY_MONTHLY_MAX_MAIN = TEN_DAY_POINTS * Decimal(TEN_DAY_MONTHLY_MAIN_CAP)

ONE_DAY_POINTS = Decimal("1")
ONE_DAY_MONTHLY_MAIN_CAP = 20
ONE_DAY_MONTHLY_MAX_MAIN = ONE_DAY_POINTS * Decimal(ONE_DAY_MONTHLY_MAIN_CAP)

MONTHLY_MAX_MAIN_POINTS = TEN_DAY_MONTHLY_MAX_MAIN + ONE_DAY_MONTHLY_MAX_MAIN

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


def is_admin_profile(profile: Profile | None) -> bool:
    if profile is None:
        return False
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)
    return (role_name or "").strip() == ADMIN_ROLE_NAME


def _completed_status_id() -> int | None:
    status = TaskStatus.objects.filter(status_name__iexact="COMPLETED").first()
    return status.pk if status else None


def _completed_tasks_for_assignee(
    user,
    type_name: str,
    year: int,
    month: int | None,
    quarter: int | None,
):
    completed_id = _completed_status_id()
    if completed_id is None:
        return Task.objects.none()

    qs = (
        Task.objects.filter(
            assignees=user,
            status_id=completed_id,
            type__type_name__iexact=type_name,
        )
        .select_related("type", "status_change_logs")
        .filter(status_change_logs__isnull=False)
        .distinct()
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


def _month_scores_for_count(
    count: int,
    *,
    monthly_main_cap: int,
    points_per_task: Decimal,
) -> tuple[Decimal, Decimal]:
    if count <= 0:
        return Decimal("0"), Decimal("0")
    main_count = min(count, monthly_main_cap)
    main = Decimal(main_count) * points_per_task
    bonus = Decimal(max(0, count - monthly_main_cap)) * points_per_task
    return main, bonus


def _group_tasks_by_completion_month(
    tasks,
) -> dict[tuple[int, int], list[Task]]:
    monthly_tasks: dict[tuple[int, int], list[Task]] = defaultdict(list)
    for task in tasks:
        log = getattr(task, "status_change_logs", None)
        completed_at = getattr(log, "last_edit", None)
        if completed_at is None:
            continue
        monthly_tasks[(completed_at.year, completed_at.month)].append(task)
    return monthly_tasks


def build_admin_task_points(
    user, year: int, month: int | None = None, quarter: int | None = None
) -> dict:
    profile = Profile.objects.filter(Employee_id=user).select_related("Role").first()
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)

    eligible = is_admin_profile(profile)
    months_in_period = _months_in_period(year, month, quarter)
    months_count = len(months_in_period)

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "task_source": "assigned_tasks",
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "ten_day_monthly_main_cap": TEN_DAY_MONTHLY_MAIN_CAP,
        "ten_day_points_per_task": float(TEN_DAY_POINTS),
        "ten_day_monthly_max_main_points": float(TEN_DAY_MONTHLY_MAX_MAIN),
        "one_day_monthly_main_cap": ONE_DAY_MONTHLY_MAIN_CAP,
        "one_day_points_per_task": float(ONE_DAY_POINTS),
        "one_day_monthly_max_main_points": float(ONE_DAY_MONTHLY_MAX_MAIN),
        "monthly_max_main_points": float(MONTHLY_MAX_MAIN_POINTS),
        "max_main_points": float(MONTHLY_MAX_MAIN_POINTS * months_count),
        "months_in_period": months_count,
        "counts": {
            "completed_ten_day_tasks": 0,
            "completed_one_day_tasks": 0,
            "completed_tasks": 0,
        },
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "monthly_breakdown": [],
        "events": [],
    }

    if not eligible:
        return base

    ten_day_by_month = _group_tasks_by_completion_month(
        _completed_tasks_for_assignee(user, TEN_DAY_TYPE_NAME, year, month, quarter)
    )
    one_day_by_month = _group_tasks_by_completion_month(
        _completed_tasks_for_assignee(user, ONE_DAY_TYPE_NAME, year, month, quarter)
    )

    main_total = Decimal("0")
    bonus_total = Decimal("0")
    ten_day_total = 0
    one_day_total = 0
    monthly_breakdown: list[dict] = []
    events: list[dict] = []

    for month_key in months_in_period:
        ten_day_tasks = ten_day_by_month.get(month_key, [])
        one_day_tasks = one_day_by_month.get(month_key, [])
        ten_day_count = len(ten_day_tasks)
        one_day_count = len(one_day_tasks)
        ten_day_total += ten_day_count
        one_day_total += one_day_count

        ten_main, ten_bonus = _month_scores_for_count(
            ten_day_count,
            monthly_main_cap=TEN_DAY_MONTHLY_MAIN_CAP,
            points_per_task=TEN_DAY_POINTS,
        )
        one_main, one_bonus = _month_scores_for_count(
            one_day_count,
            monthly_main_cap=ONE_DAY_MONTHLY_MAIN_CAP,
            points_per_task=ONE_DAY_POINTS,
        )
        month_main = ten_main + one_main
        month_bonus = ten_bonus + one_bonus
        main_total += month_main
        bonus_total += month_bonus

        cal_year, cal_month = month_key
        monthly_breakdown.append(
            {
                "year": cal_year,
                "month": cal_month,
                "completed_ten_day_tasks": ten_day_count,
                "completed_one_day_tasks": one_day_count,
                "ten_day_main_score": float(round(ten_main, 2)),
                "ten_day_monthly_bonus": float(round(ten_bonus, 2)),
                "one_day_main_score": float(round(one_main, 2)),
                "one_day_monthly_bonus": float(round(one_bonus, 2)),
                "main_score": float(round(month_main, 2)),
                "monthly_bonus": float(round(month_bonus, 2)),
                "total_points": float(round(month_main + month_bonus, 2)),
            }
        )

        for task in ten_day_tasks + one_day_tasks:
            log = task.status_change_logs
            events.append(
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "task_type": getattr(getattr(task, "type", None), "type_name", None),
                    "completed_at": log.last_edit.isoformat() if log and log.last_edit else None,
                }
            )

    total_points = main_total + bonus_total
    return {
        **base,
        "counts": {
            "completed_ten_day_tasks": ten_day_total,
            "completed_one_day_tasks": one_day_total,
            "completed_tasks": ten_day_total + one_day_total,
        },
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
        "monthly_breakdown": monthly_breakdown,
        "events": events,
    }


__all__ = [
    "ADMIN_ROLE_NAME",
    "MONTHLY_MAX_MAIN_POINTS",
    "TEN_DAY_MONTHLY_MAIN_CAP",
    "ONE_DAY_MONTHLY_MAIN_CAP",
    "build_admin_task_points",
    "is_admin_profile",
]
