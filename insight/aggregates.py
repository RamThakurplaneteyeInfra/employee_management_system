"""
Read-only ORM aggregates for the EMS insight endpoint. No PII beyond role/department name.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum

from accounts.filters import _get_user_profile_object_sync, _get_user_role_sync
from task_management.models import TaskAssignies

User = get_user_model()

_ORG_ROLES = frozenset({"Admin", "MD", "HR"})


def _dec(v: Any) -> str:
    if v is None:
        return "0"
    if isinstance(v, Decimal):
        return str(v)
    return str(v)


def resolve_insight_tier(user: User) -> tuple[str, str | None]:
    """
    Returns (tier, role_name) where tier is 'org' or 'personal'.
    org: superuser, or Profile role in Admin/MD/HR.
    """
    if getattr(user, "is_superuser", False):
        return "org", _get_user_role_sync(user)

    role_name = _get_user_role_sync(user)
    if role_name and role_name in _ORG_ROLES:
        return "org", role_name

    return "personal", role_name


def build_metrics_payload(user: User) -> dict[str, Any]:
    """
    Returns JSON-serializable dict: role, insight_tier, and scoped aggregates only.
    """
    insight_tier, role_name = resolve_insight_tier(user)
    out: dict[str, Any] = {
        "role": role_name or "unknown",
        "insight_tier": insight_tier,
    }

    if insight_tier == "org":
        from adminpanel.models import Asset, Bill, ExpenseTracker, Vendor

        assets_total = Asset.objects.count()
        assets_by_type = list(
            Asset.objects.values("asset_type__name").annotate(count=Count("id"))[:50]
        )
        bills_agg = Bill.objects.aggregate(total_amount=Sum("amount"))
        bills_total = bills_agg["total_amount"] or 0
        bills_by_category = list(
            Bill.objects.values("category__name").annotate(total=Sum("amount"))[:50]
        )
        exp_agg = ExpenseTracker.objects.aggregate(total_amount=Sum("amount"))
        expenses_total = exp_agg["total_amount"] or 0
        vendors_total = Vendor.objects.count()

        out["org"] = {
            "assets_total": assets_total,
            "assets_by_type": [
                {"asset_type__name": x.get("asset_type__name"), "count": x["count"]}
                for x in assets_by_type
            ],
            "bills_total_amount": _dec(bills_total),
            "bills_by_category": [
                {"category__name": x.get("category__name"), "total": _dec(x.get("total"))}
                for x in bills_by_category
            ],
            "expenses_total_amount": _dec(expenses_total),
            "vendors_total": vendors_total,
        }
    else:
        profile = _get_user_profile_object_sync(user)
        dept = None
        if profile and profile.Department:
            dept = profile.Department.dept_name

        assigned_rows = (
            TaskAssignies.objects.filter(assigned_to=user)
            .values("task__status__status_name")
            .annotate(n=Count("id"))
        )
        task_by_status = [
            {"status": r.get("task__status__status_name"), "count": r["n"]}
            for r in assigned_rows
        ]
        from accounts.models import LeaveApplicationData

        leave_qs = LeaveApplicationData.objects.filter(applicant=user)
        leave_total = leave_qs.count()

        out["personal"] = {
            "department": dept,
            "tasks_assigned_by_status": task_by_status,
            "leave_applications_total": leave_total,
        }

    return out
