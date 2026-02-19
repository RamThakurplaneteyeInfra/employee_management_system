from asgiref.sync import sync_to_async
from django.http import HttpRequest, JsonResponse
from accounts.models import *
from datetime import date, datetime, timedelta
from rest_framework import status
from django.db import DatabaseError, transaction

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #


# ==================== get_user_profile_object ====================
# Get Profile object from User. (Helper)
def _get_user_profile_object_sync(user: User | None):
    """Sync helper: DB with transaction.atomic."""
    try:
        if user:
            with transaction.atomic():
                return Profile.objects.get(Employee_id=user)
    except Exception:
        return None
    return None


async def get_user_profile_object(user: User | None):
    return await sync_to_async(_get_user_profile_object_sync)(user)


# ==================== get_user_object ====================
# Get User object from username. (Helper)
def _get_user_object_sync(username: str):
    """Sync helper: DB with transaction.atomic."""
    try:
        with transaction.atomic():
            return User.objects.get(username=username)
    except Exception as e:
        return {"message": f"{e}"}
    return None


async def get_user_object(username: str):
    return await sync_to_async(_get_user_object_sync)(username)


# ==================== get_role_object ====================
# Get Role object from role_name. (Helper)
def _get_role_object_sync(role: str):
    """Sync helper: DB with transaction.atomic."""
    try:
        with transaction.atomic():
            return Roles.objects.get(role_name=role)
    except Exception as e:
        return {"message": f"{e}"}
    return None


async def get_role_object(role: str = ""):
    return await sync_to_async(_get_role_object_sync)(role)


# ==================== get_designation_object ====================
# Get Designation object. (Helper)
def _get_designation_object_sync(designation: str):
    """Sync helper: DB with transaction.atomic."""
    try:
        with transaction.atomic():
            return Designation.objects.get(designation=designation)
    except Exception as e:
        return {"message": f"{e}"}
    return None


async def get_designation_object(designation: str):
    return await sync_to_async(_get_designation_object_sync)(designation)


# ==================== get_branch_object ====================
# Get Branch object. (Helper)
def _get_branch_object_sync(branch: str):
    """Sync helper: DB with transaction.atomic."""
    try:
        with transaction.atomic():
            return Branch.objects.get(branch_name=branch)
    except Exception as e:
        return {"message": f"{e}"}
    return None


async def get_branch_object(branch: str = ""):
    return await sync_to_async(_get_branch_object_sync)(branch)


# ==================== get_user_role ====================
# Get user's Role name from User. (Helper)
def _get_user_role_sync(user: User):
    """Sync helper: DB with transaction.atomic."""
    try:
        with transaction.atomic():
            role = Profile.objects.get(Employee_id=user).Role
            return role.role_name
    except Exception:
        return None
    return None


async def get_user_role(user: User):
    return await sync_to_async(_get_user_role_sync)(user)


# ==================== get_users_Name ====================
# Get user's display name. (Helper)
def _get_users_Name_sync(user: User | None):
    """Sync helper: uses get_user_profile_object."""
    if isinstance(user, User):
        profile_obj = _get_user_profile_object_sync(user)
        return profile_obj.Name if profile_obj else None
    return None


async def get_users_Name(user: User | None):
    return await sync_to_async(_get_users_Name_sync)(user)


# ==================== get_designations ====================
# Filter designations by role. URL: {{baseurl}}/accounts/getDesignations/
def _get_designations_sync(role: str):
    """Sync helper: DB with transaction.atomic."""
    if role in ["MD", "Admin"]:
        return [{}]
    with transaction.atomic():
        designations = Designation.objects.all().values("designation")
    return list(designations)


async def get_designations(request: HttpRequest):
    role = request.GET.get("Role")
    data = await sync_to_async(_get_designations_sync)(role)
    return JsonResponse(data, safe=False)


# ==================== get_department_obj ====================
# Get Departments object. (Helper)
def _get_department_obj_sync(dept: str):
    """Sync helper: DB with transaction.atomic."""
    try:
        with transaction.atomic():
            return Departments.objects.get(dept_name=dept)
    except Exception as e:
        return JsonResponse({"Message": f"{e}"}, status=status.HTTP_403_FORBIDDEN)
    return None


async def get_department_obj(dept: str = ""):
    return await sync_to_async(_get_department_obj_sync)(dept)


# ==================== get_roles ====================
# Get all roles. URL: {{baseurl}}/accounts/getRoles/
def _get_roles_sync():
    """Sync helper: DB with transaction.atomic."""
    with transaction.atomic():
        roles = Roles.objects.exclude(role_id=1).values("role_name")
    return list(roles)


async def get_roles(request: HttpRequest):
    data = await sync_to_async(_get_roles_sync)()
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)


# ==================== get_branches ====================
# Get branches by role. URL: {{baseurl}}/accounts/getBranch/
def _get_branches_sync(role: str):
    """Sync helper: DB with transaction.atomic."""
    if role in ["MD", "Admin"]:
        return [{}]
    with transaction.atomic():
        branch = Branch.objects.all().values("branch_name")
    return list(branch)


async def get_branches(request: HttpRequest):
    role = request.GET.get("Role")
    data = await sync_to_async(_get_branches_sync)(role)
    return JsonResponse(data, safe=False)


# ==================== get_departments_and_functions ====================
# Get departments and functions. URL: {{baseurl}}/accounts/getDepartmentsandFunctions/
def _get_departments_and_functions_sync(role: str):
    """Sync helper: DB with transaction.atomic."""
    if role in ["Admin", "MD"]:
        return {"Departments": [{}], "functions": [{}]}
    try:
        with transaction.atomic():
            departments = Departments.objects.all()
            functions = Functions.objects.all()
        return {"Departments": [i.dept_name for i in departments], "functions": [j.function for j in functions]}
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def get_departments_and_functions(request: HttpRequest):
    role = request.GET.get("Role")
    data = await sync_to_async(_get_departments_and_functions_sync)(role)
    if isinstance(data, JsonResponse):
        return data
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)


# ==================== Pure helpers (no DB) ====================
def get_photo_url(user_profile: Profile):
    if user_profile.Photo_link:
        return user_profile.Photo_link.url
    return None


def completed_years_and_days(start_date: date) -> str:
    end_date = date.today()
    if start_date > end_date:
        return "Null"
    years = end_date.year - start_date.year
    anniversary = start_date.replace(year=start_date.year + years)
    if anniversary > end_date:
        years -= 1
        anniversary = start_date.replace(year=start_date.year + years)
    days = (end_date - anniversary).days
    return f"{years} years {days} days"


def get_created_time_format(dt: datetime):
    IST_time = dt + timedelta(hours=5, minutes=30)
    return IST_time.strftime("%d/%m/%Y, %H:%M:%S")
