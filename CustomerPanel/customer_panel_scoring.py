"""
Customer panel entry performance points from CustomerPanelAmountLog (created_by).

Points are attributed to the user who entered each amount log, in the month of
the log's selected date (log.date), not the entry creator / creation month.

Applies only when the employee's Profile.functions contains any of:
- MMR
- RG

Scoring rules (per calendar month, amount-log amounts):
- ₹5,00,000 in logged amounts = 40 main_score points (₹12,500 per point).
- Points above 40 main_score in a month count as monthly_bonus.
- Quarter / year totals sum monthly main_score and monthly_bonus across months in the period.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.mmr_rg_scoring_targets import load_mmr_rg_targets_for_months, resolve_mmr_rg_scoring_targets
from accounts.models import Profile

from .models import CustomerPanelAmountLog

User = get_user_model()

AMOUNT_PER_POINT = Decimal("12500")
MONTHLY_TARGET_AMOUNT = Decimal("500000")
MONTHLY_MAX_MAIN_POINTS = Decimal("40")

MMR_RG_FUNCTIONS = frozenset({"MMR", "RG"})

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


def _is_mmr_rg_user(profile: Profile | None) -> bool:
    return bool(_profile_function_names_upper(profile) & MMR_RG_FUNCTIONS)


def _log_month_key(log: CustomerPanelAmountLog) -> tuple[int, int] | None:
    # log.date is a plain DateField chosen by the user; no timezone conversion.
    if log.date is None:
        return None
    return log.date.year, log.date.month


def _logs_for_creator(user, year: int, month: int | None, quarter: int | None):
    qs = (
        CustomerPanelAmountLog.objects.filter(created_by=user)
        .select_related("entry")
        .order_by("date", "id")
    )
    if month is not None:
        qs = qs.filter(date__year=year, date__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(date__year=year)
    return qs


def _month_amount(logs) -> Decimal:
    total = Decimal("0")
    for log in logs:
        if log.amount is not None:
            total += log.amount
    return total


def _month_scores_for_amount(
    amount: Decimal, target_amount: Decimal | None = None
) -> tuple[Decimal, Decimal, Decimal]:
    target = target_amount or MONTHLY_TARGET_AMOUNT
    if amount <= 0 or target <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    raw_points = (amount / target) * MONTHLY_MAX_MAIN_POINTS
    main = min(raw_points, MONTHLY_MAX_MAIN_POINTS)
    bonus = raw_points - main
    return main, bonus, main + bonus


def _build_events_for_month(logs, target_amount: Decimal | None = None) -> list[dict]:
    target = target_amount or MONTHLY_TARGET_AMOUNT
    amount_per_main_point = target / MONTHLY_MAX_MAIN_POINTS if MONTHLY_MAX_MAIN_POINTS else Decimal("0")
    events = []
    main_so_far = Decimal("0")
    for log in logs:
        amount = log.amount or Decimal("0")
        raw_pts = amount / amount_per_main_point if amount > 0 and amount_per_main_point > 0 else Decimal("0")
        main_room = max(Decimal("0"), MONTHLY_MAX_MAIN_POINTS - main_so_far)
        log_main = min(raw_pts, main_room)
        log_bonus = raw_pts - log_main
        main_so_far += log_main

        entry = getattr(log, "entry", None)
        base = {
            "log_id": log.pk,
            "entry_id": log.entry_id,
            "business_name": (getattr(entry, "business_name", None) or ""),
            "amount": float(amount),
            "date": log.date.isoformat() if log.date else None,
            "notes": log.notes,
        }
        if log_main > 0:
            events.append({**base, "points_type": "main", "points": float(round(log_main, 2))})
        if log_bonus > 0:
            events.append({**base, "points_type": "bonus", "points": float(round(log_bonus, 2))})
    return events


def build_customer_panel_entries_points(
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

    eligible = _is_mmr_rg_user(profile)
    months_in_period = _months_in_period(year, month, quarter)
    months_count = len(months_in_period)
    target_rows = load_mmr_rg_targets_for_months(profile, months_in_period) if eligible else {}

    display_year, display_month = months_in_period[0] if months_in_period else (year, month or 1)
    if month is not None:
        display_year, display_month = year, month
    resolved_targets = resolve_mmr_rg_scoring_targets(
        user,
        year=display_year,
        month=display_month,
        profile=profile,
        custom=target_rows.get((display_year, display_month)),
    )
    monthly_target_amount = (
        resolved_targets["customer_panel_target_amount"]
        if eligible
        else MONTHLY_TARGET_AMOUNT
    )

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "eligible_functions": sorted(list(_profile_function_names_upper(profile) & MMR_RG_FUNCTIONS)),
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "amount_per_point": float(
            monthly_target_amount / MONTHLY_MAX_MAIN_POINTS
            if MONTHLY_MAX_MAIN_POINTS
            else AMOUNT_PER_POINT
        ),
        "monthly_target_amount": float(monthly_target_amount),
        "monthly_max_main_points": float(MONTHLY_MAX_MAIN_POINTS),
        "target_is_customized": bool(eligible and resolved_targets.get("is_customized")),
        "scoring_targets": {
            "year": display_year,
            "month": display_month,
            "defaults": resolved_targets.get("defaults"),
            "custom_fields": resolved_targets.get("custom_fields"),
            "effective": {
                "customer_panel_target_amount": float(monthly_target_amount),
            },
        },
        "max_main_points": float(MONTHLY_MAX_MAIN_POINTS * months_count),
        "max_bonus_points": None,
        "max_points": float(MONTHLY_MAX_MAIN_POINTS * months_count),
        "months_in_period": months_count,
        "counts": {"amount_logs": 0, "entries": 0, "total_amount": 0.0},
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "events": [],
    }

    if not eligible:
        return base

    monthly_logs: dict[tuple[int, int], list] = defaultdict(list)
    entry_ids: set[int] = set()
    for log in _logs_for_creator(user, year, month, quarter):
        month_key = _log_month_key(log)
        if month_key is None:
            continue
        monthly_logs[month_key].append(log)
        entry_ids.add(log.entry_id)

    main_total = Decimal("0")
    bonus_total = Decimal("0")
    log_count = 0
    amount_total = Decimal("0")
    events: list[dict] = []

    for month_key in months_in_period:
        logs = monthly_logs.get(month_key, [])
        log_count += len(logs)
        month_amount = _month_amount(logs)
        amount_total += month_amount
        y, m = month_key
        month_custom = target_rows.get((y, m)) if eligible else None
        month_targets = resolve_mmr_rg_scoring_targets(
            user,
            year=y,
            month=m,
            profile=profile,
            custom=month_custom,
        )
        month_target_amount = (
            month_targets["customer_panel_target_amount"]
            if eligible
            else MONTHLY_TARGET_AMOUNT
        )
        month_main, month_bonus, _ = _month_scores_for_amount(month_amount, month_target_amount)
        main_total += month_main
        bonus_total += month_bonus
        if month is not None or logs:
            events.extend(_build_events_for_month(logs, month_target_amount))

    total_points = main_total + bonus_total
    return {
        **base,
        "counts": {
            "amount_logs": log_count,
            "entries": len(entry_ids),
            "total_amount": float(round(amount_total, 2)),
        },
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
        "events": events,
    }


__all__ = [
    "build_customer_panel_entries_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
    "AMOUNT_PER_POINT",
    "MONTHLY_TARGET_AMOUNT",
    "MONTHLY_MAX_MAIN_POINTS",
    "MMR_RG_FUNCTIONS",
]
