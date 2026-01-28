from django.http import HttpRequest, JsonResponse
from accounts.models import *
from datetime import date
from rest_framework import status

# get an user's "Profile" object from the user's "User" object
def get_user_profile_object(user:User|None):
    try:
        if user:
            profile=Profile.objects.get(Employee_id=user)
            return profile
    except Profile.DoesNotExist as e:
        return None
    else:
        return None
    
# get an user's "User" object from an username
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
    # print(data)
    if data.get("Role")=="MD" or data.get("Role")=="Admin":
        designations=[{}]
    else:
        designations=Designation.objects.all().values("designation")
    # print(designations)
    return JsonResponse(list(designations),safe=False)

def get_department_obj(dept=str):
    try:
        dept_obj=Departments.objects.get(dept_name=dept)
    except Exception as e:
        print(e)
        return JsonResponse({"Message":f"{e}"},status=status.HTTP_403_FORBIDDEN)
    else:
        return dept_obj
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
    
def get_users_Name(user:User|None):
    if isinstance(user,User):
        profile_obj=get_user_profile_object(user)        
        return profile_obj.Name if profile_obj else None
    return None

def get_photo_url(user_profile: Profile):
    if user_profile.Photo_link:
        return user_profile.Photo_link.url
    else:
        None
        
def get_departments_and_functions(request: HttpRequest):
    data=request.GET
    role=data.get("Role")
    # print(role)
    if role in ["Admin","MD"]:
        response=[{}]
    else:
        departments=Departments.objects.all()
        functions=Functions.objects.all()
        response={"Departments":[i.dept_name for i in departments],"functions":[j.function for j in functions]}
    return JsonResponse(response,safe=False,status=status.HTTP_200_OK)

def completed_years_and_days(start_date: date) -> str:
    end_date = date.today()
    if start_date >end_date:
        return "Null"

    # Step 1: Calculate completed years
    years = end_date.year - start_date.year

    # Adjust if anniversary not yet reached
    anniversary = start_date.replace(year=start_date.year + years)
    if anniversary > end_date:
        years -= 1
        anniversary = start_date.replace(year=start_date.year + years)

    # Step 2: Remaining days
    days = (end_date - anniversary).days

    return f"{years} years {days} days"