"""
P&S service scoring from Approved InfraProjectFormEntry rows.

Replaces checklist for P&S employees.

Per calendar month:
- Achieved quantity = sum(MJB + MNB + VUP + PUP + BOX_Slab_Culvert + ROB + FO)
  across Approved entries created by the employee (entry.date in month).
- Raw points = (achieved / monthly_quantity_target) * 70
- Main capped at 70; overflow goes to monthly_bonus.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile
from accounts.ps_scoring_targets import (
    DEFAULT_MONTHLY_QUANTITY_TARGET,
    PS_SERVICE_MAX_MAIN_POINTS,
    is_ps_profile,
    resolve_ps_scoring_targets,
)

User = get_user_model()

SERVICE_QUANTITY_FIELDS = (
    "MJB",
    "MNB",
    "VUP",
    "PUP",
    "BOX_Slab_Culvert",
    "ROB",
    "FO",
)


def _fy_quarter_date_filter(year: int, quarter: int) -> Q:
    months = {
        1: (4, 5, 6),
        2: (7, 8, 9),
        3: (10, 11, 12),
        4: (1, 2, 3),
    }[quarter]
    if quarter == 4:
        return Q(date__year=year + 1, date__month__in=months)
    return Q(date__year=year, date__month__in=months)


def _months_in_period(year: int, month: int | None, quarter: int | None) -> list[tuple[int, int]]:
    if month is not None:
        return [(year, month)]
    if quarter is not None:
        cal_year = year + 1 if quarter == 4 else year
        months = {1: (4, 5, 6), 2: (7, 8, 9), 3: (10, 11, 12), 4: (1, 2, 3)}[quarter]
        return [(cal_year, m) for m in months]
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


def _entry_quantity(entry) -> Decimal:
    total = Decimal("0")
    for field in SERVICE_QUANTITY_FIELDS:
        value = getattr(entry, field, None)
        if value is None:
            continue
        total += Decimal(str(value))
    return total


def _approved_entries_for_creator(user, year: int, month: int | None, quarter: int | None):
    from infra_forms.models import InfraProjectFormEntry

    qs = (
        InfraProjectFormEntry.objects.filter(
            created_by=user,
            approval=InfraProjectFormEntry.APPROVAL_APPROVED,
            date__isnull=False,
        )
        .order_by("date", "id")
    )
    if month is not None:
        qs = qs.filter(date__year=year, date__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(date__year=year)
    return qs


def _split_main_and_bonus(raw: Decimal, cap: Decimal) -> tuple[Decimal, Decimal]:
    main = min(raw, cap)
    return main, raw - main


def _raw_points(achieved: Decimal, target: Decimal, max_points: Decimal) -> Decimal:
    if achieved <= 0 or target <= 0:
        return Decimal("0")
    return (achieved / target) * max_points


def build_ps_service_points(
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
    eligible = is_ps_profile(profile)

    months = _months_in_period(year, month, quarter)
    months_count = len(months)
    max_main = Decimal(str(PS_SERVICE_MAX_MAIN_POINTS)) * months_count

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "months_in_period": months_count,
        "service_max_main_points_per_month": float(PS_SERVICE_MAX_MAIN_POINTS),
        "default_monthly_quantity_target": float(DEFAULT_MONTHLY_QUANTITY_TARGET),
        "quantity_fields": list(SERVICE_QUANTITY_FIELDS),
        "max_main_points": float(max_main),
        "max_bonus_points": None,
        "max_points": float(max_main),
        "achieved_quantity": 0.0,
        "monthly_quantity_target": float(DEFAULT_MONTHLY_QUANTITY_TARGET),
        "approved_entry_count": 0,
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "events": [],
        "by_month": [],
    }

    if not eligible:
        return base

    entries = list(_approved_entries_for_creator(user, year, month, quarter))
    by_month_qty: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    by_month_count: dict[tuple[int, int], int] = defaultdict(int)
    events: list[dict] = []

    for entry in entries:
        qty = _entry_quantity(entry)
        key = (entry.date.year, entry.date.month)
        by_month_qty[key] += qty
        by_month_count[key] += 1
        events.append(
            {
                "entry_id": entry.pk,
                "date": entry.date.isoformat() if entry.date else None,
                "status": entry.status,
                "quantity": float(qty),
                "form_id": entry.form_id,
            }
        )

    main_total = Decimal("0")
    bonus_total = Decimal("0")
    achieved_total = Decimal("0")
    month_rows: list[dict] = []
    target_used = DEFAULT_MONTHLY_QUANTITY_TARGET

    for y, m in months:
        targets = resolve_ps_scoring_targets(user, year=y, month=m, profile=profile)
        target = Decimal(str(targets["monthly_quantity_target"]))
        target_used = target
        achieved = by_month_qty.get((y, m), Decimal("0"))
        achieved_total += achieved
        raw = _raw_points(achieved, target, Decimal(str(PS_SERVICE_MAX_MAIN_POINTS)))
        main, bonus = _split_main_and_bonus(raw, Decimal(str(PS_SERVICE_MAX_MAIN_POINTS)))
        main_total += main
        bonus_total += bonus
        month_rows.append(
            {
                "year": y,
                "month": m,
                "period": f"{y}-{m:02d}",
                "monthly_quantity_target": float(target),
                "achieved_quantity": float(achieved),
                "approved_entry_count": by_month_count.get((y, m), 0),
                "raw_points": float(round(raw, 2)),
                "main_score": float(round(main, 2)),
                "monthly_bonus": float(round(bonus, 2)),
            }
        )

    base.update(
        {
            "achieved_quantity": float(achieved_total),
            "monthly_quantity_target": float(target_used) if months_count == 1 else None,
            "approved_entry_count": len(entries),
            "main_score": float(round(main_total, 2)),
            "monthly_bonus": float(round(bonus_total, 2)),
            "total_points": float(round(main_total + bonus_total, 2)),
            "events": events,
            "by_month": month_rows,
        }
    )
    return base


__all__ = [
    "SERVICE_QUANTITY_FIELDS",
    "build_ps_service_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
]
