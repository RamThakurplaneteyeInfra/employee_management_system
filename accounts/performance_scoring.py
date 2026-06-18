"""
Combined employee performance score.

Default (non-MMR/RG): leave + meeting + checklist + certification + actionable co-author + actionable entries.
MMR/RG: leave (attendance) + certification + actionable co-author + customer panel entries only.
"""
from __future__ import annotations

from events.meeting_scoring import build_meeting_points
from projects_deadline.checklist_scoring import build_checklist_points
from certificates.certification_scoring import build_certification_points
from QuaterlyReports.actionable_coauthor_scoring import build_actionable_coauthor_points
from QuaterlyReports.actionable_entries_scoring import build_actionable_entries_points
from CustomerPanel.customer_panel_scoring import MMR_RG_FUNCTIONS, build_customer_panel_entries_points

from accounts.models import Profile

from .leave_scoring import build_leave_points


def _employee_functions(user) -> list[str]:
    profile = Profile.objects.filter(Employee_id=user).prefetch_related("functions").first()
    if profile is None:
        return []
    try:
        return sorted(
            {
                (f.function or "").strip()
                for f in profile.functions.all()
                if f is not None and getattr(f, "function", None)
            }
        )
    except Exception:
        return []


def _is_mmr_rg_user(user) -> bool:
    profile = Profile.objects.filter(Employee_id=user).prefetch_related("functions").first()
    if profile is None:
        return False
    try:
        names = {
            (f.function or "").strip().upper()
            for f in profile.functions.all()
            if f is not None and getattr(f, "function", None)
        }
    except Exception:
        return False
    return bool(names & MMR_RG_FUNCTIONS)


def build_performance_score(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    leave = build_leave_points(user, year, month=month, quarter=quarter)
    meeting = build_meeting_points(user, year, month=month, quarter=quarter)
    checklist = build_checklist_points(user, year, month=month, quarter=quarter)
    certification = build_certification_points(user, year, month=month, quarter=quarter)
    actionable_coauthor = build_actionable_coauthor_points(user, year, month=month, quarter=quarter)
    actionable_entries = build_actionable_entries_points(user, year, month=month, quarter=quarter)
    customer_panel_entries = build_customer_panel_entries_points(user, year, month=month, quarter=quarter)

    is_mmr_rg = _is_mmr_rg_user(user)
    if is_mmr_rg:
        combined_total = round(
            leave["total_points"]
            + certification["total_points"]
            + actionable_coauthor["total_points"]
            + customer_panel_entries["total_points"],
            2,
        )
        scoring_profile = "mmr_rg"
    else:
        combined_total = round(
            leave["total_points"]
            + meeting["total_points"]
            + checklist["total_points"]
            + certification["total_points"]
            + actionable_coauthor["total_points"]
            + actionable_entries["total_points"],
            2,
        )
        scoring_profile = "default"

    return {
        "employee_id": leave["employee_id"],
        "name": leave["name"],
        "role": leave["role"],
        "employee_functions": _employee_functions(user),
        "scoring_profile": scoring_profile,
        "period_type": leave["period_type"],
        "period": leave["period"],
        "period_range": leave["period_range"],
        "financial_year_start": leave["financial_year_start"],
        "year": leave["year"],
        "month": leave["month"],
        "quarter": leave["quarter"],
        "combined_total_points": combined_total,
        "leave": leave,
        "meeting": meeting,
        "checklist": checklist,
        "certification": certification,
        "actionable_coauthor": actionable_coauthor,
        "actionable_entries": actionable_entries,
        "customer_panel_entries": customer_panel_entries,
    }
