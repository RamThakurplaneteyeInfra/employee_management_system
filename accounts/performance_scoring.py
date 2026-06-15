"""
Combined employee performance score: leave + meeting + checklist points.
"""
from __future__ import annotations

from events.meeting_scoring import build_meeting_points
from projects_deadline.checklist_scoring import build_checklist_points

from .leave_scoring import build_leave_points


def build_performance_score(user, year: int, month: int | None = None, quarter: int | None = None) -> dict:
    leave = build_leave_points(user, year, month=month, quarter=quarter)
    meeting = build_meeting_points(user, year, month=month, quarter=quarter)
    checklist = build_checklist_points(user, year, month=month, quarter=quarter)
    combined_total = round(
        leave["total_points"] + meeting["total_points"] + checklist["total_points"],
        2,
    )

    return {
        "employee_id": leave["employee_id"],
        "name": leave["name"],
        "role": leave["role"],
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
    }
