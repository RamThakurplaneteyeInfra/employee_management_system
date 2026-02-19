from asgiref.sync import sync_to_async
from accounts.filters import _get_user_role_sync
from .filters import (
    get_task_object,
    _get_taskTypes_object_sync,
    _get_taskStatus_object_sync,
    get_tasks_by_type,
    get_Names_from_selected_role_and_desigantion,
    get_types,
    get_all_TaskStatuses,
)
from .models import *
from ems.verify_methods import *

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #


# ==================== home ====================
# Tasks home page.
# URL: {{baseurl}}/tasks/
# Method: GET
@login_required
async def home(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    else:
        return JsonResponse({"message": "You are at tasks page"}, status=status.HTTP_200_OK)


# ==================== create_task ====================
# Create a new task.
# URL: {{baseurl}}/tasks/createTask/
# Method: POST
def _create_task_sync(user, data):
    body_data = {k: data.get(k) for k in ["title", "description", "due_date", "type"] if data.get(k)}
    body_data["type"] = get_object_or_404(TaskTypes, type_name=data["type"])
    body_data["created_by"] = user
    assignees = data.get("assigned_to", [])
    task = Task.objects.create(**body_data)
    for userid in assignees:
        u = get_object_or_404(User, username=userid)
        TaskAssignies.objects.create(task=task, assigned_to=u)


@csrf_exempt
@login_required
async def create_task(request: HttpRequest):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    data = load_data(request)
    for f in ["title", "description", "due_date", "assigned_to", "type"]:
        if not data.get(f):
            return JsonResponse({"error": f"{f} is required"}, status=status.HTTP_206_PARTIAL_CONTENT)
    try:
        await sync_to_async(_create_task_sync)(request.user, data)
        return JsonResponse({"message": "Task created"}, status=status.HTTP_201_CREATED)
    except (Http404, Exception) as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_403_FORBIDDEN)


# ==================== update_task ====================
# Update a task by task_id.
# URL: {{baseurl}}/tasks/updateTask/<task_id>/
# Method: PATCH
def _update_task_sync(user, task_id, data):
    task = get_task_object(task_id=task_id)
    if user != task.created_by:
        raise PermissionDenied("Not allowed")
    for i in ["title", "description", "due_date", "type"]:
        fv = data.get(i)
        if fv and i == "type":
            setattr(task, i, _get_taskTypes_object_sync(type_name=fv))
        elif fv and i in ["due_date", "description", "title"]:
            setattr(task, i, fv)
    task.save()


# Update a particular Task. applicable method-"POST",insert path parameter "task_id" of type integer. 
# endpoint-{{baseurl}}/tasks/{task_id}/updateTask/
@csrf_exempt
@login_required
async def update_task(request, task_id: int):
    verify_method = verifyPatch(request)
    if verify_method:
        return verify_method
    try:
        data = load_data(request)
        await sync_to_async(_update_task_sync)(request.user, task_id, data)
        return JsonResponse({"message": "Task updated successfully"}, status=status.HTTP_200_OK)
    except PermissionDenied:
        return JsonResponse({"message": "you cannot update or edit this task"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_404_NOT_FOUND)


# ==================== show_created_tasks ====================
# Show self-created tasks.
# URL: {{baseurl}}/tasks/viewTasks/?type=
# Method: GET
@login_required
async def show_created_tasks(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    try:
        t = request.GET.get("type")
        response = await get_tasks_by_type(request=request, type=t) if t in ["all", "SOS", "1 Day", "10 Day", "Monthly", "Quaterly"] else await get_tasks_by_type(request)
        return JsonResponse(response, safe=False)
    except Exception as e:
        return JsonResponse({"msg": f"{e}"})


# ==================== show_assigned_tasks ====================
# Show assigned tasks by other users.
# URL: {{baseurl}}/tasks/viewAssignedTasks/?type=
# Method: GET
@login_required
async def show_assigned_tasks(request: HttpRequest):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        t = request.GET.get("type")
        response = await get_tasks_by_type(request, type=t, self_created=False) if t in ["all", "SOS", "1 Day", "10 Day", "Monthly", "Quaterly"] else await get_tasks_by_type(request, self_created=False)
        return JsonResponse(response, safe=False)
    except Exception as e:
        return JsonResponse({"msg": f"{e}"})


# ==================== change_status ====================
# Change task status.
# URL: {{baseurl}}/tasks/changeStatus/<task_id>/
# Method: PATCH
def _change_task_status_sync(task_id, changed_to):
    task = get_task_object(task_id=task_id)
    task.status = _get_taskStatus_object_sync(status_name=changed_to.upper())
    task.save()


# change status of a task.applicable method-"PATCH".request content-type-"application/json"
# endpoint-{{baseurl}}/tasks/{id}/changeStatus/
@login_required
@csrf_exempt
async def change_status(request: HttpRequest, task_id):
    request_method = verifyPatch(request)
    if request_method:
        return request_method
    changed_to = load_data(request).get("change_Status_to")
    try:
        await sync_to_async(_change_task_status_sync)(task_id, changed_to)
        return JsonResponse({"message": f"Status Changed to {changed_to}"})
    except Exception as e:
        return JsonResponse({"message": f"{e}"})


# ==================== delete_task ====================
# Delete a task.
# URL: {{baseurl}}/tasks/deleteTask/<task_id>/
# Method: DELETE
def _delete_task_sync(user, task_id):
    task = get_task_object(task_id=task_id)
    role = _get_user_role_sync(user)
    if user != task.created_by and role and role not in ["MD", "TeamLead"]:
        raise PermissionDenied("Not allowed")
    task.delete()


@csrf_exempt
@login_required
async def delete_task(request: HttpRequest, task_id: int):
    verify_request = verifyDelete(request)
    if verify_request:
        return verify_request
    try:
        await sync_to_async(_delete_task_sync)(request.user, task_id)
        return JsonResponse({"Message": f"task-task_id {task_id} deleted successfully"}, status=status.HTTP_201_CREATED)
    except PermissionDenied:
        return JsonResponse({"error": "You are not authorised to delete the task"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return JsonResponse({"message": f"{e}"})


# ==================== post_task_message ====================
# Post a message in a task.
# URL: {{baseurl}}/tasks/sendMessage/
# Method: POST
def _post_task_message_sync(task_id, user, message_text):
    task = get_object_or_404(Task, task_id=task_id)
    TaskMessage.objects.create(task=task, sender=user, message=message_text)


@login_required
@csrf_exempt
async def post_task_message(request: HttpRequest):
    if verifyPost(request):
        return verifyPost(request)
    request_data = load_data(request)
    message_text = request_data.get("message")
    if not message_text:
        return JsonResponse({"error": "Message required"}, status=400)
    try:
        await sync_to_async(_post_task_message_sync)(request_data.get("task_id"), request.user, message_text)
        return JsonResponse({"status": "Message sent"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return JsonResponse(str(e), status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)


# ==================== get_task_messages ====================
# Fetch messages for a task.
# URL: {{baseurl}}/tasks/getMessage/<task_id>/
# Method: GET
@login_required
async def get_task_messages(request: HttpRequest, task_id: int):
    if verifyGet(request):
        return verifyGet(request)
    try:
        def _fetch(user):
            task = get_object_or_404(Task, task_id=task_id)
            assignees = TaskAssignies.objects.filter(task=task_id)
            for i in assignees:
                if not (user != task.created_by and user != i.assigned_to):
                    raise PermissionDenied("Not allowed")
            messages = TaskMessage.objects.filter(task=task).select_related("sender", "task").order_by("-created_at")
            messages.update(seen=True)
            return [{"sender": m.sender.username, "message": m.message, "date": m.created_at.strftime("%d/%m/%y"),
                "time": m.created_at.strftime("%H:%M"), "seen": m.seen} for m in messages]
        data = await sync_to_async(_fetch)(request.user)
        return JsonResponse(data, safe=False)
    except PermissionDenied:
        return JsonResponse({"message": "you are not authorised to accessed this task conversation"}, status=status.HTTP_403_FORBIDDEN)


# ==================== get_task_count_from_username ====================
# Get task count by status for a username.
# URL: {{baseurl}}/tasks/Taskcount/<username>/
# Method: GET
def _get_task_count_sync(username):
    user_obj = get_object_or_404(User, username=username)
    return list(TaskAssignies.objects.filter(assigned_to=user_obj).values(status=F("task__status__status_name")).annotate(count=Count("task_id")).order_by("status"))


@login_required
async def get_task_count_from_username(request: HttpRequest, username: str):
    if verifyGet(request):
        return verifyGet(request)
    try:
        data = await sync_to_async(_get_task_count_sync)(username)
        return JsonResponse(data, safe=False, status=200)
    except Exception as e:
        return JsonResponse({"msg": str(e)}, status=400)


# ==================== add_task_assignees ====================
# Add assignees to a task.
# URL: (if configured)
# Method: PATCH
def _add_task_assignees_sync(task_id, assignees):
    task = get_object_or_404(Task, task_id=task_id)
    for username in assignees:
        user = get_object_or_404(User, username=username)
        TaskAssignies.objects.get_or_create(task=task, assigned_to=user)


async def add_task_assignees(request: HttpRequest):
    if verifyPatch(request):
        return verifyPatch(request)
    data = load_data(request)
    task_id, assignees = data.get("task_id"), data.get("assignees")
    if not task_id or not assignees:
        return JsonResponse({"error": "task_id and assignees are required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        await sync_to_async(_add_task_assignees_sync)(task_id, assignees)
        return JsonResponse({"message": "Assignees added successfully"}, status=status.HTTP_200_OK)
    except Http404 as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== remove_task_assignees ====================
# Remove assignees from a task.
# URL: (if configured)
# Method: DELETE
def _remove_task_assignees_sync(task_id, assignees):
    task = get_object_or_404(Task, id=task_id)
    for username in assignees:
        user = get_object_or_404(User, username=username)
        TaskAssignies.objects.filter(task=task, assigned_to=user).delete()


async def remove_task_assignees(request: HttpRequest):
    if verifyDelete(request):
        return verifyDelete(request)
    data = load_data(request)
    task_id, assignees = data.get("task_id"), data.get("assignees")
    if not task_id or not assignees:
        return JsonResponse({"error": "task_id and assignees are required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        await sync_to_async(_remove_task_assignees_sync)(task_id, assignees)
        return JsonResponse({"message": "Assignees removed successfully"}, status=status.HTTP_200_OK)
    except Http404 as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


