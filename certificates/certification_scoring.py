"""
Certification performance points from EmployeeCertificate uploads.

Scoring rules (per calendar month):
- At least one active certificate uploaded in the month: +5 main_score (flat, not per cert).
- Each additional certificate in the same month: +5 monthly_bonus.
- Quarter / year totals sum monthly main_score and monthly_bonus across months in the period.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user
from accounts.models import Profile

from .models import EmployeeCertificate

User = get_user_model()

MAIN_SCORE_IF_ANY_CERT = Decimal("5")
BONUS_PER_EXTRA_CERT = Decimal("5")

_FY_QUARTER_MONTHS = {
    1: (4, 5, 6),
    2: (7, 8, 9),
    3: (10, 11, 12),
    4: (1, 2, 3),
}


def _fy_quarter_date_filter(year: int, quarter: int) -> Q:
    months = _FY_QUARTER_MONTHS[quarter]
    if quarter == 4:
        return Q(created_at__year=year + 1, created_at__month__in=months)
    return Q(created_at__year=year, created_at__month__in=months)


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


def _certificates_for_user_period(user, year: int, month: int | None, quarter: int | None):
    qs = EmployeeCertificate.objects.filter(employee=user, is_active=True)
    if month is not None:
        qs = qs.filter(created_at__year=year, created_at__month=month)
    elif quarter is not None:
        qs = qs.filter(_fy_quarter_date_filter(year, quarter))
    else:
        qs = qs.filter(created_at__year=year)
    return qs.order_by("created_at", "id")


def _month_scores_for_count(count: int) -> tuple[Decimal, Decimal, Decimal]:
    if count <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    main = MAIN_SCORE_IF_ANY_CERT
    bonus = BONUS_PER_EXTRA_CERT * (count - 1)
    return main, bonus, main + bonus


def _build_events_for_month(certificates) -> list[dict]:
    events = []
    for index, cert in enumerate(certificates):
        if index == 0:
            points_type = "main"
            points = float(MAIN_SCORE_IF_ANY_CERT)
        else:
            points_type = "bonus"
            points = float(BONUS_PER_EXTRA_CERT)
        created = cert.created_at
        if timezone.is_aware(created):
            created = timezone.localtime(created)
        events.append(
            {
                "certificate_id": cert.pk,
                "title": cert.title or cert.file_name or "",
                "created_at": created.date().isoformat(),
                "points_type": points_type,
                "points": points,
            }
        )
    return events


def build_certification_points(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    monthly_counts: dict[tuple[int, int], list] = defaultdict(list)
    for cert in _certificates_for_user_period(user, year, month, quarter):
        created = cert.created_at
        if timezone.is_aware(created):
            created = timezone.localtime(created)
        monthly_counts[(created.year, created.month)].append(cert)

    months_in_period = _months_in_period(year, month, quarter)
    main_total = Decimal("0")
    bonus_total = Decimal("0")
    cert_total = 0
    events: list[dict] = []

    for month_key in months_in_period:
        certs = monthly_counts.get(month_key, [])
        count = len(certs)
        cert_total += count
        month_main, month_bonus, _ = _month_scores_for_count(count)
        main_total += month_main
        bonus_total += month_bonus
        if month is not None or count > 0:
            events.extend(_build_events_for_month(certs))

    total_points = main_total + bonus_total
    months_count = len(months_in_period)
    max_main = float(MAIN_SCORE_IF_ANY_CERT * months_count)

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
        "main_score_points": float(MAIN_SCORE_IF_ANY_CERT),
        "bonus_per_extra_certificate": float(BONUS_PER_EXTRA_CERT),
        "max_main_points": max_main,
        "max_bonus_points": None,
        "max_points": max_main,
        "months_in_period": months_count,
        "counts": {"certificates": cert_total},
        "main_score": float(round(main_total, 2)),
        "monthly_bonus": float(round(bonus_total, 2)),
        "total_points": float(round(total_points, 2)),
        "events": events,
    }


__all__ = [
    "build_certification_points",
    "parse_leave_points_period",
    "resolve_leave_points_user",
    "MAIN_SCORE_IF_ANY_CERT",
    "BONUS_PER_EXTRA_CERT",
]
