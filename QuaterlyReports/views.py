from django.http import Http404
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
    DatabaseError,
)
from django.db.models import Prefetch
from ems.verify_methods import *
from accounts.filters import _get_department_obj_sync
from accounts.models import Departments
from project.models import Product
from .models import *
from task_management.filters import _get_taskStatus_object_sync
from task_management.models import TaskStatus
from .filters import (
    get_financial_year_details,
    get_current_financial_year,
    reversed_quater_month,
    _get_quater_object_sync,
    get_addeded_entries,
)
from .serializers import FunctionsEntriesSerializer, FunctionsEntriesShareSerializer
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
    product = None
    product_name = (data.get("product") or "").strip() if data.get("product") else None
    if product_name:
        product = get_object_or_404(Product, name__iexact=product_name)
    created_entries = []
    for entry in data["entries"]:
        note, status_name = entry.get("note"), entry.get("status")
        if not note or not status_name:
            continue
        status_obj = _get_taskStatus_object_sync(status_name=status_name)
        obj = UsersEntries.objects.create(
            status=status_obj,
            user=user,
            month_and_quater_id=month_quater,
            date=data["date"],
            note=note,
            product=product,
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

    except Http404:
        return JsonResponse({"error": "Product not found with the given name."}, status=404)

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
            return JsonResponse({"message": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionDenied as e:
            print(e)
            return JsonResponse({"message":"you are not authorised to access other users records"},status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
# Fetch meeting head and subhead by department name (and optional quarter/month).
# URL: {{baseurl}}/getMonthlySchedule/?department=<department_name>
# Method: GET. Query params: department (required), optional: month, quater
def _get_meeting_head_sync(request: HttpRequest, department_name: str):
    if not department_name or not str(department_name).strip():
        return None  # caller will respond with 400
    department_obj = get_object_or_404(Departments, dept_name=department_name.strip())
    get_data = request.GET
    if not get_data or "month" not in get_data or "quater" not in get_data:
        get_quater_data = get_financial_year_details()
        financial_year = get_quater_data.get("financial_year")
        reverse_month = get_quater_data.get("reverse_quater_month")
        quater = get_quater_data.get("quarter")
        month = get_quater_data.get("respective_quarter_months")
    else:
        month = get_data.get("month")
        financial_year = get_current_financial_year()
        quater = get_data.get("quater")
        reverse_month = reversed_quater_month[quater][month]
    get_monthly_schedule_set = Monthly_department_head_and_subhead.objects.filter(
        month_of_the_quater=reverse_month, department=department_obj
    )
    return [
        {
            "id": obj.id,
            "quater": quater,
            "financial_year": financial_year,
            "month": reverse_month,
            "actual_month": month,
            "Meeting-head": obj.Meeting_head,
            "Sub-Meeting-head": obj.meeting_sub_head,
            "sub-head-D1": obj.Sub_Head_D1,
            "sub-head-D2": obj.Sub_Head_D2,
            "sub-head-D3": obj.Sub_Head_D3,
        }
        for obj in get_monthly_schedule_set
    ]


@login_required
async def get_meeting_head_and_subhead(request: HttpRequest):
    department_name = request.GET.get("department") or request.GET.get("dept")
    if not department_name or not str(department_name).strip():
        return JsonResponse(
            {"Message": "department (or dept) query parameter is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        values = await sync_to_async(_get_meeting_head_sync)(request, department_name)
        return JsonResponse(values, safe=False)
    except Http404:
        return JsonResponse(
            {"Message": "Department not found or no schedule for the given criteria."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return JsonResponse({"Message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

def _entry_in_share_chain(entry, user):
    """True if user appears in this entry's share chain."""
    return entry.share_chain.filter(shared_with=user).exists()


def _entry_visible_to_user(entry, user):
    """True if user may see this entry (creator, co_author, or in share_chain and approved)."""
    if entry.Creator_id == user.username:
        return True
    if entry.co_author_id and entry.co_author_id == user.username:
        return True
    if entry.approved_by_coauthor and _entry_in_share_chain(entry, user):
        return True
    return False


def _get_entries(request: HttpRequest):
    """List actionable entries. Visibility: creator; co_author; or in share_chain and approved_by_coauthor=True."""
    current_date = date.today()
    current_month = current_date.month
    req_data = request.GET
    username, month = req_data.get("username"), req_data.get("month")
    user = request.user
    permissible = username and user.is_superuser
    user_obj = get_object_or_404(User, username=username) if permissible else None
    base_qs = FunctionsEntries.objects.select_related(
        "Creator__accounts_profile", "co_author__accounts_profile", "product"
    ).prefetch_related(
        Prefetch(
            "share_chain",
            queryset=FunctionsEntriesShare.objects.select_related(
                "shared_with__accounts_profile", "individual_status"
            ).order_by("shared_time"),
        )
    )
    if permissible and user_obj:
        visible = Q(Creator=user_obj) | Q(co_author=user_obj) | Q(share_chain__shared_with=user_obj, approved_by_coauthor=True)
        base = base_qs.filter(visible).distinct()
        month_val = int(month) if month else current_month
        entries = base.filter(date__month=month_val)
    else:
        visible = Q(Creator=user) | Q(co_author=user) | Q(share_chain__shared_with=user, approved_by_coauthor=True)
        base = base_qs.filter(visible).distinct()
        if not username and not month:
            entries = base.filter(Creator=user, date__month=current_month)
        elif not username and month:
            entries = base.filter(Creator=user, date__month=int(month))
        else:
            raise PermissionDenied("You are not authorised to do this action")
    serializer = FunctionsEntriesSerializer(entries, many=True)
    return JsonResponse(serializer.data, safe=False)
            
def _create_entry(request: HttpRequest):
    serializer = FunctionsEntriesSerializer(
        data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        entry = serializer.save(Creator=request.user)
        entry.refresh_from_db()
        entry = FunctionsEntries.objects.select_related(
            "Creator__accounts_profile", "co_author__accounts_profile", "product"
        ).prefetch_related(
            Prefetch(
                "share_chain",
                queryset=FunctionsEntriesShare.objects.select_related(
                    "shared_with__accounts_profile", "individual_status"
                ).order_by("shared_time"),
            )
        ).get(pk=entry.pk)
        return JsonResponse(FunctionsEntriesSerializer(entry).data, safe=False, status=status.HTTP_201_CREATED)
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


def _get_entry_with_share_chain(entry_id):
    return FunctionsEntries.objects.select_related(
        "Creator__accounts_profile", "co_author__accounts_profile", "product"
    ).prefetch_related(
        Prefetch(
            "share_chain",
            queryset=FunctionsEntriesShare.objects.select_related(
                "shared_with__accounts_profile", "individual_status"
            ).order_by("shared_time"),
        )
    ).get(pk=entry_id)


def _last_share_in_chain(entry):
    """Return the last share row (by shared_time); None if no shares."""
    return entry.share_chain.order_by("-shared_time").first()


def _last_share_has_completed(entry):
    """True if the last user in the share chain (by shared_time) has set their status to COMPLETED."""
    last = _last_share_in_chain(entry)
    return last and last.individual_status and getattr(last.individual_status, "status_name", "") == "COMPLETED"


def _share_chain_has_completed(entry):
    return entry.share_chain.filter(individual_status__status_name="COMPLETED").exists()


# ==================== entry_detail_update_delete ====================
# Get, update, or delete a single actionable entry.
# URL: {{baseurl}}/ActionableEntriesByID/<id>/
# Method: GET | PUT | PATCH | DELETE
def _entry_detail_ops(request, id):
    entry = _get_entry_with_share_chain(id)
    if not _entry_visible_to_user(entry, request.user):
        return Response({"error": "Entry not found or not visible"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response(FunctionsEntriesSerializer(entry).data)
    elif request.method in ["PUT", "PATCH"]:
        user = request.user
        my_share = entry.share_chain.filter(shared_with=user).first()
        if my_share and str(entry.Creator_id) != str(user.username) and (not entry.co_author_id or str(entry.co_author_id) != str(user.username)):
            # User is in share chain (not creator/co_author): update only their share row
            share_data = {}
            if "share_note" in request.data:
                share_data["shared_note"] = request.data["share_note"]
            if "individual_status" in request.data:
                new_status_name = request.data.get("individual_status")
                if new_status_name and str(new_status_name).upper() == "COMPLETED":
                    last = _last_share_in_chain(entry)
                    last_has_completed = _last_share_has_completed(entry)
                    # Only the last user (by shared_time) can set COMPLETED first; after that, any share-chain user can set their own to COMPLETED.
                    if not last_has_completed and last and last.id != my_share.id:
                        return Response({"error": "Only the last person in the share chain can set status to Completed first. After that, others may mark their status as Completed."}, status=status.HTTP_403_FORBIDDEN)
                try:
                    st = TaskStatus.objects.get(status_name__iexact=str(new_status_name).strip())
                    share_data["individual_status"] = st
                except TaskStatus.DoesNotExist:
                    pass
            if share_data:
                for k, v in share_data.items():
                    setattr(my_share, k, v)
                my_share.save(update_fields=list(share_data.keys()))
            entry.refresh_from_db()
            entry = _get_entry_with_share_chain(id)
            return Response(FunctionsEntriesSerializer(entry).data)
        # Creator or co_author: full entry update via serializer
        serializer = FunctionsEntriesSerializer(
            entry, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            is_creator = str(entry.Creator_id or "") == str(user.username)
            serializer.save()
            entry = _get_entry_with_share_chain(id)
            # When the creator updates the entry, notify co_author, all shared_with, and MD (see QuaterlyReports.signals).
            if is_creator:
                from QuaterlyReports.signals import notify_associates_and_md_on_creator_update
                notify_associates_and_md_on_creator_update(entry)
            return Response(FunctionsEntriesSerializer(entry).data)
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


# ==================== share_further ====================
# Pass the actionable entry to another user (add to share chain). Caller must be in chain; their status set to Inprogress.
# URL: {{baseurl}}/ActionableEntriesByID/<id>/share/
# Method: POST
def _share_further_sync(entry_id, request_user, share_with_username, note):
    entry = FunctionsEntries.objects.prefetch_related("share_chain").get(pk=entry_id)
    if _share_chain_has_completed(entry):
        return {"error": "No further sharing once status is Completed in the chain", "status_code": status.HTTP_400_BAD_REQUEST}
    if entry.final_Status and getattr(entry.final_Status, "status_name", "") == "COMPLETED":
        return {"error": "No further sharing when entry final status is Completed", "status_code": status.HTTP_400_BAD_REQUEST}
    my_share = entry.share_chain.filter(shared_with=request_user).first()
    if not my_share:
        return {"error": "Only someone in the share chain can pass the entry further", "status_code": status.HTTP_403_FORBIDDEN}
    try:
        new_user = User.objects.get(username=share_with_username)
    except User.DoesNotExist:
        return {"error": "User not found", "status_code": status.HTTP_404_NOT_FOUND}
    if entry.share_chain.filter(shared_with=new_user).exists():
        return {"error": "This user is already in the share chain", "status_code": status.HTTP_400_BAD_REQUEST}
    inprogress = _get_taskStatus_object_sync(status_name="INPROCESS")
    pending = _get_taskStatus_object_sync(status_name="PENDING")
    if not inprogress or not pending:
        return {"error": "Status lookup failed", "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR}
    my_share.individual_status = inprogress
    my_share.save(update_fields=["individual_status_id"])
    FunctionsEntriesShare.objects.create(
        actionable_entry=entry,
        shared_with=new_user,
        shared_note=note or "",
        individual_status=pending,
    )
    entry = _get_entry_with_share_chain(entry_id)
    return {"entry": entry, "status_code": status.HTTP_200_OK}


@api_view(["POST"])
@permission_classes([IsAuthenticated, EntryPermission])
def share_further(request, id):
    """Add next user to the share chain. Body: { \"share_with\": \"username\", \"shared_note\": \"...\" }. Caller must be in chain; their status set to Inprogress."""
    try:
        share_with_username = (request.data.get("share_with") or "").strip()
        # Accept shared_note (preferred) or note for backward compatibility
        note = (request.data.get("shared_note") or request.data.get("note") or "").strip()
        if not share_with_username:
            return Response({"error": "share_with (username) is required"}, status=status.HTTP_400_BAD_REQUEST)
        result = _share_further_sync(id, request.user, share_with_username, note)
        if "error" in result:
            return Response({"error": result["error"]}, status=result["status_code"])
        return Response(FunctionsEntriesSerializer(result["entry"]).data, status=result["status_code"])
    except FunctionsEntries.DoesNotExist:
        return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Co-author entries (list + detail; approval via PATCH) ====================
# Single API: GET list, GET/PATCH detail. Co-author approves by PATCH with {"approved_by_coauthor": true}.
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
    entries = FunctionsEntries.objects.select_related(
        "Creator__accounts_profile", "co_author__accounts_profile", "product"
    ).prefetch_related(
        Prefetch(
            "share_chain",
            queryset=FunctionsEntriesShare.objects.select_related(
                "shared_with__accounts_profile", "individual_status"
            ).order_by("shared_time"),
        )
    ).filter(co_author=request.user, date__month=month_val).order_by("-date", "-time")
    serializer = FunctionsEntriesSerializer(entries, many=True)
    return Response(serializer.data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, EntryPermission])
def co_author_entry_detail(request, id):
    """Get or update one actionable entry; co-author can approve via PATCH with approved_by_coauthor=true."""
    try:
        entry = _get_entry_with_share_chain(id)
        if str(entry.co_author_id or "") != str(request.user.username):
            return Response({"error": "Entry not found or you are not the co-author"}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "GET":
            return Response(FunctionsEntriesSerializer(entry).data)
        serializer = FunctionsEntriesSerializer(entry, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            entry = _get_entry_with_share_chain(id)
            return Response(FunctionsEntriesSerializer(entry).data)
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
    """List actionable entries where the current user is in the share chain and entry is approved by co-author. Optional ?month= (1-12)."""
    month = request.GET.get("month")
    current_month = date.today().month
    try:
        month_val = int(month) if month is not None else current_month
        if month_val < 1 or month_val > 12:
            month_val = current_month
    except (TypeError, ValueError):
        month_val = current_month
    entries = FunctionsEntries.objects.select_related(
        "Creator__accounts_profile", "co_author__accounts_profile", "product"
    ).filter(
        share_chain__shared_with=request.user, approved_by_coauthor=True, date__month=month_val
    ).prefetch_related(
        Prefetch(
            "share_chain",
            queryset=FunctionsEntriesShare.objects.select_related(
                "shared_with__accounts_profile", "individual_status"
            ).order_by("shared_time"),
        )
    ).distinct().order_by("-date", "-time")
    serializer = FunctionsEntriesSerializer(entries, many=True)
    return Response(serializer.data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, EntryPermission])
def shared_with_entry_detail(request, id):
    """Get or update one actionable entry. Allowed only if current user is in share chain and entry is approved. Share-chain user can update their share_note and individual_status."""
    try:
        entry = _get_entry_with_share_chain(id)
        if not entry.share_chain.filter(shared_with=request.user).exists():
            return Response({"error": "Entry not found or you are not in the share chain"}, status=status.HTTP_404_NOT_FOUND)
        if not entry.approved_by_coauthor:
            return Response({"error": "Entry not visible until co-author approves"}, status=status.HTTP_403_FORBIDDEN)
        if request.method == "GET":
            return Response(FunctionsEntriesSerializer(entry).data)
        my_share = entry.share_chain.get(shared_with=request.user)
        share_data = {}
        if "share_note" in request.data:
            my_share.shared_note = request.data["share_note"]
            share_data["shared_note"] = my_share.shared_note
        if "individual_status" in request.data:
            new_status_name = (request.data.get("individual_status") or "").strip()
            if new_status_name.upper() == "COMPLETED":
                last = _last_share_in_chain(entry)
                last_has_completed = _last_share_has_completed(entry)
                # Only the last user (by shared_time) can set COMPLETED first; after that, any share-chain user can set their own to COMPLETED.
                if not last_has_completed and last and last.id != my_share.id:
                    return Response({"error": "Only the last person in the share chain can set status to Completed first. After that, others may mark their status as Completed."}, status=status.HTTP_403_FORBIDDEN)
            try:
                st = TaskStatus.objects.get(status_name__iexact=new_status_name)
                my_share.individual_status = st
                share_data["individual_status"] = st  # use field name for update_fields; TaskStatus uses status_id as PK (no .id)
            except TaskStatus.DoesNotExist:
                pass
        if share_data:
            my_share.save(update_fields=list(share_data.keys()))
        entry = _get_entry_with_share_chain(id)
        return Response(FunctionsEntriesSerializer(entry).data)
    except FunctionsEntries.DoesNotExist:
        return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    except FunctionsEntriesShare.DoesNotExist:
        return Response({"error": "Entry not found or you are not in the share chain"}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ************************************************ Calling APIS ************************************************* 