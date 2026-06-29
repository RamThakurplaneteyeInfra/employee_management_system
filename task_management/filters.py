from datetime import datetime

from django.utils import timezone

from ems.RequiredImports import (
    sync_to_async,
    HttpRequest,
    JsonResponse,
    Q,
    F,
    Count,
    ArrayAgg,
    status,
    date,
)
from accounts.models import Profile
from accounts.filters import (
    _get_users_Name_sync,
    _get_role_object_sync,
    _get_designation_object_sync,
)
from task_management.models import *
from ems.utils import gmt_to_ist_str

# # # # # #  baseurl="http://localhost:8000" # # # # # # # # # # # #
# https://docs.djangoproject.com/en/stable/ref/models/querysets/


# ==================== get_task_object ====================
def _get_task_object_sync(task_id: int):
    try:
        return Task.objects.get(task_id=task_id)
    except Exception:
        return None


# ==================== get_taskTypes_object ====================
def _get_taskTypes_object_sync(type_name: str):
    try:
        return TaskTypes.objects.get(type_name=type_name)
    except Exception:
        return None


async def get_taskTypes_object(type_name: str):
    return await sync_to_async(_get_taskTypes_object_sync)(type_name)


# ==================== get_taskStatus_object ====================
def _get_taskStatus_object_sync(status_name: str):
    try:
        return TaskStatus.objects.get(status_name=status_name)
    except Exception:
        return None


async def get_taskStatus_object(status_name: str):
    return await sync_to_async(_get_taskStatus_object_sync)(status_name)


# ==================== get_task_object (sync, used by views) ====================
def get_task_object(task_id: int):
    return _get_task_object_sync(task_id)


# ==================== get_Names_from_selected_role_and_desigantion ====================
# endpoint-{{baseurl}}/tasks/getNamesfromRoleandDesignation/
# Use in the dropdown of field "Assigned_to" while assigning/ creating tasks.
def _get_Names_from_selected_role_and_desigantion_sync(request: HttpRequest):
    designation = request.GET.get("designation")
    role = request.GET.get("role")
    try:
        if not request.user:
            return JsonResponse({"error": "login required"}, status=404)
        if not role and not designation:
            names = Profile.objects.exclude(Employee_id=request.user).order_by("Name").values("Name")
        elif role and not designation:
            passed_role = _get_role_object_sync(role=role)
            if isinstance(passed_role, dict):
                return JsonResponse({"message": passed_role.get("message", "Invalid role")}, status=status.HTTP_404_NOT_FOUND)
            names = Profile.objects.select_related("Role").exclude(Employee_id=request.user).filter(Role=passed_role).order_by("Name").values("Name")
        elif designation and not role:
            passed_designation = _get_designation_object_sync(designation=designation)
            if isinstance(passed_designation, dict):
                return JsonResponse({"message": passed_designation.get("message", "Invalid designation")}, status=status.HTTP_404_NOT_FOUND)
            names = Profile.objects.select_related("Designation").exclude(Employee_id=request.user).filter(Designation=passed_designation).order_by("Name").values("Name")
        elif role and designation:
            passed_role = _get_role_object_sync(role=role)
            passed_designation = _get_designation_object_sync(designation=designation)
            if isinstance(passed_role, dict) or isinstance(passed_designation, dict):
                return JsonResponse({"message": "Invalid role or designation"}, status=status.HTTP_404_NOT_FOUND)
            names = Profile.objects.select_related("Role", "Designation").exclude(Employee_id=request.user).filter(Role=passed_role, Designation=passed_designation).order_by("Name").values("Name")
        else:
            return JsonResponse({"message": "pass the correct designation or Role to filter names"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
    return JsonResponse(list(names), status=status.HTTP_200_OK, safe=False)


async def get_Names_from_selected_role_and_desigantion(request: HttpRequest):
    return await sync_to_async(_get_Names_from_selected_role_and_desigantion_sync)(request)

# ==================== get_types ====================
# endpoint-{{baseurl}}/tasks/getTaskTypes/
def _get_types_sync(request: HttpRequest):
    task_types = TaskTypes.objects.all().values("type_name")
    return JsonResponse(list(task_types), safe=False)


async def get_types(request: HttpRequest):
    return await sync_to_async(_get_types_sync)(request)


# ==================== get_assignees ====================
def _get_assignees_sync(task: Task):
    try:
        return TaskAssignies.objects.filter(task=task).select_related("assigned_to").annotate(assignee=F("assigned_to__accounts_profile__Name")).values("assignee")
    except Exception:
        return None


def get_assignees(task: Task):
    return _get_assignees_sync(task)


# ==================== get_default_task_status ====================
def _get_default_task_status_sync():
    return _get_taskStatus_object_sync(status_name="PENDING")


# ==================== get_all_TaskStatuses ====================
def _get_all_TaskStatuses_sync(request: HttpRequest):
    values = TaskStatus.objects.all().values("status_name")
    return JsonResponse(list(values), safe=False, status=status.HTTP_200_OK)


async def get_all_TaskStatuses(request: HttpRequest):
    return await sync_to_async(_get_all_TaskStatuses_sync)(request)
def _task_item_to_response(item, assigned_to=None, completed_at_map=None, unseen_count=None):
    """Build a consistent task response dict. Assigned_to is list of {name, role}. completed_At is IST last_edit when Status is COMPLETED else None. unseen_count is per-assignee task message count (0 for creator in viewTasks)."""
    if assigned_to is None:
        assigned_to = item.get("Assigned_to") if item.get("Assigned_to") is not None else []
    if not isinstance(assigned_to, list):
        assigned_to = list(assigned_to) if assigned_to else []
    # Normalize to list of {name, role}
    normalized = []
    for x in assigned_to:
        if isinstance(x, dict) and "name" in x:
            normalized.append({"name": x.get("name", ""), "role": x.get("role")})
        else:
            normalized.append({"name": str(x) if x else "", "role": None})
    task_id = item["Task_id"]
    status = item.get("Status")
    is_completed = status and str(status).upper() == "COMPLETED"
    last_edit_dt = (completed_at_map or {}).get(task_id) if completed_at_map else None
    completed_At = gmt_to_ist_str(last_edit_dt, "%d/%m/%Y %H:%M:%S") if is_completed and last_edit_dt else None
    return {
        "Task_id": task_id,
        "Title": item["Title"],
        "Description": item["Description"],
        "Status": status,
        "Created_by": item["Created_by"],
        "Report_to": item["Report_to"],
        "Assigned_to": normalized,
        "Due_date": item["Due_date"].strftime("%d/%m/%Y"),
        "Created_at": gmt_to_ist_str(item["Created_at"], "%d/%m/%Y %H:%M:%S"),
        "Task_type": item["Task_type"],
        "completed_At": completed_At,
        "unseen_count": unseen_count if unseen_count is not None else 0,
    }


def _get_assignee_names_by_task_id(task_ids):
    """Return dict mapping task_id -> list of assignee names (from Profile.Name)."""
    if not task_ids:
        return {}
    rows = (
        TaskAssignies.objects.filter(task_id__in=task_ids)
        .order_by("task_id")
        .values("task_id")
        .annotate(names=ArrayAgg("assigned_to__accounts_profile__Name", distinct=True))
    )
    return {r["task_id"]: (r.get("names") or []) for r in rows}


def _get_assignee_names_and_roles_by_task_id(task_ids):
    """Return dict mapping task_id -> list of {name, role} for assignees (Profile.Name, Role.role_name)."""
    if not task_ids:
        return {}
    rows = (
        TaskAssignies.objects.filter(task_id__in=task_ids)
        .select_related("assigned_to__accounts_profile__Role")
        .order_by("task_id")
    )
    out = {}
    for r in rows:
        task_id = r.task_id
        if task_id not in out:
            out[task_id] = []
        profile = getattr(r.assigned_to, "accounts_profile", None)
        name = profile.Name if profile else getattr(r.assigned_to, "username", "")
        role = profile.Role.role_name if profile and profile.Role else None
        out[task_id].append({"name": name or "", "role": role})
    return out


def _get_unseen_count_map(task_ids, user):
    """Return dict task_id -> unseen_count for the given user (from TaskAssignies). Used for viewTasks/viewAssignedTasks."""
    if not task_ids or not user:
        return {}
    rows = TaskAssignies.objects.filter(task_id__in=task_ids, assigned_to=user).values("task_id", "unseen_count")
    return {r["task_id"]: r["unseen_count"] for r in rows}


def _get_completed_at_map(task_list):
    """Return dict task_id -> last_edit datetime for tasks with Status COMPLETED (from TaskStatusChangeLogs)."""
    completed_ids = [
        item["Task_id"]
        for item in task_list
        if item.get("Status") and str(item["Status"]).upper() == "COMPLETED"
    ]
    if not completed_ids:
        return {}
    rows = TaskStatusChangeLogs.objects.filter(task_id__in=completed_ids).values("task_id", "last_edit")
    return {r["task_id"]: r["last_edit"] for r in rows}


def _ist_month_datetime_range(year: int, month: int):
    """Inclusive start and exclusive end for a calendar month in Asia/Kolkata."""
    tz = timezone.get_current_timezone()
    start = datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, tz)
    if timezone.is_naive(end):
        end = timezone.make_aware(end, tz)
    return start, end


def _parse_task_month_year(request: HttpRequest):
    """
    Optional ?month= (1-12) and ?year= (defaults to current year).
    When month is omitted, no created_at filter is applied (backward-compatible).
    """
    raw_month = request.GET.get("month")
    if raw_month is None:
        return None
    try:
        month_val = int(raw_month)
        if not (1 <= month_val <= 12):
            return None
    except (TypeError, ValueError):
        return None
    raw_year = request.GET.get("year")
    try:
        year_val = int(raw_year) if raw_year is not None else date.today().year
    except (TypeError, ValueError):
        year_val = date.today().year
    return year_val, month_val


def _parse_task_pagination_params(request: HttpRequest):
    """
    Optional limit/offset pagination (backward-compatible).
    Enabled when either query param is present.
    """
    raw_limit = request.GET.get("limit")
    raw_offset = request.GET.get("offset")
    paginate_enabled = raw_limit is not None or raw_offset is not None
    if not paginate_enabled:
        return 0, 0, False

    default_limit = 30
    max_limit = 100
    try:
        limit = int(raw_limit) if raw_limit is not None else default_limit
    except (TypeError, ValueError):
        limit = default_limit
    try:
        offset = int(raw_offset) if raw_offset is not None else 0
    except (TypeError, ValueError):
        offset = 0
    if limit < 1:
        limit = default_limit
    if limit > max_limit:
        limit = max_limit
    if offset < 0:
        offset = 0
    return limit, offset, True


def _tasks_paginated_response(items, total: int, limit: int, offset: int):
    next_offset = offset + limit if (offset + limit) < total else None
    prev_offset = offset - limit if offset - limit >= 0 else None
    return {
        "items": items,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "next_offset": next_offset,
            "prev_offset": prev_offset,
            "has_next": next_offset is not None,
            "has_prev": offset > 0,
        },
    }


def _apply_created_at_month_filter(qs, month_year):
    if month_year is None:
        return qs
    year_val, month_val = month_year
    start, end = _ist_month_datetime_range(year_val, month_val)
    return qs.filter(created_at__gte=start, created_at__lt=end)


def _annotate_task_list_queryset(qs):
    return (
        qs.select_related("status", "type", "created_by")
        .annotate(
            Task_id=F("task_id"),
            Title=F("title"),
            Description=F("description"),
            Status=F("status__status_name"),
            Created_by=F("created_by__accounts_profile__Name"),
            Report_to=F("created_by__accounts_profile__Name"),
            Due_date=F("due_date"),
            Created_at=F("created_at"),
            Task_type=F("type__type_name"),
        )
        .order_by("-created_at", "due_date")
        .values(
            "Task_id",
            "Title",
            "Description",
            "Status",
            "Created_by",
            "Report_to",
            "Due_date",
            "Created_at",
            "Task_type",
        )
    )


def _format_task_list_response(task_list, user, *, limit, offset, paginate_enabled, total=None):
    task_ids = [t["Task_id"] for t in task_list]
    assignee_map = _get_assignee_names_and_roles_by_task_id(task_ids)
    completed_at_map = _get_completed_at_map(task_list)
    unseen_count_map = _get_unseen_count_map(task_ids, user)
    items = [
        _task_item_to_response(
            item,
            assigned_to=assignee_map.get(item["Task_id"], []),
            completed_at_map=completed_at_map,
            unseen_count=unseen_count_map.get(item["Task_id"], 0),
        )
        for item in task_list
    ]
    if paginate_enabled:
        return _tasks_paginated_response(items, total if total is not None else len(items), limit, offset)
    return items


# ==================== get_tasks_by_type ====================
# endpoint for "Created_Tasks"-{{baseurl}}/tasks/viewTasks/?type=
# endpoint for "Assigned_Reported"-{{baseurl}}/tasks/viewAssignedTasks/?type=
# Optional: ?month=1-12&year=YYYY (IST created_at), ?limit=&offset=
def _get_tasks_by_type_sync(request: HttpRequest, type: str = "all", self_created: bool = True, Date=None):
    if type is None:
        type = "all"

    month_year = _parse_task_month_year(request)
    limit, offset, paginate_enabled = _parse_task_pagination_params(request)

    if type.lower() != "all":
        type_obj = _get_taskTypes_object_sync(type_name=type)
        if not type_obj:
            return [{"message": "Invalid task type"}]
    else:
        type_obj = None

    if self_created:
        qs = Task.objects.filter(created_by=request.user)
    else:
        qs = Task.objects.filter(assignees=request.user).distinct()

    if type_obj is not None:
        qs = qs.filter(type=type_obj)

    qs = _apply_created_at_month_filter(qs, month_year)
    qs = _annotate_task_list_queryset(qs)

    if paginate_enabled:
        total = qs.count()
        task_list = list(qs[offset : offset + limit])
        return _format_task_list_response(
            task_list,
            request.user,
            limit=limit,
            offset=offset,
            paginate_enabled=True,
            total=total,
        )

    task_list = list(qs)
    return _format_task_list_response(
        task_list,
        request.user,
        limit=limit,
        offset=offset,
        paginate_enabled=False,
    )


async def get_tasks_by_type(request: HttpRequest, type: str = "all", self_created: bool = True, Date=None):
    return await sync_to_async(_get_tasks_by_type_sync)(request, type, self_created, Date)