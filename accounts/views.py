# from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.hashers import get_hasher
from django.http.response import HttpResponse
from django.http.request import HttpRequest
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
# from .models import farm_emp_details,infra_emp_details,Employee_login_details
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden,QueryDict
from functools import wraps
from django.views.decorators.csrf import csrf_exempt,csrf_protect
import json
from .models import Profile

def home(request: HttpRequest):
    return HttpResponse("You are at Accounts section")

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Login required")

        if request.user.is_superuser:
            return view_func(request,*args,**kwargs)

        
        return HttpResponseForbidden("Admin access only")
    return wrapper

@csrf_exempt
@admin_required
def create_employee_login(request: HttpRequest):
    if request.method == "POST":
        if request.content_type=="application/json":
            
            data=json.loads(request.body)
            u = data.get('username')
            p = data.get('password')
            _name=data.get('emp_name')
            _role=data.get('role')
            _email=data.get('email')
            _designation=data.get('designation')
            _date=data.get('date')
            _branch=data.get('branch')
            # _photo_link=data.get('photo_link')
            
        
    # for other types of body content 
        else:
            u=request.POST.get('username')
            p=request.POST.get('password')
            _name=request.POST.get('emp_name')
            _role=request.POST.get('role')
            _email=request.POST.get('email')
            _designation=request.POST.get('designation')
            _date=request.POST.get('date')
            _branch=request.POST.get('branch')
            
            
        try:
            user = User.objects.create(
                username=u,
                password=p,
                email=_email
            )
            user.set_password(p)
            user.save()
        except Exception as e:
            return HttpResponse(e)
            
        try:
            user_profile=Profile.objects.create(role=_role,Emp_id=user,Designation=_designation,Brach=_branch,Date=_date,Email_id=_email,Name=_name)
            user_profile.save()
            
            return HttpResponse(content="Employee created successfully")
        except Exception as e:
            return HttpResponse(e)
    else:
        return HttpResponse(content="create employee login credential here")
    
@login_required
def admin_dashboard(request):
    # return render(request, "admin_dashboard.html")
    
    return HttpResponse("admin dashboard")

@csrf_exempt
def user_login(request:HttpRequest):
    # request content type is in json format
    if request.method == "POST":
        if request.content_type=="application/json":
            
            data=json.loads(request.body)
            u = data.get('username')
            p = data.get('password')
        
    # for other types of body content 
        else:
            u=request.POST.get('username')
            p=request.POST.get('password')
            
    else:
        return HttpResponse("Login Here")
            
        # user=authenticate(request=request,username=_username,password=_password)
    user= authenticate(request,username=u,password=p)
        
    if not user:
            # try:
                # user=User.objects.create_user(username=u,password=p)
                # user.save()
            return HttpResponse("incorrect username/password")
            # user.set_password()
            # except Exception as e:
                # return HttpResponse(e)
            
    else:
            login(request,user)
            return HttpResponse("you are logged in")
                


                # return redirect('admin_dashboard')
        # else:
            # return render(request, "login.html", {"error": "Invalid credentials"})
            # return HttpResponse("Login failed")

    # return render(request, "login.html")

@login_required
def employee_dashboard(request: HttpRequest):

    user=request.user.objects.get()
    # user_data={"username":user.username,"email":user.email,"password":user.password,}
    # return render(request, "employee_dashboard.html")
    
    return HttpResponse(user)

@login_required
def user_logout(request: HttpRequest):
    logout(request)
    request.session.flush()
    return HttpResponse("user logout")
    
@csrf_exempt
@admin_required
def update_profile(request: HttpRequest):
    if request.method in ["PUT","PATCH"]:
        try:
            if request.content_type=="application/json":
                data=json.loads(request.body)
                u = data.get('username')
                p = data.get('password')
                _role=data.get('role')
                _name=data.get('emp_name')
                _role=data.get('role')
                _email=data.get('email')
                _designation=data.get('designation')
                _date=data.get('date')
                _branch=data.get('branch')
                # return HttpResponse("error occured")
                
# for other body content types
            else:
                data=QueryDict(request.body, encoding="utf-8")
                u=data.get('username')
                p=data.get('password')
                _role=data.get('role')
                _name=data.get('emp_name')
                # _role=data.get('role')
                _email=data.get('email')
                _designation=data.get('designation')
                _date=data.get('date')
                _branch=data.get('branch')
                print(data)
                return HttpResponse(request.body)
        except Exception as e:
            return HttpResponse(content=e)
        
        else:
            try:
                user=User.objects.get(username=u)
                profile=Profile.objects.get(emp_id=user)
                # return HttpResponse("run")
            except Exception as e:
                # print("error lies in the getting section",request.user)
                return HttpResponse(e)
            
        try:    
            setattr(user,'password',p)
            user.set_password(p)
            user.save()
        except Exception as e:
            # print("error lies in the updating section")
            return HttpResponse(content=e)
        else:
            setattr(profile,'role',_role)
            setattr(profile,'Branch',_branch)
            setattr(profile,'Designation',_designation)
            setattr(profile,'Email_id',_email)
            setattr(profile,'Date',_date)
            setattr(profile,'Name',_name)
            profile.save()
            return HttpResponse("user details updated successfully")
    else:
        return HttpResponse(content="Update users here")     
# Create your views here.
