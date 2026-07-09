"""
DM work scoring from approved DmWorkEntry rows.

Scoring rules (per calendar month):
- Digital media: main capped at 40/month; bonus for work above target.
- Digital content: main capped at 30/month; bonus for work above target.
- Raw points per type: (completed_count / target_count) * max_main_points
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile

from .dm_scoring_targets import (
    DM_CONTENT_MAX_MAIN_POINTS,
    DM_MEDIA_MAX_MAIN_POINTS,
    DEFAULT_DIGITAL_CONTENT_TARGET_COUNT,
    DEFAULT_DIGITAL_MEDIA_TARGET_COUNT,
    is_dm_profile,
    resolve_dm_scoring_targets,
)
from .models import DmWorkEntry

User = get_user_model()


def _fy_quarter_date_filter(year: int, quarter: int) -> Q:
    # FY quarters are defined in other scoring modules as Apr-Jun, Jul-Sep, Oct-Dec, Jan-Mar.
    months = {
        1: (4, 5, 6),
        2: (7, 8, 9),
        3: (10, 11, 12),
        4: (1, 2, 3),
    }[quarter]
    if quarter == 4:
        return Q(created_at__year=year + 1, created_at__month__in=months)
    return Q(created_at__year=year, created_at__month__in=months)


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


def _approved_entries_for_creator(user, year: int, month: int | None, quarter: int | None):
    qs = (
        DmWorkEntry.objects.filter(
            created_by=user,
            status=DmWorkEntry.ApprovalStatus.APPROVED,
        )
        .order_by("created_at", "id")
    )
    if month is not None:
        qs = qs.filter(created_at__year=year, created_at__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(created_at__year=year)
    return qs


def _split_main_and_bonus(raw: Decimal, cap: Decimal) -> tuple[Decimal, Decimal]:
    main = min(raw, cap)
    return main, raw - main


def _raw_points(completed: int, target: int, max_points: Decimal) -> Decimal:
    if completed <= 0 or target <= 0:
        return Decimal("0")
    return (Decimal(completed) / Decimal(target)) * max_points


def build_dm_work_points(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    profile = (
        Profile.objects.filter(Employee_id=user)
        .select_related("Role")
        .prefetch_related("functions")
        .first()
    )
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)
    eligible = is_dm_profile(profile)

    months = _months_in_period(year, month, quarter)
    months_count = len(months)

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": bool(eligible),
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "year": year,
        "month": month,
        "quarter": quarter,
        "months_in_period": months_count,
        "digital_media_max_main_points": float(DM_MEDIA_MAX_MAIN_POINTS),
        "digital_content_max_main_points": float(DM_CONTENT_MAX_MAIN_POINTS),
        "counts": {"digital_media": 0, "digital_content": 0, "total": 0},
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "events": [],
    }

    if not eligible:
        return base

    # Count approved entries per month/type
    monthly_counts: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: {"digital_media": 0, "digital_content": 0})
    for entry in _approved_entries_for_creator(user, year, month, quarter):
        created = entry.created_at
        if created is None:
            continue
        created = created if created.tzinfo is None else created
        key = (created.year, created.month)
        monthly_counts[key][entry.content_type] = monthly_counts[key].get(entry.content_type, 0) + 1

    max_media = Decimal(str(DM_MEDIA_MAX_MAIN_POINTS))
    max_content = Decimal(str(DM_CONTENT_MAX_MAIN_POINTS))

    main_total = Decimal("0")
    bonus_total = Decimal("0")
    media_total = 0
    content_total = 0

    for y, m in months:
        counts = monthly_counts.get((y, m), {"digital_media": 0, "digital_content": 0})
        media = int(counts.get(DmWorkEntry.ContentType.DIGITAL_MEDIA, 0) or 0)
        content = int(counts.get(DmWorkEntry.ContentType.DIGITAL_CONTENT, 0) or 0)
        media_total += media
        content_total += content

        targets = resolve_dm_scoring_targets(
            user,
            year=y,
            month=m,
            profile=profile,
        )
        media_target = int(targets.get("digital_media_target_count") or DEFAULT_DIGITAL_MEDIA_TARGET_COUNT)
        content_target = int(targets.get("digital_content_target_count") or DEFAULT_DIGITAL_CONTENT_TARGET_COUNT)

        raw_media = _raw_points(media, media_target, max_media)
        raw_content = _raw_points(content, content_target, max_content)
        media_main, media_bonus = _split_main_and_bonus(raw_media, max_media)
        content_main, content_bonus = _split_main_and_bonus(raw_content, max_content)

        month_main = media_main + content_main
        month_bonus = media_bonus + content_bonus
        main_total += month_main
        bonus_total += month_bonus

        if month is not None or media > 0 or content > 0:
            base["events"].append(
                {
                    "event_type": "monthly_score",
                    "month": f"{y}-{m:02d}",
                    "digital_media": {
                        "completed_count": media,
                        "target_count": media_target,
                        "main_score": float(round(media_main, 2)),
                        "monthly_bonus": float(round(media_bonus, 2)),
                    },
                    "digital_content": {
                        "completed_count": content,
                        "target_count": content_target,
                        "main_score": float(round(content_main, 2)),
                        "monthly_bonus": float(round(content_bonus, 2)),
                    },
                    "main_score": float(round(month_main, 2)),
                    "monthly_bonus": float(round(month_bonus, 2)),
                }
            )

    total_points = main_total + bonus_total
    return {
        **base,
        "counts": {
            "digital_media": media_total,
            "digital_content": content_total,
            "total": media_total + content_total,
        },
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
    }


__all__ = [
    "build_dm_work_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
]

