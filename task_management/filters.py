from django.http import HttpRequest, JsonResponse
from accounts.models import Profile
from django.db.models import Q,F,Count
from accounts.views import status
from accounts.filters import get_users_Name
from task_management.models import *
from accounts.filters import get_role_object,get_designation_object
from datetime import date

# # # # # #  baseurl="http://localhost:8000" # # # # # # # # # # # # 
    
# get a "Task" object from task_id
def get_task_object(task_id:int):
    try:
        task=Task.objects.get(task_id=task_id)
    except Exception as e:
        return None
    else:
        return task
    
# get a "TaskType" object from type_name
def get_taskTypes_object(type_name:str):
    try:
        type=TaskTypes.objects.get(type_name=type_name)
    except Exception as e:
        return None
    else:
        return type
    
# get a "TaskStatus" object from status_name
def get_taskStatus_object(status_name:str):
    try:
        status_object=TaskStatus.objects.get(status_name=status_name)
    except Exception as e:
        return None
    else:
        return status_object
        
# get Employees Name list from specified desigantion and role.
# endpoint-{{baseurl}}/tasks/getNamesfromRoleandDesignation/
# Use in the dropdown of fiels "Assigned_to" while assigning/ creating tasks.
def get_Names_from_selected_role_and_desigantion(request: HttpRequest):
   designation=request.GET.get("designation")
   role=request.GET.get("role")
   try:
    # if not user
    if not request.user:
        return JsonResponse({"error": "login required"}, status=404)
    elif not role and not designation:
        names=Profile.objects.all().order_by("Name").values("Name")
    elif role and not designation:
        passed_role=get_role_object(role=role)
        names=Profile.objects.filter(Role=passed_role).order_by("Name").values("Name")
    elif designation and not role:
        passed_designation=get_designation_object(designation=designation)
        names=Profile.objects.filter(Designation=passed_designation).order_by("Name").values("Name")
    elif role and designation:
        passed_role=get_role_object(role=role)
        passed_designation=get_designation_object(designation=designation)
        names=Profile.objects.filter(Role=passed_role,Designation=passed_designation).order_by("Name").values("Name")
    else:
        return JsonResponse({"message":"pass the correct designation or Role to filter names"}, status=status.HTTP_404_NOT_FOUND)
   except Exception as e:
       return JsonResponse({"message":f"{e}"}, status=status.HTTP_404_NOT_FOUND)
   else:
        return JsonResponse(list(names), status=status.HTTP_200_OK,safe=False)

# Get all the types of task that can be assingnable.
# endpoint-{{baseurl}}/tasks/getTaskTypes/
# Use in the dropdown of TaskTypes while creating a task
def get_types(request: HttpRequest):
    task_types=TaskTypes.objects.all().values("type_name")
    return JsonResponse(list(task_types),safe=False)

def get_assignees(task:Task):
    try:
        assignees=TaskAssignies.objects.filter(task=task).select_related("assigned_to").annotate(assignee=F("assigned_to__accounts_profile__Name")).values("assignee")
    except Exception as e:
        return None
    else:
        return assignees
    
def get_default_task_status():
    TaskStatus_obj=get_taskStatus_object(status_name="PENDING")
    if not None:
        return TaskStatus_obj
    else:
        None
    

# Fetch tasks by its types
# endpoint for "Created_Tasks"-{{baseurl}}/tasks/viewTasks/?type= 
# endpoint for "Assigned_Reported"-{{baseurl}}/tasks/viewAssignedTasks/?type= 
def get_tasks_by_type(request:HttpRequest,type:str="all",self_created: bool=True,Date=None):
    # if not Date:
    #     current_date=datetime.now().date()
    if type.lower()=="all" and self_created:
        tasks=Task.objects.filter(created_by=request.user)
        task_data=[]
        for t in tasks:
            users_name=get_users_Name(t.created_by)
            assignee=list(get_assignees(task=t))
            sample={
                "task_id":t.task_id,
                "title":t.title,
                "description":t.description,
                "status":t.status.status_name,
                "due-date":t.due_date.strftime("%d/%m/%Y"),
                "report_to":users_name,
                "created_by":users_name,
                "created_at":t.created_at.strftime("%d/%m/%Y"),
                "assigned_to":assignee,
                "reported_by":assignee,
                "type":t.type.type_name,
            }
            task_data.append(sample)
        return task_data
    
    elif type and self_created:
        type_obj=TaskTypes.objects.get(type_name=type)
        tasks=Task.objects.filter(created_by=request.user,type=type_obj)
        task_data=[]
        for t in tasks:
            users_name=get_users_Name(t.created_by)
            assignee=list(get_assignees(task=t))
            sample={
                "task_id":t.task_id,
                "title":t.title,
                "description":t.description,
                "status":t.status.status_name,
                "due-date":t.due_date.strftime("%d/%m/%Y"),
                "created_at":t.created_at.strftime("%d/%m/%Y"),
                "report_to":users_name,
                "created_by":users_name,
                "assigned_to":assignee,
                "reported_by":assignee,
                "type":t.type.type_name,
            }
            task_data.append(sample)
        return task_data
    
    elif type.lower()=="all" and not self_created:
        Task_assignee=TaskAssignies.objects.select_related("task").filter(assigned_to=request.user)
        task_data=[]
        for task in Task_assignee:
            task_obj=task.task
            users_name=get_users_Name(task_obj.created_by)
            # print(task_obj.created_at.date())
            # print(task_obj.created_at.date()==current_date)
            # if task_obj.created_at.date() == current_date:
            sample={
                    "task_id":task_obj.task_id,
                    "title":task_obj.title,
                    "description":task_obj.description,
                    "status":task_obj.status.status_name,
                    "created_by":users_name,
                    "report_to":users_name,
                    "created_at":task_obj.created_at.strftime("%d/%m/%Y"),
                    "due-date":task_obj.due_date.strftime("%d/%m/%Y"),
                    "created_at":task_obj.created_at.strftime("%d/%m/%Y"),
                    "type":task_obj.type.type_name,
                }
            task_data.append(sample)
        return task_data
    
    elif type and not self_created:
        Task_assignee=TaskAssignies.objects.select_related("task").filter(assigned_to=request.user)
        task_data=[]
        for task in Task_assignee:
            task_obj=task.task
            users_name=get_users_Name(task_obj.created_by)
            # if task_obj.type.type_name==type and task_obj.created_at.date()==current_date:
            sample={
                    "task_id":task_obj.task_id,
                    "title":task_obj.title,
                    "description":task_obj.description,
                    "status":task_obj.status.status_name,
                    "created_by":users_name,
                    "report_to":users_name,
                    "due-date":task_obj.due_date.strftime("%d/%m/%Y"),
                    "created_at":task_obj.created_at.strftime("%d/%m/%Y"),
                    "type":task_obj.type.type_name,
                }
            task_data.append(sample)
        return task_data

    else:
        tasks=[{"message":"Incorrect type for tasks"}]
    
    return JsonResponse(tasks,safe=False,status=status.HTTP_200_OK)