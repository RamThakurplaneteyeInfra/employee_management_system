from asgiref.sync import sync_to_async
from django.http import HttpRequest, JsonResponse
from accounts.models import Profile
from django.db.models import Q, F, Count
from django.contrib.postgres.aggregates import ArrayAgg
from rest_framework import status
from accounts.filters import (
    _get_users_Name_sync,
    _get_role_object_sync,
    _get_designation_object_sync,
)
from task_management.models import *
from datetime import date

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
# ==================== get_tasks_by_type ====================
# endpoint for "Created_Tasks"-{{baseurl}}/tasks/viewTasks/?type=
# endpoint for "Assigned_Reported"-{{baseurl}}/tasks/viewAssignedTasks/?type=
def _get_tasks_by_type_sync(request: HttpRequest, type: str = "all", self_created: bool = True, Date=None):
    if type.lower() == "all" and self_created:
        tasks=Task.objects.filter(created_by=request.user).select_related("status","type","created_by").annotate(Task_id=F('task_id'),Title=F('title'),
                                    Description=F('description'),Status=F('status__status_name'),
                                    Created_by=F('created_by__accounts_profile__Name'),Report_to=F("created_by__accounts_profile__Name"),Assigned_to=ArrayAgg("assignees__accounts_profile__Name", distinct=True),
                                    Due_date=F('due_date'),Created_at=F('created_at'),
                                    Task_type=F('type__type_name')).values('Task_id', 'Title', 'Description', 'Status','Created_by', 'Report_to', 'Due_date', 'Created_at', 'Task_type',"Assigned_to")
        task_data = [{
            **item,
            "Due_date": item['Due_date'].strftime("%d/%m/%Y"),
            "Created_at": item['Created_at'].strftime("%d/%m/%Y")}for item in tasks]
        
        return task_data

    elif type and self_created:
        type_obj = _get_taskTypes_object_sync(type_name=type)
        if not type_obj:
            return [{"message": "Invalid task type"}]
        tasks=Task.objects.filter(created_by=request.user,type=type_obj).select_related("status","type","created_by").annotate(Task_id=F('task_id'),Title=F('title'),
                                    Description=F('description'),Status=F('status__status_name'),
                                    Created_by=F('created_by__accounts_profile__Name'),Report_to=F("created_by__accounts_profile__Name"),Assigned_to=ArrayAgg("assignees__accounts_profile__Name", distinct=True),
                                    Due_date=F('due_date'),Created_at=F('created_at'),
                                    Task_type=F('type__type_name')).values('Task_id', 'Title', 'Description', 'Status','Created_by', 'Report_to', 'Due_date', 'Created_at', 'Task_type',"Assigned_to")
        
        task_data = [{
            **item,
            "Due_date": item['Due_date'].strftime("%d/%m/%Y"),
            "Created_at": item['Created_at'].strftime("%d/%m/%Y")}for item in tasks]
        
        return task_data

    elif type.lower() == "all" and not self_created:
        tasks = TaskAssignies.objects.filter(assigned_to=request.user).annotate(Task_id=F('task__task_id'),Title=F('task__title'),
                                    Description=F('task__description'),Status=F('task__status__status_name'),
                                    Created_by=F('task__created_by__accounts_profile__Name'),Report_to=F("task__created_by__accounts_profile__Name"),
                                    Due_date=F('task__due_date'),Created_at=F('task__created_at'),
                                    Task_type=F('task__type__type_name')).values('Task_id', 'Title', 'Description', 'Status','Created_by', 'Report_to', 'Due_date', 'Created_at', 'Task_type')
        
        task_data = [{
        **item,
        "Due_date": item['Due_date'].strftime("%d/%m/%Y"),
        "Created_at": item['Created_at'].strftime("%d/%m/%Y")}for item in tasks]
            
        return task_data
    
    elif type and not self_created:
        Task_assignee=TaskAssignies.objects.select_related("task","task__status","task__type","task__created_by").filter(assigned_to=request.user)
        task_data=[]
        for task in Task_assignee:
            task_obj = task.task
            users_name = _get_users_Name_sync(task_obj.created_by)
            # if task_obj.type.type_name==type and task_obj.created_at.date()==current_date:
            tasks= TaskAssignies.objects.filter(assigned_to=request.user).annotate(Task_id=F('task__task_id'),Title=F('task__title'),
                                    Description=F('task__description'),Status=F('task__status__status_name'),
                                    Created_by=F('task__created_by__accounts_profile__Name'),Report_to=F("task__created_by__accounts_profile__Name"),
                                    Due_date=F('task__due_date'),Created_at=F('task__created_at'),
                                    Task_type=F('task__type__type_name')).values('Task_id', 'Title', 'Description', 'Status','Created_by', 'Report_to', 'Due_date', 'Created_at', 'Task_type')
        
            task_data = [{
            **item,
            "Due_date": item['Due_date'].strftime("%d/%m/%Y"),
            "Created_at": item['Created_at'].strftime("%d/%m/%Y")}for item in tasks]

    else:
        tasks = [{"message": "Incorrect type for tasks"}]

    return JsonResponse(tasks, safe=False, status=status.HTTP_200_OK)


async def get_tasks_by_type(request: HttpRequest, type: str = "all", self_created: bool = True, Date=None):
    return await sync_to_async(_get_tasks_by_type_sync)(request, type, self_created, Date)