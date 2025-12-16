# from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.hashers import get_hasher
from django.http.response import HttpResponse
from django.http.request import HttpRequest
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
# from .models import farm_emp_details,infra_emp_details,Employee_login_details
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from functools import wraps
from django.views.decorators.csrf import csrf_exempt
import json

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Login required")

        if request.user.role != "Admin":
            return HttpResponseForbidden("Admin access only")

        return view_func(request, *args, **kwargs)
    return wrapper

# @login_required
# @admin_required
# def create_employee(request):
#     if request.method == "POST":
#         _emp_id= request.POST['emp_id']
#         _password = request.POST['password']
#         _name=request.POST['name']
#         _role=request.POST['role']
#         _email=request.POST['email_id']
#         _designation=request.POST['designation']
#         team:str=request.POST['Team']
        
#         user = Employee_login_details.objects.create(
#             username=_emp_id,
#             password=_password,
#             role=_role
#         )
#         user.set_password(_password)
#         user.save()

#         if team.split(" ")[0]=="Farm":
            
#             _team=team.split(" ")[1]
#             empl=farm_emp_details.objects.create(emp_id=_emp_id,name=_name,part_of=_team,role=_role,designation=_designation)
#             empl.save()
            
#         else:
#             _team=team.split(" ")[1]
#             empl=infra_emp_details.objects.create(emp_id=_emp_id,name=_name,part_of=_team,role=_role,designation=_designation)
#             empl.save()

#         return HttpResponse(Stauts_code=200,content="Employee created successfully")

#     else:
#         return HttpResponse(farm_emp_details.objects.all())
    
@login_required
def admin_dashboard(request):
    # return render(request, "admin_dashboard.html")
    return HttpResponse("admin dashboard")

@csrf_exempt
def user_login(request:HttpRequest):
    if request.method == "POST":
        # data=json.loads(request.body)
        # u = data.get('username')
        # p = data.get('password')
        u=request.POST.get('username')
        
        p=request.POST.get('password')
        
        # return HttpResponse(content=u+p)

        # user=authenticate(request=request,username=_username,password=_password)
        user= authenticate(username=u,password=p)
         
        if not user:
            try:
                user=User.objects.create_user(username=u,password=p)
                user.save()
                return HttpResponse("user saved successfully")
            # user.set_password()
            except Exception as e:
                return HttpResponse(e)
            
        else:
            login(request,user)
            return HttpResponse(str(User.objects.filter(username=u)))
                


                # return redirect('admin_dashboard')
        # else:
            # return render(request, "login.html", {"error": "Invalid credentials"})
            # return HttpResponse("Login failed")

    # return render(request, "login.html")
    return HttpResponse("Login Here")
    
@login_required
def employee_dashboard(request: HttpRequest):

    print(request.body)
    # return render(request, "employee_dashboard.html")
    
    return HttpResponse("Hello dashboard")

@login_required
def user_logout(request: HttpRequest):
    logout(request)
    request.session.flush()
    


# Create your views here.
