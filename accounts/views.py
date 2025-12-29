# from django.shortcuts import render
# from django.contrib.auth.models import User
# from django.contrib.auth.hashers import get_hasher
# from django.http.response import HttpResponse
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
from .models import Profile,User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt,csrf_protect
import json
from rest_framework import status
from django.http.response import JsonResponse
from .snippet import admin_required

def home(request: HttpRequest):
    # return JsonResponse({"messege":"You are at Accounts section"})
    # return redirect("/accounts/login")
    # return redirect("login")
    return HttpResponse(status=204)

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
            if not bool(_username and _password and _name and _role and _email and _designation and _date_of_birth and _date_of_join and _branch and _photo_link):
                return JsonResponse({"messege":"All fields are required"},status=status.HTTP_406_NOT_ACCEPTABLE)
            
            
            user = User.objects.create(
                username=_username,
                password=_password,
                email=_email
            )
            user.set_password(_password)
            user.save()
            user_profile=Profile.objects.create(Role=_role,Employee_id=user,
                                                Designation=_designation,Branch=_branch,
                                                Date_of_birth=_date_of_birth,
                                                Email_id=_email,Name=_name,
                                                Date_of_join=_date_of_join,
                                                Photo_link=_photo_link)
            user_profile.save()
            
            # return HttpJsonResponse(content="Employee created successfully")
            return JsonResponse({"messege":"Employee Created successfully"},status=status.HTTP_201_CREATED)
        except Exception as e:
            return JsonResponse({"messege":f"{e}"})
    else:
        # return HttpJsonResponse(content="create employee login credential here
        return JsonResponse({"messege":"create employee login credentials here"},status=status.HTTP_204_NO_CONTENT)
    
@login_required
@admin_required
def admin_dashboard(request: HttpRequest):
    # return render(request, "admin_dashboard.html")
    return  JsonResponse({"messege":"This is a Admin information dashboard","username":f"{request.user.username}"})

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
            return  JsonResponse({"messege":"Incorrect userID/Password"})
            
    else:
            login(request,user)
            profile=Profile.objects.get(Employee_id=user)
            if profile:
                return  JsonResponse({"messege":"You are logged in","username":f"{request.user.username}","Role":profile.Role})
            else:
                return  JsonResponse({"messege":"You are logged in","username":f"{request.user.username}","Role":"Admin"},status=status.HTTP_202_ACCEPTED)


@login_required
def employee_dashboard(request: HttpRequest):
    if request.user.is_superuser:
        profile=Profile.objects.filter().values("Employee_id","Email_id","Designation","Date_of_birth","Date_of_join","Branch","Name","Photo_link","Role")
        # print(profile)
        # return HttpResponse()
    else:
        profile=Profile.objects.filter(Employee_id=request.user).values("Employee_id","Email_id","Designation","Date_of_birth","Date_of_join","Branch","Name","Photo_link","Role")
        
    return  JsonResponse(list(profile),safe=False)

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
                _email_id=data.get('Email Address')
                _designation=data.get('Designation')
                _branch=data.get('Branch')
                _date_of_join=data.get('Joining Date')
                _date_of_birth=data.get('Date of Birth')
                _photo_link=data.get("Profile Picture")
                # return HttpJsonResponse("error occured")
                
# for other body content types
            else:
                data=request.POST
                _username=data.get('Employee ID')
                _password=data.get('Initial Password')
                _role=data.get('Role')
                _name=data.get('Full Name')
                _email_id=data.get('Email Address')
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
                # model_fields=["Role","Designation","Branch","Name","Email_id","Date_of_join","Date_of_birth","Photo_link"]
                # values_to_update=[]
                # for i in fields
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
            Profile.objects.filter(Employee_id=user).update(Role=_role,Branch=_branch,Designation=_designation,Email_id=_email_id,
                                        Date_of_join=_date_of_join,Date_of_birth=_date_of_birth,Photo_link=_photo_link,Name=_name)
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

@login_required
@admin_required
@csrf_exempt
def delete_user_profile(request: HttpRequest,u):
    if request.method=='DELETE':
        user=User.objects.get(username=u)
        # profile=Profile.objects.get(Employee_id=user)
    
        if user:
            user.delete()
            return JsonResponse({"message":"user deleted successfully"})
        else:
            return JsonResponse({"message":"user does not exist"})
    
    else:
            return JsonResponse({"message":"delete user"})
    
        