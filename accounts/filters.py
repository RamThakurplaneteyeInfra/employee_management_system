import json
from django.http import HttpRequest, JsonResponse
from django.views import View
from accounts.models import Designation,Roles,Profile,User,Branch
from django.db import models
from rest_framework import status
# from django.shortcuts import get_object_or_404

# get an user's "Profile" object from user's "User" object
def get_user_profile_object(user:User):
    try:
        profile=Profile.objects.get(Employee_id=user)
    except Exception as e:
        return {"message":f"{e}"}
    else:
        return profile
    
# get an user's "User" object from its username
def get_user_object(username:str):
    try:
        user=User.objects.get(username=username)
    except Exception as e:
        return {"message":f"{e}"}
    else:
        return user

#get a "Role" object from role_name 
def get_role_object(role=str):
    try:
        user_role=Roles.objects.get(role_name=role)
    except Exception as e:
        return {"message":f"{e}"}
    else:
        return user_role
    
# get a "Designation" object from an input designation
def get_designation_object(designation:str):
    try:
        user_designation=Designation.objects.get(designation=designation)
    except Exception as e:
        return {"message":f"{e}"}
    else:
        return user_designation
    
# get a "Branch" object from a branch name
def get_branch_object(branch=str):
    try:
        user_branch=Branch.objects.get(branch_name=branch)
    except Exception as e:
        return {"message":f"{e}"}
    else:
        return user_branch
    
# get an user's "Role" from "User" objects
def get_user_role(user=User):
    try:
        role=Profile.objects.get(Employee_id=user).Role
    except Exception as e:
        return {"message":f"{e}"}
    else:
        return role.role_name
    
# filter designations for a particular role.
# endpoint={{baseurl}}/accounts/getDesignations/?Role=Employee.
# Use in the dropdown as for designations.
def get_designations(request:HttpRequest):
    data=request.GET
    if data.get("Role")=="MD" or data.get("Role")=="Admin":
        designations=[{}]
    else:
        designations=Designation.objects.all().values("designation")
    return JsonResponse(list(designations),safe=False)

# get all defined roles in an organisation.
# endpoint={{baseurl}}/accounts/getRoles/.
# use in the dropdown of roles.
def get_roles(request: HttpRequest):
    roles=Roles.objects.exclude(role_id=1).values("role_name")
    return JsonResponse(list(roles),safe=False)

# Get all respective departments or branches in an organisation.
# endpoint={{baseurl}}/accounts/getBranch/
# use in the dropdown of branches.
def get_branches(request: HttpRequest):
    data=request.GET
    if data.get("Role")=="MD" or data.get("Role")=="Admin":
        branch=[{}]
    else:
        branch=Branch.objects.all().values("branch_name")
    return JsonResponse(list(branch),safe=False)

# empty
def get_designations_by_branch(request: HttpRequest):
    ...
    
# empty
def get_role_wise_count(request:HttpRequest):
    ...
    
# to verify POST request
# use in the view that has been passed in the respective path function of the requested url.
def verifyPost(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return None
    
# to verify GET request
# use in the view that has been passed in the respective path function of the requested url.
def verifyGet(request: HttpRequest):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return None
    
# to verify DELETE request 
# use in the view that has been passed in the respective path function of the requested url.
def verifyDelete(request: HttpRequest):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return None
    
# to verify PATCH request
# use in the view that has been passed in the respective path function of the requested url.
def verifyPatch(request: HttpRequest):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return None
    
# to verify PUT request
# use in the view that has been passed in the respective path function of the requested url.
def verifyPut(request: HttpRequest):
    if request.method != "PUT":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return None
    
# to load data from an incoming request
# use in the view that receives requests of the method POST, PUT, PATCH.
def load_data(request: HttpRequest):
    if request.content_type=="application/json":
        request_data=json.loads(request.body)
    else:
        request_data=request.POST
    return request_data

# If there are files, use the below one to load
def load_files_data(request: HttpRequest):
    files=request.FILES
    if files:
        return files
    else:
        return None
