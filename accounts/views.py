# from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.hashers import get_hasher
# from django.http.response import HttpResponse
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
from .models import Profile
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden,QueryDict
from functools import wraps
from django.views.decorators.csrf import csrf_exempt,csrf_protect
import json
from rest_framework import status
from django.http.response import JsonResponse

def home(request: HttpRequest):
    return JsonResponse({"messege":"You are at Accounts section"})

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Login required")

        if request.user.is_superuser:
            return view_func(request,*args,**kwargs)

        
        return JsonResponse({"messege":"Admin access only"},status=status.HTTP_204_NO_CONTENT)
    return wrapper

@csrf_exempt
@admin_required
def create_employee_login(request: HttpRequest):
    if request.method == "POST":
        if request.content_type=="application/json":
            
            data=json.loads(request.body)
            _username= data.get('Employee ID')
            _password = data.get('Initial Password')
            _name=data.get('Full Name')
            _role=data.get('Role')
            _email=data.get('Email Address')
            _designation=data.get('Designation')
            _date_of_join=data.get('Joining Date')
            _date_of_birth=data.get('Date of Birth')
            _branch=data.get('Branch')
            _photo_link=data.get('Profile picture')
            
    # for other types of body content 
        else:
            data=request.POST
            _username=data.get('Employee ID')
            _password=data.get('Initial Password')
            _name=data.get('Full Name')
            _role=data.get('Role')
            _email=data.get('Email Address')
            _designation=data.get('Designation')
            _date_of_birth=data.get('Date of Birth')
            _date_of_join=data.get('Joining Date')
            _branch=data.get('Branch')
            _photo_link=request.FILES.get("Profile Picture")
            
        try:
            user = User.objects.create(
                username=_username,
                password=_password,
                email=_email
            )
            user.set_password(_password)
            user.save()
        except Exception as e:
            return JsonResponse({"messege":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
            
        try:
            user_profile=Profile.objects.create(Role=_role,Employee_id=user,Designation=_designation,Branch=_branch,Date_of_birth=_date_of_birth,Email_id=_email,Name=_name,Date_of_join=_date_of_join,Photo_link=_photo_link)
            user_profile.save()
            
            # return HttpJsonResponse(content="Employee created successfully")
            return JsonResponse({"messege":"Employee Created successfully"},status=status.HTTP_201_CREATED)
        except Exception as e:
            return JsonResponse({"messege":f"{e}"},status=status.HTTP_204_NO_CONTENT)
    else:
        # return HttpJsonResponse(content="create employee login credential here
        return JsonResponse({"messege":"create employee login credentials here"},status=status.HTTP_204_NO_CONTENT)
    
@login_required
@admin_required
def admin_dashboard(request: HttpRequest):
    # return render(request, "admin_dashboard.html")
    
    return  JsonResponse({"messege":"this is admin info dashboard","username":f"{request.user.username}"},status=status.HTTP_200_OK)

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
            data=request.POST
            u=data.get('username')
            p=data.get('password')
            
    else:
        return  JsonResponse({"messege":"Login Here"},status=status.HTTP_200_OK)
    
    user= authenticate(request,username=u,password=p)
        
    if not user:
            return  JsonResponse({"messege":"Incorrect userID/Password"},status=status.HTTP_404_NOT_FOUND)
            
    else:
            login(request,user)
            profile=Profile.objects.filter(Employee_id=user).values("Role")
            if profile:
                return  JsonResponse({"messege":"You are logged in","username":f"{request.user.username}","Role":f"{profile}"},status=status.HTTP_202_ACCEPTED)
            else:
                return  JsonResponse({"messege":"You are logged in","username":f"{request.user.username}","Role":"Admin"},status=status.HTTP_202_ACCEPTED)


@login_required
def employee_dashboard(request: HttpRequest):

    user=User.objects.get(username=request.user)
    profile=Profile.objects.filter(Employee_id=user).values()
    return  JsonResponse(profile)

@login_required
def user_logout(request: HttpRequest):
    logout(request)
    request.session.flush()
    return  JsonResponse({"messege":"Logout successfully"},status=status.HTTP_200_OK)
    
@csrf_exempt
@admin_required
def update_profile(request: HttpRequest):
    if request.method in ['PUT','PATCH','POST']:
        try:
            if request.content_type=="application/json":
                data=json.loads(request.body)
                _username = data.get('Employee ID')
                _password = data.get('Initial Password')
                _name=data.get('Full Name')
                _role=data.get('Role')
                _email=data.get('Email Address')
                _designation=data.get('Designation')
                _branch=data.get('Branch')
                _date_of_join=data.get('Joining Date')
                _date_of_birth=data.get('Date of Birth')
                # return HttpJsonResponse("error occured")
                
# for other body content types
            else:
                data=request.POST
                _username=data.get('Employee ID')
                _password=data.get('Initial Password')
                _role=data.get('Role')
                _name=data.get('Full Name')
                _email=data.get('Email Address')
                _designation=data.get('Designation')
                _branch=data.get('Branch')
                _date_of_join=data.get('Joining Date')
                _date_of_birth=data.get('Date of Birth')
                _photo_link=request.FILES.get("Profile Picture")
                # return HttpJsonResponse(data)
        except Exception as e:
            return  JsonResponse({"messege":f"{e}"},status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        else:
            try:
                user=User.objects.get(username=_username)
                profile=Profile.objects.get(Employee_id=user)
                # return HttpJsonResponse("run")
            except Exception as e:
                return  JsonResponse({"messege":f"{e}"},status=status.HTTP_404_NOT_FOUND)
            
        try:    
            setattr(user,'password',_password)
            user.set_password(_password)
            user.save()
        except Exception as e:
            return  JsonResponse({"messege":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
        else:
            setattr(profile,'Role',_role)
            setattr(profile,'Branch',_branch)
            setattr(profile,'Designation',_designation)
            setattr(profile,'Email_id',_email)
            setattr(profile,'Date_of_join',_date_of_join)
            setattr(profile,'Date_of_birth',_date_of_birth)
            setattr(profile,'Name',_name)
            setattr(profile,'Photo_link',_photo_link)
            profile.save()
            return  JsonResponse({"messege":"user details update successfully"},status=status.HTTP_205_RESET_CONTENT)
    else:
        return  JsonResponse({"messege":"update users here"},status=status.HTTP_200_OK)

# Individual Employee Dashboard View
@login_required
@admin_required
def admin_employee_dashboard_view(request: HttpRequest,username):

    user=User.objects.get(username=username)
    profile=Profile.objects.filter(Employee_id=user).values()
    return  HttpResponse(profile)
