from .filters import *
from .models import *
from accounts.RequiredImports import *
# # # # # #  baseurl="http://localhost:8000" # # # # # # # # # # # # 

# Lands on the Home page.applicable method-"GET"
@login_required
def home(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    else:
        return JsonResponse({"message":"You are at tasks page"},status=status.HTTP_200_OK)

# Create a New task.applicable method-"POST"
@csrf_exempt
@login_required
def create_task(request:HttpRequest):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    # print("Error1")
    user = request.user
    data=load_data(request)
    required_fields=["title","description","due_date","assigned_to","type"]
    body_data={}
    # print("error2")
    for i in required_fields:
        field_value=data.get(i)
        if not field_value:
            # print("Error3")
            return JsonResponse({"error": f"{i} is required"}, status=status.HTTP_206_PARTIAL_CONTENT)
        body_data[i]=data.get(i)
    # print(body_data)
    try:
        body_data["type"]=TaskTypes.objects.get(type_name=body_data["type"])
        u_profile= Profile.objects.get(Name=body_data["assigned_to"])
        body_data["assigned_to"]=u_profile.Employee_id
        body_data["created_by"]=request.user
    except Exception as e:
        # print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_501_NOT_IMPLEMENTED)
    else:
        try:
            task = Task.objects.create(**body_data)
            task.save()
            # print("error 5")
            return JsonResponse({"message": "Task created"},status=status.HTTP_201_CREATED) 
        except Exception as e:
            # print(e)
            return JsonResponse({"message":f"{e}"},status=status.HTTP_501_NOT_IMPLEMENTED)
        
# Update a particular Task. applicable method-"POST",insert path parameter "task_id" of type integer. 
# endpoint-{{baseurl}}/tasks/{task_id}/updateTask/
@csrf_exempt
@login_required
def update_task(request,task_id:int):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    elif not isinstance(task_id,int):
        return JsonResponse({"error": "Invalid data type of task_id.It must be integer"}, status=status.HTTP_404_NOT_FOUND)
    try:
        user = request.user
        task=get_task_object(task_id=task_id)
        if request.user!=task.created_by:
            raise PermissionDenied("Not allowed")
    except PermissionDenied:
        return JsonResponse({"message":"you cannot update or edit this task"},status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    
    fields=["title","description","due_date","assigned_to","type"]
    body_data={}
    data=load_data(request)
    for i in fields:
        field_value=data.get(i)
        if not field_value and i!="description":
            return JsonResponse({"error": f"{i} is required"}, status=302)
            ...
        body_data[i]=data.get(i)
    try:
        body_data["type"]=get_taskTypes_object(type_name=body_data["type"])
        u_profile= Profile.objects.get(Name=body_data["assigned_to"])
        body_data["assigned_to"]=u_profile.Employee_id
    except Exception as e:
        return JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    try:
        task=Task.objects.filter(task_id=task_id).update(**body_data)
    except Exception as e:
        JsonResponse({"message":f"{e}"},status_code=302)
    else:
        return JsonResponse(
        {"message": "Task updated successfully"},status=status.HTTP_200_OK) 
    ...
    
# Show self created tasks.applicable method-"GET"
# endpoint-{{baseurl}}/tasks/viewTasks/?type=
@login_required
def show_created_tasks(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    type=request.GET.get("type")
    try:
        if type in ["all","SOS","1 Day","10 Day","Monthly","Quaterly"]:
            response=get_tasks_by_type(request=request,type=type)
        else:
            response=get_tasks_by_type(request)
        # print(response)
        return JsonResponse(response,safe=False)
    except Exception as e:
        return JsonResponse({"msg":f"{e}"},status=status.HTTP_501_NOT_IMPLEMENTED)
    ...
    
# Shows assigned/reporting tasks by other users.applicable method-"GET"
# endpoint-{{baseurl}}/tasks/viewAssignedTasks/?type=
@login_required
def show_assigned_tasks(request: HttpRequest):
    if request.method!="GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    type=request.GET.get("type")
    try:
        if type in ["all","SOS","1 Day","10 Day","Monthly","Quaterly"]:
            response=get_tasks_by_type(request,type=type,self_created=False)
        else:
            response=get_tasks_by_type(request,self_created=False)
        # print(response)
        return JsonResponse(response,safe=False)
    except Exception as e:
        return JsonResponse({"msg":f"{e}"})
    ...

# change status of a task.applicable method-"PATCH".request content-type-"application/json"
# endpoint-{{baseurl}}/tasks/{id}/changeStatus/
@login_required
@csrf_exempt
def change_status(request: HttpRequest,id):
    request_method=verifyPatch(request)
    if request_method:
        return request_method
    data=load_data(request)
    changed_to:str=data.get("change_Status_to")
    try:
        task=get_task_object(task_id=id)
        changed_status=get_taskStatus_object(status_name=changed_to.upper())
        setattr(task,"status",changed_status)
        task.save()
    except Exception as e:
        return JsonResponse({"message":f"{e}"})
    else:
        return JsonResponse({"message":f"Status Changed to {changed_to}"})

@csrf_exempt
@login_required
def delete_task(request: HttpRequest,task_id:int):
    verify_request=verifyDelete(request)
    if verify_request:
        return verify_request
    
    try:
        user = request.user
        task=get_task_object(task_id=task_id)
        role=get_user_role(request.user)
        if request.user!=task.created_by and (isinstance(role,str) and (role!="MD" and role!="TeamLead")):
            raise PermissionDenied("Not allowed")
    except PermissionDenied:
        return JsonResponse({"error": "You are not authorised to delete the task"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"})
    else:
        task.delete()
        return JsonResponse({"Message":f"task-id {task_id} deleted successfully"},status=status.HTTP_201_CREATED)
    
####################################### Messaging (API)#####################################################

# Post a message in a task.acceptable method-"POST"
# endpoint-{{baseurl}}/tasks/sendMessage/
@login_required
@csrf_exempt
def post_task_message(request: HttpRequest):
    reqest_method=verifyPost(request)
    if reqest_method:
        return reqest_method
    else:
        try:
            request_data=load_data(request)
            task = get_object_or_404(Task, task_id=request_data.get("task_id"))
        except Exception as e:
            print(e)
            return JsonResponse(f"{e}",status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
        else:
            message_text = request_data.get("message")
            if not message_text:
                return JsonResponse({"error": "Message required"}, status=400)

            TaskMessage.objects.create(
                task=task,
                sender=request.user,
                message=message_text
            )

            return JsonResponse({"status": "Message sent"},status=status.HTTP_201_CREATED)

# Fetch a message in a task
# endpoint-{{baseurl}}/tasks/getMessage/{task_id:int}
@login_required
def get_task_messages(request: HttpRequest, task_id:int):
    request_method=verifyGet(request)
    if request_method:
        return request_method
    else:
        try:
            task:Task= get_object_or_404(Task, task_id=task_id)
            if not(request.user!=task.created_by or request.user!=task.assigned_to):
                raise PermissionDenied("Not allowed")
        except PermissionDenied:
            return JsonResponse({"message":"you are not authorised to accessed this task conversation"},status=status.HTTP_403_FORBIDDEN)
        else:
            messages= task.messages.select_related("sender").order_by("-created_at")
            messages.update(seen=True)

        data = [
            {   
                "sender": m.sender.username,
                "message": m.message,
                "date":m.created_at.strftime("%d/%m/%y"),
                "time": m.created_at.strftime("%H:%M"),
                "seen":m.seen
            }
            for m in messages
        ]

        return JsonResponse(data, safe=False)


def sort_tasks_by_date(request: HttpRequest):
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
    
    
    

