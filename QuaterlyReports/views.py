from ems.RequiredImports import (
    sync_to_async,
    Q,
    Response,
    status,
    api_view,
    permission_classes,
    date,
    IsAuthenticated,
    JsonResponse,
    get_object_or_404,
    PermissionDenied,
)
from ems.verify_methods import *
from accounts.filters import _get_department_obj_sync
from .models import *
from task_management.filters import _get_taskStatus_object_sync
from .filters import (
    get_financial_year_details,
    get_current_financial_year,
    reversed_quater_month,
    _get_quater_object_sync,
    get_addeded_entries,
)
from .serializers import FunctionsEntriesSerializer
from .permissions import EntryPermission
import logging
from django.utils import timezone

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #


# ==================== create_multiple_user_entries ====================
# Create multiple user day entries.
# URL: {{baseurl}}/addDayEntries/
# Method: POST
def _create_multiple_user_entries_sync(user, data):
    month_quater = Monthly_department_head_and_subhead.objects.get(id=data["month_quater_id"])
    created_entries = []
    for entry in data["entries"]:
        note, status_name = entry.get("note"), entry.get("status")
        if not note or not status_name:
            continue
        status_obj = _get_taskStatus_object_sync(status_name=status_name)
        obj = UsersEntries.objects.create(
            status=status_obj, user=user, month_and_quater_id=month_quater,
            date=data["date"], note=note
        )
        created_entries.append(obj.id)
    return created_entries


@csrf_exempt
@login_required
async def create_multiple_user_entries(request: HttpRequest):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    try:
        if request.user.is_superuser:
            raise PermissionDenied("You cannot create entries")
        data = load_data(request)
        if not all(data.get(f) for f in ["date", "entries", "month_quater_id"]):
            return JsonResponse({"message": "Invalid payload"})
        created_entries = await sync_to_async(_create_multiple_user_entries_sync)(request.user, data)
        return JsonResponse({"message": "Entries created successfully", "created_entry_ids": created_entries}, safe=False, status=201)

    except User.DoesNotExist:
        return JsonResponse({"error": "User not found, pass the correct username"},status=404)
    
    except TaskStatus.DoesNotExist:
        return JsonResponse({"message": "Incorrect Status passed in the body"},status=404)

    except Monthly_department_head_and_subhead.DoesNotExist:
        return JsonResponse({"error": "Invalid month_quater_id"}, status=404)
    
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)},status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)


# ==================== get_entries ====================
# Fetch user entries by username, month, quater, department.
# URL: {{baseurl}}/getUserEntries/
# Method: GET
@login_required
async def get_entries(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    try:
        query_parameter = {}
        username = request.GET.get("username")
        if not username:
            raise ValueError("username is required")
        user_obj = await sync_to_async(get_object_or_404)(User, username=username)
        query_parameter["user"] = user_obj
        if user_obj.is_superuser:
            return JsonResponse([], safe=False, status=status.HTTP_200_OK)
        for i in ["date", "quater", "month", "department"]:
            para_value = request.GET.get(i)
            if not para_value and i in ["quater", "month", "department"]:
                raise ValueError(f"{i} is missing")
            else:
                query_parameter[i] = para_value
        superuser = request.user.is_superuser
        if superuser or username == request.user.username:
            data = await get_addeded_entries(request, **query_parameter)
        else:
            raise PermissionDenied("Not authorised")
    except ValueError as e:
            print(e)
            return JsonResponse({"message":f"{e}"},status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    except PermissionDenied as e:
            print(e)
            return JsonResponse({"message":"you are not authorised to access other users records"},status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=status.HTTP_501_NOT_IMPLEMENTED)
    else:
        if isinstance(data,JsonResponse):
            return data
        return JsonResponse(data, safe=False, status=200)


# ==================== change_status ====================
# Change status of a user entry.
# URL: {{baseurl}}/changeStatus/<user_entry_id>/
# Method: PATCH
def _change_entry_status_sync(user_entry_id, changed_to):
    user_entry = UsersEntries.objects.get(id=user_entry_id)
    changed_status = _get_taskStatus_object_sync(status_name=changed_to.upper())
    user_entry.status = changed_status
    user_entry.save()


@login_required
@csrf_exempt
async def change_status(request: HttpRequest, user_entry_id: int):
    request_method = verifyPatch(request)
    if request_method:
        return request_method
    data = load_data(request)
    changed_to = data.get("change_Status_to")
    try:
        await sync_to_async(_change_entry_status_sync)(user_entry_id, changed_to)
        return JsonResponse({"message": f"Status Changed to {changed_to}"})
    except Exception as e:
        return JsonResponse({"message": f"{e}"})


# ==================== delete_entry ====================
# Delete a user entry.
# URL: {{baseurl}}/deleteEntry/<user_entry_id>/
# Method: DELETE
def _delete_entry_sync(user_entry_id, user):
    user_entry = get_object_or_404(UsersEntries, id=user_entry_id)
    if user_entry.user == user:
        user_entry.delete()
    else:
        raise PermissionDenied("you are not authorised")


@login_required
@csrf_exempt
async def delete_entry(request: HttpRequest, user_entry_id: int):
    request_method = verifyDelete(request)
    if request_method:
        return request_method
    try:
        await sync_to_async(_delete_entry_sync)(user_entry_id, request.user)
    except PermissionDenied:
        return JsonResponse({"message": "you are not authorised to access other users records"}, status=status.HTTP_403_FORBIDDEN)
    except Http404:
        return JsonResponse({"message": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    return JsonResponse({"message": "entry deleted successfully"}, status=status.HTTP_200_OK)


# ==================== get_meeting_head_and_subhead ====================
# Fetch meeting head and subhead for a user by quarter/month.
# URL: {{baseurl}}/getMonthlySchedule/<user_id>/
# Method: GET
def _get_meeting_head_sync(request:HttpRequest,user_id:str):
    user = get_object_or_404(User, username=user_id)
    user_profile = get_object_or_404(Profile, Employee_id=user)
    get_data=request.GET
    if user_profile.Role.role_name in ["MD", "Admin"]:
        return []
    if not get_data:
        get_quater_data = get_financial_year_details()
        actual_month = get_quater_data.get("respective_quarter_months")
        financial_year = get_quater_data.get("financial_year")
        reverse_month = get_quater_data.get("reverse_quater_month")
        quater = get_quater_data.get("quarter")
    else:
        month = get_data.get("month")
        # actual_month = month
        # print(get_data)
        # print(type(month))
        financial_year = get_current_financial_year()
        quater = get_data.get("quater")
        # print(type(quater))
        reverse_month = reversed_quater_month[quater][month]
        # print(reverse_month)
    # quarter_obj = _get_quater_object_sync(quater=quater)
    department_obj = user_profile.Department
    get_monthly_schedule_set = Monthly_department_head_and_subhead.objects.filter(
        month_of_the_quater=reverse_month, department=department_obj)
    return [{"id": obj.id, "quater": quater, "financial_year": financial_year,
        "month": reverse_month, "actual_month": month, "Meeting-head": obj.Meeting_head,
        "Sub-Meeting-head": obj.meeting_sub_head, "sub-head-D1": obj.Sub_Head_D1,
        "sub-head-D2": obj.Sub_Head_D2, "sub-head-D3": obj.Sub_Head_D3}
        for obj in get_monthly_schedule_set]


@login_required
async def get_meeting_head_and_subhead(request: HttpRequest, user_id: str):
    try:
        values = await sync_to_async(_get_meeting_head_sync)(request,user_id)
        return JsonResponse(values, safe=False)
    except Http404:
        return JsonResponse({"Message": "http 404 error occured"},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({"Message": f"{e}"},status=status.HTTP_501_NOT_IMPLEMENTED)


# ==================== add_meeting_head_subhead ====================
# Add meeting head and subhead for a department/quarter.
# URL: {{baseurl}}/addMeetingHeadSubhead/
# Method: POST
def _add_meeting_head_sync(data):
    department = _get_department_obj_sync(dept=data["dept"])
    # quater_object = Quaters.objects.get(quater=data["quater"])
    Monthly_department_head_and_subhead.create_head_and_subhead_for_each_dept(
        dept=department,month_of_the_quater=data["month"],
        Meeting_head=data["head"], meeting_sub_head=data["sub_head"],
        Sub_Head_D1=data["sub_d1"], Sub_Head_D2=data["sub_d2"], Sub_Head_D3=data["sub_d3"])


@csrf_exempt
async def add_meeting_head_subhead(request: HttpRequest):
    try:
        data = load_data(request)
        data = {k: v.strip() for k, v in data.items() if isinstance(v, str)}
        await sync_to_async(_add_meeting_head_sync)(data)
        return JsonResponse({"Message": "added successfully"})
    except Exception as e:
        print(e)
        return JsonResponse({"Message": "Error occured"})


# ==================== get_functions_and_actionable_goals ====================
# Fetch function goals and actionable goals by function name.
# URL: {{baseurl}}/get_functions_and_actionable_goals/?function_name=<name>
# Method: GET
def _get_functions_goals_sync(function_name):
    function_obj = Functions.objects.prefetch_related('functionsgoals_set__actionablegoals_set').get(function__iexact=function_name)
    functional_goals_list = []
    for f_goal in function_obj.functionsgoals_set.all():
        actionable_goals = [{"actionable_id": a_goal.id, "purpose": a_goal.purpose, "grp_id": a_goal.grp.grp}
            for a_goal in f_goal.actionablegoals_set.all()]
        functional_goals_list.append({"functional_id": f_goal.id, "main_goal": f_goal.Maingoal, "actionable_goals": actionable_goals})
    return {"function": function_obj.function, "functional_goals": functional_goals_list}


async def get_functions_and_actionable_goals(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    function_name = request.GET.get('function_name')
    if not function_name:
        return JsonResponse({"error": "Query parameter 'function_name' is required."}, status=400)
    try:
        response_data = await sync_to_async(_get_functions_goals_sync)(function_name)
        return JsonResponse(response_data, safe=False)
    except Functions.DoesNotExist:
        return JsonResponse({"error": f"Function '{function_name}' not found."}, status=404)


# ==================== entry_list_create ====================
# List or create actionable entries (FunctionsEntries).
# URL: {{baseurl}}/ActionableEntries/
# Method: GET (list) | POST (create)

def _get_entries(request: HttpRequest):
    """List actionable entries. Visibility: creator sees own; co_author sees where they are co_author; share_with sees where approved_by_coauthor=True."""
    current_date = date.today()
    current_month = current_date.month
    req_data = request.GET
    username, month = req_data.get("username"), req_data.get("month")
    user = request.user
    permissible = username and user.is_superuser
    user_obj = get_object_or_404(User, username=username) if permissible else None
    if permissible and user_obj:
        visible = Q(Creator=user_obj) | Q(co_author=user_obj) | Q(share_with=user_obj, approved_by_coauthor=True)
        base = FunctionsEntries.objects.filter(visible)
        month_val = month or current_month
        entries = base.filter(date__month=month_val)
    else:
        visible = Q(Creator=user) | Q(co_author=user) | Q(share_with=user, approved_by_coauthor=True)
        base = FunctionsEntries.objects.filter(visible)
        if not username and not month:
            entries = base.filter(Creator=user, date__month=current_month)
        elif not username and month:
            entries = base.filter(Creator=user, date__month=month)
        else:
            raise PermissionDenied("You are not authorised to do this action")
    serializer = FunctionsEntriesSerializer(entries, many=True)
    return JsonResponse(serializer.data, safe=False)
            
def _create_entry(request: HttpRequest):
    serializer = FunctionsEntriesSerializer(
        data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save(Creator=request.user)
        return JsonResponse(serializer.data, safe=False, status=status.HTTP_201_CREATED)
    return JsonResponse(serializer.errors or {"message": "error occurred"}, status=status.HTTP_400_BAD_REQUEST)
            
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, EntryPermission])
def entry_list_create(request: HttpRequest):
    """List or create actionable entries. Sync so DRF permission_classes and api_view work correctly."""
    try:
        if request.method == 'GET':
            return _get_entries(request=request)

        elif request.method == 'POST':
            return _create_entry(request=request)

    except PermissionDenied as e:
        return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

def _entry_visible_to_user(entry, user):
    """True if user may see this entry (creator, co_author, or share_with and approved)."""
    if entry.Creator_id == user.username:
        return True
    if entry.co_author_id and entry.co_author_id == user.username:
        return True
    if entry.share_with_id and entry.share_with_id == user.username and entry.approved_by_coauthor:
        return True
    return False


# ==================== co_author_approve_entry ====================
# Co-author approves an actionable entry (no payload). Sets approved_by_coauthor=True and final_Status=In-progress.
# URL: {{baseurl}}/ActionableEntriesByID/<id>/co-author-approve/
# Method: POST
def _co_author_approve_sync(entry_id, user):
    entry = FunctionsEntries.objects.get(pk=entry_id)
    if not entry.co_author_id:
        return {"error": "Entry has no co-author assigned", "status_code": status.HTTP_400_BAD_REQUEST}
    if str(entry.co_author_id) != str(user.username):
        return {"error": "Only the co-author can approve this entry", "status_code": status.HTTP_403_FORBIDDEN}
    if entry.approved_by_coauthor:
        return {"already_approved": True, "entry": entry, "status_code": status.HTTP_200_OK}
    inprogress = _get_taskStatus_object_sync(status_name="INPROCESS")
    if not inprogress:
        return {"error": "In-progress status not found", "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR}
    entry.approved_by_coauthor = True
    entry.final_Status = inprogress
    entry.save()
    return {"entry": entry, "status_code": status.HTTP_200_OK}


@api_view(["POST"])
@permission_classes([IsAuthenticated, EntryPermission])
def co_author_approve_entry(request, id):
    """Co-author approves an actionable entry. No payload required. Only the assigned co_author can call this."""
    try:
        result = _co_author_approve_sync(id, request.user)
        status_code = result["status_code"]
        if "error" in result:
            return Response({"error": result["error"]}, status=status_code)
        entry = result["entry"]
        data = FunctionsEntriesSerializer(entry).data
        if result.get("already_approved"):
            return Response({"message": "Entry already approved", "entry": data}, status=status_code)
        return Response({"message": "Entry approved by co-author", "entry": data}, status=status_code)
    except FunctionsEntries.DoesNotExist:
        return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== entry_detail_update_delete ====================
# Get, update, or delete a single actionable entry.
# URL: {{baseurl}}/ActionableEntriesByID/<id>/
# Method: GET | PUT | PATCH | DELETE
def _entry_detail_ops(request, id):
    entry = FunctionsEntries.objects.get(pk=id)
    if not _entry_visible_to_user(entry, request.user):
        return Response({"error": "Entry not found or not visible"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response(FunctionsEntriesSerializer(entry).data)
    elif request.method in ["PUT", "PATCH"]:
        serializer = FunctionsEntriesSerializer(
            entry, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == "DELETE":
        if entry.Creator_id != request.user.username:
            return Response({"error": "Only creator can delete this entry"}, status=status.HTTP_403_FORBIDDEN)
        entry.delete()
        return Response({"message": "entry deleted successfully"}, status=status.HTTP_202_ACCEPTED)


@api_view(['GET', 'PUT', 'DELETE', "PATCH"])
@permission_classes([IsAuthenticated, EntryPermission])
def entry_detail_update_delete(request, id):
    """Get, update, or delete a single actionable entry. Sync so DRF permission_classes work correctly."""
    try:
        return _entry_detail_ops(request, id)
    except FunctionsEntries.DoesNotExist:
        return Response({'error': 'Entry not found'}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Co-author entries (list + detail) ====================
# Entries where the current user is co_author. Same fields as ActionableEntries.
# URL: {{baseurl}}/ActionableEntriesCoAuthor/  |  {{baseurl}}/ActionableEntriesCoAuthor/<id>/
@api_view(["GET"])
@permission_classes([IsAuthenticated, EntryPermission])
def co_author_entries_list(request):
    """List actionable entries where the current user is co_author. Optional ?month= (1-12)."""
    month = request.GET.get("month")
    current_month = date.today().month
    try:
        month_val = int(month) if month is not None else current_month
        if month_val < 1 or month_val > 12:
            month_val = current_month
    except (TypeError, ValueError):
        month_val = current_month
    entries = FunctionsEntries.objects.filter(co_author=request.user, date__month=month_val).order_by("-date", "-time")
    serializer = FunctionsEntriesSerializer(entries, many=True)
    return Response(serializer.data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, EntryPermission])
def co_author_entry_detail(request, id):
    """Get or update one actionable entry. Allowed only if current user is co_author. Same fields as ActionableEntries."""
    try:
        entry = FunctionsEntries.objects.get(pk=id)
        if str(entry.co_author_id or "") != str(request.user.username):
            return Response({"error": "Entry not found or you are not the co-author"}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "GET":
            return Response(FunctionsEntriesSerializer(entry).data)
        serializer = FunctionsEntriesSerializer(entry, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except FunctionsEntries.DoesNotExist:
        return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Shared-with entries (list + detail) ====================
# Entries where the current user is share_with (and approved). Same fields as ActionableEntries.
# URL: {{baseurl}}/ActionableEntriesSharedWith/  |  {{baseurl}}/ActionableEntriesSharedWith/<id>/
@api_view(["GET"])
@permission_classes([IsAuthenticated, EntryPermission])
def shared_with_entries_list(request):
    """List actionable entries where the current user is share_with and entry is approved by co-author. Optional ?month= (1-12)."""
    month = request.GET.get("month")
    current_month = date.today().month
    try:
        month_val = int(month) if month is not None else current_month
        if month_val < 1 or month_val > 12:
            month_val = current_month
    except (TypeError, ValueError):
        month_val = current_month
    entries = FunctionsEntries.objects.filter(
        share_with=request.user, approved_by_coauthor=True, date__month=month_val
    ).order_by("-date", "-time")
    serializer = FunctionsEntriesSerializer(entries, many=True)
    return Response(serializer.data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, EntryPermission])
def shared_with_entry_detail(request, id):
    """Get or update one actionable entry. Allowed only if current user is share_with and entry is approved. Same fields; share_with can update shared_Status."""
    try:
        entry = FunctionsEntries.objects.get(pk=id)
        if str(entry.share_with_id or "") != str(request.user.username):
            return Response({"error": "Entry not found or you are not the share_with user"}, status=status.HTTP_404_NOT_FOUND)
        if not entry.approved_by_coauthor:
            return Response({"error": "Entry not visible until co-author approves"}, status=status.HTTP_403_FORBIDDEN)
        if request.method == "GET":
            return Response(FunctionsEntriesSerializer(entry).data)
        serializer = FunctionsEntriesSerializer(entry, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except FunctionsEntries.DoesNotExist:
        return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ************************************************ Calling APIS ************************************************* 