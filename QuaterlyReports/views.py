from accounts.filters import get_department_obj
from ems.verify_methods import *
from .models import *
from task_management.filters import get_taskStatus_object
from .filters import *
from rest_framework import status

@csrf_exempt
@login_required
def create_multiple_user_entries(request: HttpRequest):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    try:
        if request.user.is_superuser:
            raise PermissionDenied("You cannot create entries")
        fields=["date","entries","month_quater_id"]
        data = load_data(request)
        entry_date = data.get("date")
        month_quater_id = data.get("month_quater_id")
        entries = data.get("entries")
        if not all(fields):
            return JsonResponse({"message": "Invalid payload"},)
        user = request.user
        month_quater = Monthly_department_head_and_subhead.objects.get(id=month_quater_id)
        created_entries = []
        for entry in entries:
            note=entry.get("note")
            status=entry.get("status")
            
            if not note or not status:
                continue

            status_obj=get_taskStatus_object(status_name=status)

            obj = UsersEntries.objects.create(
                status=status_obj,
                user=user,
                month_and_quater_id=month_quater,
                date=entry_date,
                note=note
            )
            created_entries.append(obj.id)
        print(created_entries)
        return JsonResponse({
            "message": "Entries created successfully",
            "created_entry_ids": created_entries
        }, safe=False,status=201)

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
    
@login_required
def get_entries(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    try:
        data=request.GET
        query_parameter={}
        username=data.get("username",None)
        if not username:
            raise ValueError("username is required")
        user_obj=get_object_or_404(User,username=username)
        query_parameter["user"]=user_obj
        if user_obj.is_superuser:
            return JsonResponse([],safe=False,status=status.HTTP_200_OK)
        login_users_username=request.user.username
        
        for i in ["date","quater","month","department"]:
            para_value=data.get(i)
            if not para_value and i in ["quater","month","department"]:
                raise ValueError(f"{i} is missing")
            elif i=="date" and not para_value:
                ...
            else:
                query_parameter[i]=para_value
        # print(query_parameter)
        superuser=request.user.is_superuser
        if superuser:
            data=get_addeded_entries(request,**query_parameter)

        elif username==login_users_username and not superuser:
            data=get_addeded_entries(request,**query_parameter)
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
        return JsonResponse(data,safe=False,status=200)

@login_required
@csrf_exempt
def change_status(request: HttpRequest,user_entry_id:int):
    request_method=verifyPatch(request)
    if request_method:
        return request_method
    data=load_data(request)
    changed_to:str=data.get("change_Status_to")
    try:
        user_entry=UsersEntries.objects.get(id=user_entry_id)
        changed_status=get_taskStatus_object(status_name=changed_to.upper())
        setattr(user_entry,"status",changed_status)
        user_entry.save()
    except Exception as e:
        return JsonResponse({"message":f"{e}"})
    else:
        return JsonResponse({"message":f"Status Changed to {changed_to}"})
    
@login_required
@csrf_exempt
def delete_entry(request: HttpRequest,user_entry_id:int):
    request_method=verifyDelete(request)
    if request_method:
        return request_method
    try:
        user_entry=get_object_or_404(UsersEntries,id=user_entry_id)
        if user_entry.user==request.user:
            user_entry.delete()
        else:
            raise PermissionDenied("you are not authorised")
    except PermissionDenied as e:
        return JsonResponse({"message":f"{e}"},status=status.HTTP_403_FORBIDDEN)
    except Http404 as e:
        return JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({"message":f"entry deleted successfully"},status=status.HTTP_200_OK)
# Create your views here.

@login_required
def get_meeting_head_and_subhead(request:HttpRequest,user_id:str):
    try:
        user=get_object_or_404(User,username=user_id)
        user_profile=get_object_or_404(Profile,Employee_id=user)
        if user_profile.Role.role_name in ["MD","Admin"]:
            return JsonResponse([],safe=False,status=status.HTTP_200_OK)
        data=request.GET
        if not data:
            get_quater_data=get_financial_year_details()
            actual_month=get_quater_data.get("respective_quarter_months")
            financial_year=get_quater_data.get("financial_year")
            reverse_month=get_quater_data.get("reverse_quater_month")
            quater=get_quater_data.get("quarter")
        else:
            get_quater_data=data
            month=get_quater_data.get("month")
            actual_month=month
            financial_year=get_current_financial_year()
            actual_month=month
            quater=get_quater_data.get("quater")
            reverse_month=reversed_quater_month[quater][month]
            
        quarter_obj=get_quater_object(quater=quater)
        department_obj=user_profile.Department
    except Http404 as e:
        print(e)
        return JsonResponse({"Message":"http 404 error occured"})
    except Exception as e:
        print(e)
        return JsonResponse({"Message":f"{e}"}) 
    else:
        get_monthly_schedule_set=Monthly_department_head_and_subhead.objects.filter(month_of_the_quater=reverse_month,quater=quarter_obj,
                                                                        department=department_obj)
        values=[{"id":obj.id,
                "quater":obj.quater.quater,
                "financial_year":financial_year,
                "month":reverse_month,
                "actual_month":actual_month,
                "Meeting-head":obj.Meeting_head,
                "Sub-Meeting-head":obj.meeting_sub_head,
                "sub-head-D1":obj.Sub_Head_D1,
                "sub-head-D2":obj.Sub_Head_D2,
                "sub-head-D3":obj.Sub_Head_D3 
                } for obj in get_monthly_schedule_set]
        
        return JsonResponse(values,safe=False)
    ...

@csrf_exempt       
def add_meeting_head_subhead(request:HttpRequest):
    data=load_data(request)
    quater=data.get("quater")
    month=data.get("month")
    head=data.get("head")
    sub_head=data.get("sub_head")
    sub_d1=data.get("sub_d1")
    sub_d2=data.get("sub_d2")
    sub_d3=data.get("sub_d3")
    try:
        department=get_department_obj(dept=data.get("dept"))
        quater_object=Quaters.objects.get(quater=quater)
    except Exception as e:
        print(e)
        return JsonResponse({"Message":"Error occured"})
    else:
        Monthly_department_head_and_subhead.create_head_and_subhead_for_each_dept(dept=department,quater=quater_object,
                                                                            month_of_the_quater=month,Meeting_head=head,meeting_sub_head=sub_head,
                                                                            Sub_Head_D1=sub_d1,Sub_Head_D2=sub_d2,Sub_Head_D3=sub_d3)
    
    return JsonResponse({"Message":"added successfully"})