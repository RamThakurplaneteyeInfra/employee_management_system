"""
Combined employee performance score.

Default (non-MMR/RG): leave + meeting + checklist + certification + actionable co-author + actionable entries (main_score only; no bonus).
MMR/RG: leave + meeting + certification + actionable co-author + client profiles + customer panel entries (main_score only; no bonus).
Intern: leave + meeting + tasks (21 completed/month = 70 main) + certification + actionable co-author + actionable entries (no checklist).
HR: leave (max 8/mo) + meeting (max 7/mo) + certification (max 5/mo) individually, plus an
80-point work bucket: co-author (max 10/mo, individual) + org-average work (max 70/mo);
scoring_profile=hr_org_average.
"""
from __future__ import annotations

from events.meeting_scoring import build_meeting_points
from projects_deadline.checklist_scoring import build_checklist_points
from certificates.certification_scoring import build_certification_points
from QuaterlyReports.actionable_coauthor_scoring import build_actionable_coauthor_points
from QuaterlyReports.actionable_entries_scoring import build_actionable_entries_points
from CustomerPanel.customer_panel_scoring import MMR_RG_FUNCTIONS, build_customer_panel_entries_points
from Clients.client_profile_scoring import build_client_profile_points
from task_management.intern_task_scoring import INTERN_ROLE_NAME, build_intern_task_points

from accounts.models import Profile

from .leave_scoring import build_leave_points

NPD_HC_IP_FUNCTIONS = frozenset({"NPD", "HC", "IP"})
NPC_FUNCTIONS = frozenset({"NPC"})
HR_ORG_AVERAGE_EXCLUDE_ROLES = frozenset({"HR", "Hr", "MD", "Admin"})
HR_MONTHLY_LEAVE_CAP = 8.0
HR_MONTHLY_MEETING_CAP = 7.0
HR_MONTHLY_CERTIFICATION_CAP = 5.0
HR_MONTHLY_COAUTHOR_CAP = 10.0
HR_ORG_WORK_BUCKET_CAP_PER_MONTH = 80.0
HR_ORG_WORK_AVG_CAP_PER_MONTH = 70.0
PERFORMANCE_SCORES_VIEW_ROLES = frozenset({"HR", "Hr", "MD"})
SCORING_GROUP_ALIASES = {
    "mmr_rg": "mmr_rg",
    "mmr-rg": "mmr_rg",
    "npd_hc_ip": "npd_hc_ip",
    "npd-hc-ip": "npd_hc_ip",
    "npd": "npd_hc_ip",
    "hc": "npd_hc_ip",
    "ip": "npd_hc_ip",
    "npc": "npc",
    "interns": "interns",
    "intern": "interns",
    "other": "other",
    "others": "other",
    "default": "other",
}


# Omitted from nested category objects on combined performance-score (kept at root).
_PERFORMANCE_NESTED_COMMON_KEYS = frozenset({
    "employee_id",
    "name",
    "role",
    "period_type",
    "period",
    "period_range",
    "financial_year_start",
    "year",
    "month",
    "quarter",
    "months_in_period",
})


def _slim_category_payload(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in _PERFORMANCE_NESTED_COMMON_KEYS}


def _points_for_combined(category: dict) -> float:
    """Combined score uses main_score when present; bonus is excluded. Leave uses total_points."""
    if "main_score" in category:
        return float(category.get("main_score") or 0)
    return float(category.get("total_points") or 0)


def _bonus_for_combined(category: dict) -> float:
    return float(category.get("monthly_bonus") or 0)


def _sum_bonus(categories: list[dict]) -> float:
    return round(sum(_bonus_for_combined(c) for c in categories), 2)


def _bonus_breakdown(categories: dict[str, dict]) -> dict[str, float]:
    return {key: round(_bonus_for_combined(payload), 2) for key, payload in categories.items()}


def _org_pool_work_points_from_performance_score(score: dict) -> float:
    """Org-average pool: combined minus leave, meeting, certification, and co-author main."""
    leave_pts = float(score.get("leave", {}).get("total_points") or 0)
    meeting_pts = float(score.get("meeting", {}).get("main_score") or 0)
    cert_pts = float(score.get("certification", {}).get("main_score") or 0)
    coauthor_pts = float(score.get("actionable_coauthor", {}).get("main_score") or 0)
    combined = float(score.get("combined_total_points") or 0)
    return round(max(0.0, combined - leave_pts - meeting_pts - cert_pts - coauthor_pts), 2)


def _work_points_from_performance_score(score: dict) -> float:
    """Backward-compatible alias for org-pool work scoring."""
    return _org_pool_work_points_from_performance_score(score)


def _org_work_avg_cap_for_period(months_in_period: int) -> float:
    return round(HR_ORG_WORK_AVG_CAP_PER_MONTH * max(months_in_period, 1), 2)


def _org_work_bucket_cap_for_period(months_in_period: int) -> float:
    return round(HR_ORG_WORK_BUCKET_CAP_PER_MONTH * max(months_in_period, 1), 2)


def _hr_monthly_component_caps() -> dict[str, float]:
    return {
        "leave": HR_MONTHLY_LEAVE_CAP,
        "meeting": HR_MONTHLY_MEETING_CAP,
        "certification": HR_MONTHLY_CERTIFICATION_CAP,
        "actionable_coauthor": HR_MONTHLY_COAUTHOR_CAP,
        "org_work_average": HR_ORG_WORK_AVG_CAP_PER_MONTH,
        "org_work_bucket": HR_ORG_WORK_BUCKET_CAP_PER_MONTH,
    }


def _period_sample_fallback(year: int, month: int | None, quarter: int | None) -> dict:
    fallback_user = (
        Profile.objects.filter(Employee_id__is_active=True)
        .select_related("Employee_id")
        .first()
    )
    if fallback_user is not None:
        return build_leave_points(
            fallback_user.Employee_id,
            year,
            month=month,
            quarter=quarter,
        )
    return {
        "period_type": "month" if month is not None else ("quarter" if quarter else "year"),
        "period": str(year),
        "period_range": None,
        "financial_year_start": year if quarter is not None else None,
        "year": year,
        "month": month,
        "quarter": quarter,
        "months_in_period": 1 if month is not None else (3 if quarter else 12),
    }


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


def _is_intern_user(user) -> bool:
    profile = Profile.objects.filter(Employee_id=user).select_related("Role").first()
    if profile is None:
        return False
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)
    return (role_name or "").strip() == INTERN_ROLE_NAME


def _is_hr_user(user) -> bool:
    profile = Profile.objects.filter(Employee_id=user).select_related("Role").first()
    if profile is None:
        return False
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)
    return (role_name or "").strip() in ("HR", "Hr")


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


def _function_names_upper_from_profile(profile: Profile | None) -> set[str]:
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


def _is_intern_profile(profile: Profile | None) -> bool:
    if profile is None:
        return False
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)
    return (role_name or "").strip() == INTERN_ROLE_NAME


def _profile_matches_scoring_list_group(profile: Profile, group: str) -> bool:
    if group == "interns":
        return _is_intern_profile(profile)
    if _is_intern_profile(profile):
        return False
    function_names = _function_names_upper_from_profile(profile)
    return classify_scoring_group(function_names) == group


def classify_scoring_group(function_names_upper: set[str]) -> str:
    if function_names_upper & MMR_RG_FUNCTIONS:
        return "mmr_rg"
    if function_names_upper & NPD_HC_IP_FUNCTIONS:
        return "npd_hc_ip"
    if function_names_upper & NPC_FUNCTIONS:
        return "npc"
    return "other"


def parse_scoring_group(raw: str | None) -> str | None:
    key = (raw or "").strip().lower()
    if not key:
        return None
    return SCORING_GROUP_ALIASES.get(key)


def summarize_performance_score(full_score: dict) -> dict:
    return {
        "employee_id": full_score["employee_id"],
        "name": full_score["name"],
        "role": full_score["role"],
        "employee_functions": full_score["employee_functions"],
        "scoring_profile": full_score["scoring_profile"],
        "scoring_group": classify_scoring_group(
            {f.strip().upper() for f in full_score.get("employee_functions") or []}
        ),
        "combined_total_points": full_score["combined_total_points"],
        "combined_total_bonus": full_score["combined_total_bonus"],
        "bonus_by_category": full_score["bonus_by_category"],
    }


def profiles_queryset_for_org_average(*, branch: str | None = None):
    """Active employees included in the HR org-average pool (excludes HR, MD, Admin)."""
    qs = (
        Profile.objects.filter(Employee_id__is_active=True)
        .exclude(Role__role_name__in=HR_ORG_AVERAGE_EXCLUDE_ROLES)
        .select_related("Role", "Employee_id", "Branch")
        .prefetch_related("functions")
    )
    branch_name = (branch or "").strip()
    if branch_name:
        qs = qs.filter(Branch__branch_name__iexact=branch_name)
    return qs


def build_org_average_work_score(
    year: int,
    month: int | None = None,
    quarter: int | None = None,
    *,
    branch: str | None = None,
) -> dict:
    """
    Average work-only main points across active employees (excluding HR, MD, Admin).
    Work = combined minus leave, meeting, certification, and co-author main.
    Capped at 70/month (the org-average portion of the 80-point work bucket).
    """
    work_scores: list[float] = []
    bonuses: list[float] = []
    period_sample: dict | None = None

    for profile in profiles_queryset_for_org_average(branch=branch):
        score = _compute_individual_performance_score(
            profile.Employee_id, year, month=month, quarter=quarter
        )
        work_scores.append(_org_pool_work_points_from_performance_score(score))
        bonuses.append(score["combined_total_bonus"])
        if period_sample is None:
            period_sample = score

    count = len(work_scores)
    if period_sample is None:
        period_sample = _period_sample_fallback(year, month, quarter)

    months_in_period = int(period_sample.get("months_in_period") or 1)
    work_avg_cap = _org_work_avg_cap_for_period(months_in_period)
    work_bucket_cap = _org_work_bucket_cap_for_period(months_in_period)
    avg_work = round(sum(work_scores) / count, 2) if count else 0.0
    avg_bonus = round(sum(bonuses) / count, 2) if count else 0.0
    applied_work = round(min(avg_work, work_avg_cap), 2)
    branch_name = (branch or "").strip() or None

    return {
        "scoring_profile": "hr_org_average",
        "period_type": period_sample["period_type"],
        "period": period_sample["period"],
        "period_range": period_sample["period_range"],
        "financial_year_start": period_sample["financial_year_start"],
        "year": period_sample["year"],
        "month": period_sample["month"],
        "quarter": period_sample["quarter"],
        "months_in_period": months_in_period,
        "average_org_work_points": avg_work,
        "org_work_points_applied": applied_work,
        "org_work_cap": work_avg_cap,
        "org_work_bucket_cap": work_bucket_cap,
        "monthly_component_caps": _hr_monthly_component_caps(),
        "average_combined_total_points": applied_work,
        "average_combined_total_bonus": avg_bonus,
        "employee_count": count,
        "excluded_roles": sorted(HR_ORG_AVERAGE_EXCLUDE_ROLES),
        "branch": branch_name,
    }


def build_org_average_performance_score(
    year: int,
    month: int | None = None,
    quarter: int | None = None,
    *,
    branch: str | None = None,
) -> dict:
    """Org-average work component used for HR scoring (see build_org_average_work_score)."""
    return build_org_average_work_score(year, month, quarter, branch=branch)


def build_hr_performance_score(
    hr_user,
    year: int,
    month: int | None = None,
    quarter: int | None = None,
    *,
    branch: str | None = None,
) -> dict:
    """
    HR score = own leave + meeting + certification + co-author (main) + capped org-average work.
    Monthly framework: 8 + 7 + 5 + 10 + 70 = 100 main at full performance.
    """
    leave = build_leave_points(hr_user, year, month=month, quarter=quarter)
    meeting = build_meeting_points(hr_user, year, month=month, quarter=quarter)
    certification = build_certification_points(hr_user, year, month=month, quarter=quarter)
    actionable_coauthor = build_actionable_coauthor_points(
        hr_user, year, month=month, quarter=quarter
    )
    org_avg = build_org_average_work_score(year, month, quarter, branch=branch)

    profile = Profile.objects.filter(Employee_id=hr_user).select_related("Role").first()
    display_name = (getattr(profile, "Name", None) or hr_user.username) if profile else hr_user.username
    role_name = getattr(getattr(profile, "Role", None), "role_name", None)

    hr_core_individual = round(
        _points_for_combined(leave)
        + _points_for_combined(meeting)
        + _points_for_combined(certification),
        2,
    )
    coauthor_main = round(_points_for_combined(actionable_coauthor), 2)
    hr_individual = round(hr_core_individual + coauthor_main, 2)
    combined_total = round(hr_individual + org_avg["org_work_points_applied"], 2)

    bonus_categories = {
        "meeting": meeting,
        "certification": certification,
        "actionable_coauthor": actionable_coauthor,
    }
    combined_total_bonus = _sum_bonus(list(bonus_categories.values()))

    empty_category = {"main_score": 0.0, "monthly_bonus": 0.0, "total_points": 0.0}

    return {
        "employee_id": hr_user.username,
        "name": display_name,
        "role": role_name,
        "employee_functions": _employee_functions(hr_user),
        "scoring_profile": "hr_org_average",
        "hr_core_individual_points": hr_core_individual,
        "hr_coauthor_points": coauthor_main,
        "hr_individual_points": hr_individual,
        "org_average_work_points": org_avg["average_org_work_points"],
        "org_work_points_applied": org_avg["org_work_points_applied"],
        "org_work_cap": org_avg["org_work_cap"],
        "org_work_bucket_cap": org_avg["org_work_bucket_cap"],
        "monthly_component_caps": org_avg["monthly_component_caps"],
        "derived_from_employee_count": org_avg["employee_count"],
        "excluded_roles": org_avg["excluded_roles"],
        "branch": org_avg["branch"],
        "period_type": org_avg["period_type"],
        "period": org_avg["period"],
        "period_range": org_avg["period_range"],
        "financial_year_start": org_avg["financial_year_start"],
        "year": org_avg["year"],
        "month": org_avg["month"],
        "quarter": org_avg["quarter"],
        "months_in_period": org_avg["months_in_period"],
        "combined_total_points": combined_total,
        "combined_total_bonus": combined_total_bonus,
        "bonus_by_category": _bonus_breakdown(bonus_categories),
        "leave": _slim_category_payload(leave),
        "meeting": _slim_category_payload(meeting),
        "certification": _slim_category_payload(certification),
        "checklist": empty_category,
        "tasks": empty_category,
        "actionable_coauthor": _slim_category_payload(actionable_coauthor),
        "actionable_entries": empty_category,
        "customer_panel_entries": empty_category,
        "client_profiles": empty_category,
    }


def profiles_queryset_for_scoring_list(viewer, get_user_role, *, branch: str | None = None):
    if not viewer or not viewer.is_authenticated:
        return None
    role = (get_user_role(viewer) or "").strip()
    if role not in PERFORMANCE_SCORES_VIEW_ROLES:
        return None

    qs = (
        Profile.objects.filter(Employee_id__is_active=True)
        .select_related("Role", "Employee_id", "Branch")
        .prefetch_related("functions")
        .order_by("Name")
    )
    branch_name = (branch or "").strip()
    if branch_name:
        qs = qs.filter(Branch__branch_name__iexact=branch_name)
    return qs


def build_performance_scores_list(
    group: str,
    viewer,
    get_user_role,
    year: int,
    month: int | None = None,
    quarter: int | None = None,
    *,
    branch: str | None = None,
) -> dict | None:
    profiles_qs = profiles_queryset_for_scoring_list(viewer, get_user_role, branch=branch)
    if profiles_qs is None:
        return None

    employees: list[dict] = []
    period_sample: dict | None = None

    for profile in profiles_qs:
        if not _profile_matches_scoring_list_group(profile, group):
            continue
        full_score = build_performance_score(profile.Employee_id, year, month=month, quarter=quarter)
        if period_sample is None:
            period_sample = full_score
        employees.append(summarize_performance_score(full_score))

    employees.sort(
        key=lambda row: (row["combined_total_points"], row["combined_total_bonus"]),
        reverse=True,
    )

    if period_sample is None:
        period_sample = build_leave_points(viewer, year, month=month, quarter=quarter)

    return {
        "group": group,
        "period_type": period_sample["period_type"],
        "period": period_sample["period"],
        "period_range": period_sample["period_range"],
        "financial_year_start": period_sample["financial_year_start"],
        "year": period_sample["year"],
        "month": period_sample["month"],
        "quarter": period_sample["quarter"],
        "months_in_period": period_sample["months_in_period"],
        "count": len(employees),
        "employees": employees,
    }


def build_performance_score(
    user,
    year: int,
    month: int | None = None,
    quarter: int | None = None,
    *,
    branch: str | None = None,
) -> dict:
    if _is_hr_user(user):
        return build_hr_performance_score(
            user, year, month=month, quarter=quarter, branch=branch
        )
    return _compute_individual_performance_score(
        user, year, month=month, quarter=quarter
    )


def _compute_individual_performance_score(
    user, year: int, month: int | None = None, quarter: int | None = None
) -> dict:
    leave = build_leave_points(user, year, month=month, quarter=quarter)
    meeting = build_meeting_points(user, year, month=month, quarter=quarter)
    checklist = build_checklist_points(user, year, month=month, quarter=quarter)
    certification = build_certification_points(user, year, month=month, quarter=quarter)
    actionable_coauthor = build_actionable_coauthor_points(user, year, month=month, quarter=quarter)
    actionable_entries = build_actionable_entries_points(user, year, month=month, quarter=quarter)
    customer_panel_entries = build_customer_panel_entries_points(user, year, month=month, quarter=quarter)
    client_profiles = build_client_profile_points(user, year, month=month, quarter=quarter)
    intern_tasks = build_intern_task_points(user, year, month=month, quarter=quarter)

    is_mmr_rg = _is_mmr_rg_user(user)
    is_intern = _is_intern_user(user)
    if is_mmr_rg:
        combined_categories = {
            "meeting": meeting,
            "certification": certification,
            "actionable_coauthor": actionable_coauthor,
            "client_profiles": client_profiles,
            "customer_panel_entries": customer_panel_entries,
        }
        combined_total = round(
            _points_for_combined(leave)
            + sum(_points_for_combined(c) for c in combined_categories.values()),
            2,
        )
        combined_total_bonus = _sum_bonus(list(combined_categories.values()))
        scoring_profile = "mmr_rg"
    elif is_intern:
        combined_categories = {
            "meeting": meeting,
            "tasks": intern_tasks,
            "certification": certification,
            "actionable_coauthor": actionable_coauthor,
            "actionable_entries": actionable_entries,
        }
        combined_total = round(
            _points_for_combined(leave)
            + sum(_points_for_combined(c) for c in combined_categories.values()),
            2,
        )
        combined_total_bonus = _sum_bonus(list(combined_categories.values()))
        scoring_profile = "intern"
    else:
        combined_categories = {
            "meeting": meeting,
            "checklist": checklist,
            "certification": certification,
            "actionable_coauthor": actionable_coauthor,
            "actionable_entries": actionable_entries,
        }
        combined_total = round(
            _points_for_combined(leave)
            + sum(_points_for_combined(c) for c in combined_categories.values()),
            2,
        )
        combined_total_bonus = _sum_bonus(list(combined_categories.values()))
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
        "months_in_period": leave["months_in_period"],
        "combined_total_points": combined_total,
        "combined_total_bonus": combined_total_bonus,
        "bonus_by_category": _bonus_breakdown(combined_categories),
        "leave": _slim_category_payload(leave),
        "meeting": _slim_category_payload(meeting),
        "checklist": _slim_category_payload(checklist),
        "tasks": _slim_category_payload(intern_tasks),
        "certification": _slim_category_payload(certification),
        "actionable_coauthor": _slim_category_payload(actionable_coauthor),
        "actionable_entries": _slim_category_payload(actionable_entries),
        "customer_panel_entries": _slim_category_payload(customer_panel_entries),
        "client_profiles": _slim_category_payload(client_profiles),
    }
