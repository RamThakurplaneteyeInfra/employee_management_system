from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import *
from accounts.models import *
from django.db.models import Q
from django.http.request import HttpRequest
import json
from django.views.decorators.csrf import csrf_exempt 

def home(request: HttpRequest):
    if request.method == "GET":
        return JsonResponse({"message":"You are at tasks page"},status=200)
    else:
        return JsonResponse({"message":"Method is not allowed"},status=405)

@csrf_exempt
@login_required
def create_task(request:HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    user = request.user
    # profile = Profile.objects.get(Employee_id=user)
    if request.content_type=="application/json":
        data=json.loads(request.body)
    else:
        data=request.POST

    title = data.get("title")
    description = data.get("description")
    due_date=data.get("due_date")
    assigned_to=data.get("assigned_to")
    type=data.get("type")
    if not title or not assigned_to or not due_date or not type:
        return JsonResponse({"error": "Missing fields"}, status=400)
    
    try:
        task_type_id=TaskTypes.objects.get(type_name=type)
        # if assigned_to!= "self":
        u_profile= Profile.objects.get(Name=assigned_to)
        assigned_to=u_profile.Employee_id
    except Exception as e:
        return JsonResponse({"message":f"{e}"})

    task = Task.objects.create(
        title=title,
        description=description,
        created_by=request.user,
        assigned_to=assigned_to,
        due_date=due_date,
        type=task_type_id,
    )

    return JsonResponse(
        {"message": "Task created"},
        status=201
    )
@login_required 
def edit_tasks(request: HttpRequest,task_id):
    
    ...
@login_required
def get_available_roles(request: HttpRequest):
    profile=Profile.objects.get(Employee_id=request.user)
    if request.GET:
        role=request.GET.get("role")
    else:
        role=profile.Role
    if role=="MD":
        roles=Roles.objects.filter().values("role_name")
        return JsonResponse(list(roles),safe=False,status=200)
    elif role=="TeamLead":
        roles=Roles.objects.exclude(Q(role_name="MD") | Q(role_name="Admin")).values("role_name")
        return JsonResponse(list(roles),safe=False,status=200)
    elif role=="Employee":
        roles=Roles.objects.exclude(Q(role_name="MD") | Q(role_name="Admin")).values("role_name")
        return JsonResponse(list(roles),safe=False,status=200)
    elif role=="Intern":
        roles=Roles.objects.exclude(Q(role_name="MD") | Q(role_name="Admin")).values("role_name")
        return JsonResponse(list(roles),safe=False,status=200)
    else:
        roles=[{}]
        return JsonResponse(list(roles),safe=False,status=200)
    
@login_required
def get_usernames_from_selected_role_and_desigantion(request: HttpRequest):

   designation=request.GET.get("designation")
   role=request.GET.get("role")
   try:
    # if not user
    if not request.user:
        return JsonResponse({"error": "login required"}, status=404)
    # for md
    elif not role and not designation:
        names=Profile.objects.filter().values("Name")
    elif not role:
        names=Profile.objects.filter(Designation=designation).values("Name")
    elif not designation:
        names=Profile.objects.filter(Role=role).values("Name")
    elif role=="MD" and not designation:
        names=Profile.objects.filter(Role="MD").values("Name")
    elif role=="MD" and designation:
        names=Profile.objects.filter(Role="MD",Designation=designation).values("Name")
    # for team lead
    elif role=="TeamLead" and  not designation:
        names=Profile.objects.exclude(Q(Role="MD") | Q(Role="Admin")).values("Name")
    elif role=="TeamLead" and  designation:
        names=Profile.objects.filter(Q(Role="Intern") | Q(Role="Employee") | Q(Role="TeamLead"),Designation=designation).values("Name")
    # for employees
    elif role=="Employee" and  not designation:
        names=Profile.objects.exclude(Role="MD").values("Name")
    elif role=="Employee" and  designation:
        names=Profile.objects.filter(Q(Role="Employee") | Q(Role="Intern") | Q(Role="TeamLeader"),Designation=designation).values("Name")
    # for interns
    elif role=="Intern" and  not designation:
        names=Profile.objects.exclude(Q(Role="MD") | Q(Role="admin")).values("Name")
    elif role=="Intern" and  designation:
        names=Profile.objects.filter(Q(Role="Employee") | Q(Role="Intern") | Q(Role="TeamLEad"),Designation=designation).values("Name")
    else:
        return JsonResponse({"message":"Choose the correct designation"}, status=302)
    
    return JsonResponse(list(names), status=200,safe=False)
    
   
   except Exception as e:
       return JsonResponse({"message":f"{e}"}, status=401)
   
@login_required
def show_created_tasks(request: HttpRequest):
    if request.method!="GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    if request.user.is_superuser:
        tasks=Task.objects.filter().select_related().values()
        return JsonResponse(list(tasks),safe=False,status=200)
        
    else:
        try:
            tasks=Task.objects.select_related("status","type")
            for task in tasks:
                print(task.type.type_name)
            # return JsonResponse({"msg":"runs"})
        except Exception as e:
            return JsonResponse({"msg":f"{e}"})
        else:
            # return JsonResponse(list(tasks),safe=False,status=200)
    
@login_required
def show_assigned_tasks(request: HttpRequest):
    if request.method!="GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    if request.user.is_superuser:
        tasks=Task.objects.select_related("status","type")
        return JsonResponse(list(tasks),safe=False,status=200)
    
    try:
        tasks=Task.objects.filter(assigned_to=request.user).select_relatedvalues()
    except Exception as e:
        return JsonResponse({"message":f"{e}"})
    else:
        return JsonResponse(list(tasks),safe=False,status=200)
        
@login_required
@csrf_exempt
def change_status(request: HttpRequest,task_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    data=json.loads(request.body)
    changed_to=data.get("changed_status")
    
    task=Task.object.get(task_id=task_id)
    changed_to=TaskStatus.objects.get(status_name=changed_to).status_id
    setattr(task,"current_status",changed_to)
    task.save()
    
    return JsonResponse({"message":f"Status Changed to {changed_to}"})

def sort_tasks_by_date(request: HttpRequest):
    ...
    
def sort_tasks_by_type(request: HttpRequest):
    ...
    
def sort_tasks_by_status(request:HttpRequest):
    ...
    
def sort_tasks_by_Role(request: HttpRequest):
    ...
    
def sort_Tasks_by_designation(request: HttpRequest):
    ...
    
def sort_tasks_by_assigend_to(request: HttpRequest):
    ...
    
def sort_tasks_by_assigned_by(request: HttpRequest):
    ...
    
    
    

