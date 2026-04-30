from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from accounts.filters import _get_user_role_sync
from accounts.models import Profile
from task_management.models import Task, TaskAssignies

User = get_user_model()


def _normalize_status_name(status_name: str | None) -> str | None:
    """
    Map DB task status names to the normalized set expected by process_data.py:
    completed / inprogress / pending.
    """
    if not status_name:
        return None
    s = str(status_name).strip().upper()
    if s in {"COMPLETED", "COMPLETE", "DONE"}:
        return "completed"
    if s in {"INPROGRESS", "IN_PROGRESS", "INPROCESS", "IN_PROCESS"}:
        return "inprogress"
    if s in {"PENDING", "TODO", "TO_DO"}:
        return "pending"
    return None


def _process_tasks_like_repo(tasks: Iterable[Task]) -> dict:
    """
    Match the aggregation idea in AI-summray/md-ai-summary/services/process_data.py:
    compute total + counts by normalized status + completion_rate rounded to 2.
    """
    task_list = list(tasks)
    total = len(task_list)
    completed = 0
    inprogress = 0
    pending = 0
    for t in task_list:
        normalized = _normalize_status_name(getattr(getattr(t, "status", None), "status_name", None))
        if normalized == "completed":
            completed += 1
        elif normalized == "inprogress":
            inprogress += 1
        elif normalized == "pending":
            pending += 1

    completion_rate = (completed / total * 100) if total > 0 else 0
    return {
        "tasks_total": total,
        "tasks_completed": completed,
        "tasks_inprogress": inprogress,
        "tasks_pending": pending,
        "completion_rate": round(completion_rate, 2),
    }


def _get_user_tasks_qs(user: User) -> QuerySet[Task]:
    """
    "Own tasks" = tasks created by user + tasks assigned to user (deduped by task_id).
    """
    created_ids = list(Task.objects.filter(created_by=user).values_list("task_id", flat=True))
    assigned_ids = list(
        TaskAssignies.objects.filter(assigned_to=user).values_list("task_id", flat=True)
    )
    task_ids = set(created_ids) | set(assigned_ids)
    return Task.objects.filter(task_id__in=task_ids).select_related("status")


def _get_team_member_users(teamlead: User) -> list[User]:
    """
    Team membership uses existing Profile.Teamlead foreign key (team lead -> member profiles).
    """
    members = (
        Profile.objects.filter(Teamlead=teamlead)
        .select_related("Employee_id")
        .values_list("Employee_id", flat=True)
    )
    return list(User.objects.filter(username__in=list(members)))


def build_metrics_for_type(user: User, summary_type: str) -> tuple[dict, User | None]:
    """
    Returns (metrics, user_for_summary_row).
    - user_for_summary_row is nullable for org-wide md.
    """
    st = (summary_type or "").strip().lower()

    if st in {"intern", "employee"}:
        tasks_qs = _get_user_tasks_qs(user)
        return _process_tasks_like_repo(tasks_qs), user

    if st == "teamlead":
        role = (_get_user_role_sync(user) or "").strip()
        if role != "TeamLead":
            raise PermissionError("teamlead summary requires TeamLead role")
        member_users = _get_team_member_users(user)
        member_usernames = [u.username for u in member_users]
        tasks_qs = (
            Task.objects.filter(tasks__assigned_to__in=member_usernames)
            .distinct()
            .select_related("status")
        )
        return _process_tasks_like_repo(tasks_qs), user

    if st == "md":
        # Org-wide: all tasks.
        tasks_qs = Task.objects.all().select_related("status")
        return _process_tasks_like_repo(tasks_qs), None

    raise ValueError("invalid summary type")

