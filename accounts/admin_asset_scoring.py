"""
Admin asset-panel performance points (org-wide performing vs non-performing ratio).

Per calendar month (snapshot at query time):
- main_score = (performing_assets / total_assets) * 20
- If there are no assets, full 20 main points are awarded.
- More non-performing assets reduce the score out of 20.

Quarter / year totals sum the monthly main score across months in the period using the
current asset snapshot (historical asset status is not tracked).
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model

from accounts.models import Profile
from adminpanel.models import Asset

from .admin_task_scoring import (
    ADMIN_ROLE_NAME,
    _months_in_period,
    _period_label,
    _period_range_label,
    _period_type,
    is_admin_profile,
)

User = get_user_model()

ASSET_MAX_MAIN_POINTS = Decimal("20")


def _asset_counts() -> tuple[int, int, int]:
    total = Asset.objects.count()
    if total == 0:
        return 0, 0, 0
    non_performing = Asset.objects.filter(
        status=Asset.PerformanceStatus.NONPERFORMING
    ).count()
    performing = total - non_performing
    return total, performing, non_performing


def _monthly_main_from_counts(total: int, performing: int) -> Decimal:
    if total <= 0:
        return ASSET_MAX_MAIN_POINTS
    return (Decimal(performing) / Decimal(total)) * ASSET_MAX_MAIN_POINTS


def build_admin_asset_points(
    user, year: int, month: int | None = None, quarter: int | None = None
) -> dict:
    profile = Profile.objects.filter(Employee_id=user).select_related("Role").first()
    display_name = (getattr(profile, "Name", None) or user.username) if profile else user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)

    eligible = is_admin_profile(profile)
    months_in_period = _months_in_period(year, month, quarter)
    months_count = len(months_in_period)

    total, performing, non_performing = _asset_counts()
    monthly_main = _monthly_main_from_counts(total, performing)
    performing_ratio = float(round(Decimal(performing) / Decimal(total), 4)) if total else 1.0

    base = {
        "employee_id": user.username,
        "name": display_name,
        "role": role_name,
        "eligible": eligible,
        "scope": "org_wide_asset_panel",
        "period_type": _period_type(month, quarter),
        "period": _period_label(year, month, quarter),
        "period_range": _period_range_label(year, month, quarter),
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "months_in_period": months_count,
        "monthly_max_main_points": float(ASSET_MAX_MAIN_POINTS),
        "max_main_points": float(ASSET_MAX_MAIN_POINTS * months_count),
        "counts": {
            "total_assets": total,
            "performing_assets": performing,
            "nonperforming_assets": non_performing,
        },
        "performing_ratio": performing_ratio,
        "main_score": 0.0,
        "monthly_bonus": 0.0,
        "total_points": 0.0,
        "monthly_breakdown": [],
    }

    if not eligible:
        return base

    monthly_breakdown: list[dict] = []
    main_total = Decimal("0")
    for cal_year, cal_month in months_in_period:
        main_total += monthly_main
        monthly_breakdown.append(
            {
                "year": cal_year,
                "month": cal_month,
                "total_assets": total,
                "performing_assets": performing,
                "nonperforming_assets": non_performing,
                "performing_ratio": performing_ratio,
                "main_score": float(round(monthly_main, 2)),
                "monthly_bonus": 0.0,
                "total_points": float(round(monthly_main, 2)),
            }
        )

    return {
        **base,
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": 0.0,
        "total_points": float(round(main_total, 2)),
        "monthly_breakdown": monthly_breakdown,
    }


__all__ = [
    "ADMIN_ROLE_NAME",
    "ASSET_MAX_MAIN_POINTS",
    "build_admin_asset_points",
]
