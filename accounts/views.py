import asyncio
import mimetypes
from asgiref.sync import sync_to_async
from django.http import FileResponse
from ems.verify_methods import *
from .models import *
from .snippet import admin_required
from .filters import (
    get_branches,
    get_roles,
    get_designations,
    get_departments_and_functions,
    _get_user_object_sync,
    _get_user_role_sync,
    _get_user_profile_object_sync,
    _get_role_object_sync,
    get_photo_url,
    completed_years_and_days,
)

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #


# ==================== home ====================
# Home page placeholder. Returns 204 No Content.
# URL: {{baseurl}}/accounts/
# Method: GET
async def home(request: HttpRequest):
    return HttpResponse(status=204)


# ==================== birthdaycounter ====================
# Increment or fetch birthday counter for a user.
# URL: {{baseurl}}/accounts/birthdaycounter/<username>/  (or as configured)
# Method: GET (fetch) | POST (increment)
def _birthdaycounter_sync(username, method):
    """Sync helper: DB operations with transaction.atomic."""
    user_obj = get_object_or_404(User, username=username)
    user_profile = Profile.objects.select_related("Employee_id").filter(Employee_id=user_obj).first()
    if method == "POST":
        with transaction.atomic():
            user_profile.birthday_counter += 1
            user_profile.save()
    return {"birthday_counter": user_profile.birthday_counter}


async def birthdaycounter(request: HttpRequest, username=None):
    try:
        result = await sync_to_async(_birthdaycounter_sync)(username, request.method)
        return JsonResponse(result, status=status.HTTP_200_OK)
    except Http404:
        return JsonResponse({"message": "user not found"}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== create_employee_login ====================
# Create new employee login and profile (Admin only).
# URL: {{baseurl}}/accounts/admin/createEmployeeLogin/
# Method: POST
def _create_employee_login_sync(req):
    """Sync helper: DB operations. Expects application/x-www-form-urlencoded or multipart/form-data."""
    fields = ['Employee_id', 'password', 'Name', 'Role', 'Email_id', 'Designation', 'Date_of_join', 'Date_of_birth', 'Branch', 'Photo_link', "Department", "Teamlead", "Functions"]
    not_required_field = ["Branch", "Designation", "Department", "Teamlead", "Functions", "Photo_link"]
    login_values = {}
    profile_values = {}
    data, files = req.POST, req.FILES
    # print(data)
    for i in fields:
        if i == "Photo_link":
            field_value = files.get(i)
        elif i == "Functions":
            raw = data.getlist("Functions") or data.get("Functions")
            if raw is None:
                field_value = []
            elif isinstance(raw, list):
                field_value = [v for v in raw if v]
            else:
                field_value = [raw] if raw else []
            profile_values["Functions"] = field_value
            continue
        else:
            field_value = data.get(i)
        if not field_value and i not in not_required_field:
            return {"error": JsonResponse({"messege": f"{i} is required"}, status=status.HTTP_406_NOT_ACCEPTABLE)}
        if i == "Teamlead" and field_value:
            teamlead_user_obj = get_object_or_404(User, username=field_value)
            profile_values["Teamlead"] = teamlead_user_obj
        elif i == 'Employee_id':
            login_values["username"] = str(field_value)
            profile_values["Employee_id"] = field_value
        elif i == 'password':
            login_values[i] = field_value
        elif i == 'Email_id':
            login_values["email"] = field_value
            profile_values[i] = field_value
        elif i not in not_required_field or field_value:
            if i != "Functions":
                profile_values[i] = field_value
    with transaction.atomic():
        check_user = _get_user_object_sync(username=login_values["username"])
        if not isinstance(check_user, User):
            user = User(**login_values)
            user.set_password(login_values["password"])
            user.save()
        else:
            user = check_user
    profile_values["Employee_id"] = user
    function_names = profile_values.pop("Functions", [])
    if profile_values["Role"] not in ["MD", "Admin"]:
        with transaction.atomic():
            get_branch = get_object_or_404(Branch, branch_name=profile_values["Branch"])
            get_designation = get_object_or_404(Designation, designation=profile_values["Designation"])
            get_department = get_object_or_404(Departments, dept_name=profile_values["Department"])
        profile_values["Department"] = get_department
        profile_values["Branch"] = get_branch
        profile_values["Designation"] = get_designation
    with transaction.atomic():
        get_role = get_object_or_404(Roles, role_name=profile_values["Role"])
        profile_values["Role"] = get_role
        profile = Profile.objects.create(**profile_values)
        if function_names:
            function_objs = list(Functions.objects.filter(function__in=function_names))
            profile.functions.set(function_objs)
    return {"ok": True}


@admin_required
@csrf_exempt
async def create_employee_login(request: HttpRequest):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    try:
        result = await sync_to_async(_create_employee_login_sync)(request)
        if "error" in result:
            return result["error"]
        return JsonResponse({"messege": "user profile created successfully"}, status=status.HTTP_200_OK)
    except Http404 as e:
        return JsonResponse({"messege": f"{e}"})
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return JsonResponse({"messege": f"{e}"}, status=status.HTTP_406_NOT_ACCEPTABLE)


# ==================== get_all_employees ====================
# Fetch all employees/users in the record.
# URL: {{baseurl}}/accounts/employees/
# Method: GET
def _get_all_employees_sync():
    """Sync helper: DB operations with transaction.atomic."""
    with transaction.atomic():
        profiles = Profile.objects.all().select_related(
            "Role", "Designation", "Branch", "Department", "Employee_id", "Teamlead"
        ).prefetch_related("functions").order_by("Name")
        result = []
        for p in profiles:
            branch = p.Branch.branch_name if p.Branch else None
            designation = p.Designation.designation if p.Designation else None
            role = p.Role.role_name if p.Role else None
            department = p.Department.dept_name if p.Department else None
            lead = p.Teamlead.accounts_profile.Name if (p.Teamlead and hasattr(p.Teamlead, "accounts_profile")) else None
            functions = [f.function for f in p.functions.all()]
            result.append({
                "Name": p.Name,
                "Branch": branch,
                "Designation": designation,
                "Functions": functions,
                "Department": department,
                "Role": role,
                "Teamleader": lead,
                "Photo_link": p.Photo_link.url if p.Photo_link else None,
                "Employee_id": p.Employee_id.username,
                "Date_of_join": p.Date_of_join,
                "Date_of_birth": p.Date_of_birth,
                "Email_id": p.Email_id,
                "Number_of_days_from_joining": completed_years_and_days(start_date=p.Date_of_join),
            })
        return result


@login_required
async def get_all_employees(request: HttpRequest):
    try:
        data_list = await sync_to_async(_get_all_employees_sync)()
        # print("get all employees not from cache")
        return JsonResponse(data_list, safe=False, status=status.HTTP_200_OK)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== get_session_data ====================
# Get session data of the logged-in user.
# URL: {{baseurl}}/accounts/sessiondata/
# Method: GET
@login_required
async def get_session_data(request: HttpRequest):
    try:
        verify_method = verifyGet(request)
        if verify_method:
            return verify_method
        if not request.user:
            return JsonResponse({"messege": "login credentials required"}, status=status.HTTP_200_OK)
        session_data = {}
        session_data["expiray-age"] = request.session.get_expiry_age()
        session_data["expiray-date"] = request.session.get_expiry_date()
        session_data["accessed"] = request.session.accessed
        session_data["is_empty"] = request.session.is_empty()
        return JsonResponse(session_data)
        # print("session data not from cache")
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== user_login ====================
# Login view. Authenticate and create session.
# URL: {{baseurl}}/accounts/login/
# Method: POST
@csrf_exempt
def user_login(req: HttpRequest):
    """Sync helper: authenticate, login, get_user_role. Returns HttpResponse."""
    verify_method = verifyPost(req)
    if verify_method:
        return verify_method
    data = load_data(req)
    u, p = data.get("username"), data.get("password")
    try:
        if not u or not p:
            return JsonResponse({"message": "username or password is missing"}, status=status.HTTP_204_NO_CONTENT)
        user = authenticate(req, username=u, password=p)
        if not user:
            return JsonResponse({"messege": "Incorrect userID/Password,Try again"}, status=status.HTTP_400_BAD_REQUEST)
        login(req, user)
        user_role = _get_user_role_sync(user)
        if not user_role:
            raise DatabaseError("Database Error 500")
    except DatabaseError as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return JsonResponse({"messege": str(e)}, status=status.HTTP_403_FORBIDDEN)
    else:
        return JsonResponse({"messege": "You are logged in", "username": user.username, "Role": user_role}, status=status.HTTP_200_OK)
# ==================== employee_dashboard ====================
# Get logged-in user's profile data.
# URL: {{baseurl}}/accounts/employee/dashboard/
# Method: GET
def _employee_dashboard_sync(request: HttpRequest):
    """Sync helper: DB operations for profile by role (Admin/MD vs regular)."""
    user = request.user
    user_role = _get_user_role_sync(user=user)
    if user.is_superuser and user_role and user_role == "Admin":
        profile = Profile.objects.select_related("Role").filter(Employee_id=user).annotate(role=F("Role__role_name")).values("Employee_id", "Email_id", "Date_of_birth", "Date_of_join", "Name", "Photo_link", "role")
        data = list(profile)
        for row in data:
            row["functions"] = []
        return data
    elif user.is_superuser and user_role and user_role == "MD":
        profile = Profile.objects.select_related("Role").filter(Employee_id=user).annotate(role=F("Role__role_name")).values("Employee_id", "Email_id", "Date_of_birth", "Date_of_join", "Name", "Photo_link", "role")
        data = list(profile)
        for row in data:
            row["functions"] = []
        return data
    else:
        profiles = Profile.objects.select_related("Department", "Branch", "Designation", "Role").prefetch_related("functions").filter(Employee_id=user)
        return [{
            "Employee_id": p.Employee_id_id,
            "Email_id": p.Email_id,
            "designation": p.Designation.designation if p.Designation else None,
            "Date_of_birth": p.Date_of_birth,
            "Date_of_join": p.Date_of_join,
            "branch": p.Branch.branch_name if p.Branch else None,
            "Name": p.Name,
            "Photo_link": p.Photo_link.url if p.Photo_link else None,
            "role": p.Role.role_name if p.Role else None,
            "department": p.Department.dept_name if p.Department else None,
            "functions": [f.function for f in p.functions.all()],
        } for p in profiles]


@login_required
async def employee_dashboard(request: HttpRequest):
    try:
        profile = await sync_to_async(_employee_dashboard_sync)(request)
        # assert not asyncio.iscoroutine(profile), "Accidentally returning a coroutine"
        # return HttpResponse(profile)
        return JsonResponse(profile, safe=False)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== user_logout ====================
# Logout the logged-in user and delete the session.
# URL: {{baseurl}}/accounts/logout/
# Method: GET
def _user_logout_sync(req):
    """Sync helper: logout and session flush with transaction.atomic."""
    user_id = req.user.username
    with transaction.atomic():
        logout(req)
        req.session.flush()
    return user_id


@login_required
async def user_logout(request: HttpRequest):
    try:
        user_id = await sync_to_async(_user_logout_sync)(request)
        return JsonResponse({"messege": f"Logout successfully {user_id}"}, status=status.HTTP_200_OK)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== update_profile ====================
# Update particular user profile by username (Admin only).
# URL: {{baseurl}}/accounts/admin/updateProfile/<username>/
# Method: POST
def _update_profile_sync(req, username):
    """Sync helper: DB operations. Expects application/x-www-form-urlencoded or multipart/form-data."""
    user = get_object_or_404(User, username=username)
    fields = ['Name', 'Role', 'Email_id', 'Designation', 'Date_of_join', 'Date_of_birth', 'Branch', "Department", "Teamlead", "Functions"]
    not_required_fields = ["Designation", "Branch", "Department", "Teamlead", "Functions"]
    profile_values = {}
    data = load_data(req)
    function_names = None
    # print(data)
    for i in fields:
        if i == "Functions":
            raw = data.get("Functions", [])
            if raw is not None:
                function_names = [raw] if not isinstance(raw, list) else [v for v in raw if v]
            continue
        field_value = data.get(i)
        if not field_value and i not in not_required_fields:
            return {"error": JsonResponse({"messege": f"{i} is empty"}, status=status.HTTP_406_NOT_ACCEPTABLE)}
        if not field_value and i in not_required_fields:
            continue
        if i == 'Email_id':
            setattr(user, 'email', field_value)
            user.save()
            profile_values[i] = field_value
        elif i == "Teamlead":
            profile_values[i] = get_object_or_404(User, username=field_value)
        elif i == "Branch":
            profile_values[i] = get_object_or_404(Branch, branch_name=field_value)
        elif i == "Department":
            profile_values[i] = get_object_or_404(Departments, dept_name=field_value)
        elif i == "Designation":
            profile_values[i] = get_object_or_404(Designation, designation=field_value)
        elif i == "Role":
            profile_values[i] = get_object_or_404(Roles, role_name=field_value)
        else:
            profile_values[i] = field_value
    with transaction.atomic():
        Profile.objects.filter(Employee_id=user).update(**profile_values)
        if function_names is not None:
            profile = Profile.objects.get(Employee_id=user)
            function_objs = list(Functions.objects.filter(function__in=function_names))
            profile.functions.set(function_objs)
    return {"ok": True}


@admin_required
@csrf_exempt
async def update_profile(request: HttpRequest, username):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    try:
        result = await sync_to_async(_update_profile_sync)(request, username)
        if "error" in result:
            return result["error"]
        return JsonResponse({"messege": "user details update successfully"}, status=status.HTTP_200_OK)
    except Http404:
        return JsonResponse({"messege": "User Not Found. Incorrect Username Passed in the URL"}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return JsonResponse({"messege": f"{e}"}, status=status.HTTP_406_NOT_ACCEPTABLE)


# ==================== changePassword ====================
# Change password for a user (Admin or self).
# URL: {{baseurl}}/accounts/admin/changePassword/<username>/
# Method: PATCH
def _change_password_sync(username, new_password):
    """Sync helper: DB operations with transaction.atomic."""
    with transaction.atomic():
        user = get_object_or_404(User, username=username)
        user.password = new_password
        user.set_password(new_password)
        user.save(force_update=True)


@csrf_exempt
@admin_required
async def changePassword(request: HttpRequest, u):
    verify_method = verifyPatch(request)
    if verify_method:
        return verify_method
    data = load_data(request)
    new_password = data.get("new_password")
    if not new_password:
        return JsonResponse({"messege": "Password is empty"}, status=status.HTTP_406_NOT_ACCEPTABLE)
    try:
        await sync_to_async(_change_password_sync)(u, new_password)
        return JsonResponse({"messege": f"Password is changed to {new_password}"}, status=status.HTTP_200_OK)
    except Http404 as e:
        return JsonResponse({"messege": f"{e}"})


# ==================== view_employee ====================
# View individual employee profile by username (Admin only).
# URL: {{baseurl}}/accounts/admin/viewEmployee/<username>/
# Method: GET
def _view_employee_sync(username):
    """Sync helper: DB operations with transaction.atomic."""
    user = get_object_or_404(User, username=username)
    profile = Profile.objects.prefetch_related("functions").filter(Employee_id=user).first()
    if profile:
        with transaction.atomic():
            functions = [f.function for f in profile.functions.all()]
        return [{
            "Employee_id": profile.Employee_id_id,
            "Email_id": profile.Email_id,
            "Designation": profile.Designation.designation if profile.Designation else None,
            "Date_of_birth": profile.Date_of_birth,
            "Date_of_join": profile.Date_of_join,
            "Branch": profile.Branch.branch_name if profile.Branch else None,
            "Name": profile.Name,
            "Photo_link": profile.Photo_link if profile.Photo_link else None,
            "Role": profile.Role.role_name if profile.Role else None,
            "Functions": functions,
        }]
    return [{}]


@admin_required
async def view_employee(request: HttpRequest, u):
    try:
        # print("view employee not from cache")
        profile_data = await sync_to_async(_view_employee_sync)(u)
        return JsonResponse(profile_data, safe=False)
    except Http404:
        return JsonResponse({"Message": "User not found.Incorrect username"}, status=status.HTTP_404_NOT_FOUND)


# ==================== delete_user_profile ====================
# Delete employee from all records (Admin only).
# URL: {{baseurl}}/accounts/admin/deleteEmployee/<username>/
# Method: DELETE
def _delete_user_sync(username):
    """Sync helper: DB delete operation."""
    user = get_object_or_404(User, username=username)
    user.delete()


@admin_required
@csrf_exempt
async def delete_user_profile(request: HttpRequest, u):
    if request.method != 'DELETE':
        return JsonResponse({"message": "Request method must be 'DELETE'"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        await sync_to_async(_delete_user_sync)(u)
        return JsonResponse({"message": "user deleted successfully"})
    except Http404:
        return JsonResponse({"Message": "User not found.Incorrect username"}, status=status.HTTP_404_NOT_FOUND)


# ==================== get_teamLeads ====================
# Fetch team leads for dropdown (filtered by Role query param).
# URL: {{baseurl}}/accounts/getTeamleads/
# Method: GET
def _get_teamleads_sync(query_role):
    """Sync helper: DB query for team leads by role."""
    allowed_roles = ["Employee", "Intern"]
    if query_role in allowed_roles:
        role = _get_role_object_sync(role="TeamLead")
        teamleads = Profile.objects.filter(Role=role).order_by("Name")
        return [{"Name": tl.Name, "Employee_id": tl.Employee_id.username} for tl in teamleads]
    return [{}]


@login_required
async def get_teamLeads(request: HttpRequest):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    try:
        # print("get team leads not from cache")
        query_role = request.GET.get("Role")
        data = await sync_to_async(_get_teamleads_sync)(query_role)
        return JsonResponse(list(data), safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_404_NOT_FOUND)


# ==================== update_photo ====================
# Update employee photo (Admin only).
# URL: {{baseurl}}/accounts/admin/changePhoto/<username>/
# Method: POST
def _update_photo_sync(request: HttpRequest, username: str):
    """Sync helper: verify, DB and file operations. Returns HttpResponse."""
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    try:
        user_obj = get_object_or_404(User, username=username)
        user_profile = _get_user_profile_object_sync(user_obj)
        files = request.FILES
        if not files:
            return JsonResponse({"messege": "upload file is missing"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        photo_link = files.get("Photo_link")
        old_photo = user_profile.Photo_link
        if old_photo and photo_link:
            old_photo.delete(save=True)
        user_profile.Photo_link = photo_link
        user_profile.save(force_update=True)
        return JsonResponse({"messege": f"{user_profile.Name}'s Photo updated successfully"}, status=status.HTTP_205_RESET_CONTENT)
    except Http404 as e:
        return JsonResponse({"messege": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return JsonResponse({"messege": str(e)}, status=status.HTTP_304_NOT_MODIFIED)

@csrf_exempt
@admin_required
async def update_photo(request: HttpRequest, username: str):
    # print("hello world")
    return await sync_to_async(_update_photo_sync)(request, username)


# ==================== FetchImage ====================
# Fetch employee photo (Admin only). Response body is the image if file exists, else JSON {"image": null}.
# Opening the URL in a browser displays the image directly.
# URL: {{baseurl}}/accounts/admin/FetchPhoto/<username>/
# Method: GET
def _fetch_image_sync(username: str):
    """Return (path, content_type) if image exists in media folder, else None. Raises Http404 if user missing."""
    user = get_object_or_404(User, username=username)
    profile = _get_user_profile_object_sync(user)
    if not profile or not profile.Photo_link:
        return None
    if not profile.Photo_link.storage.exists(profile.Photo_link.name):
        return None
    path = profile.Photo_link.path
    content_type = mimetypes.guess_type(path)[0] or "image/jpeg"
    return (path, content_type)


def _open_image_response_sync(path: str, content_type: str):
    """Open image file and return FileResponse so the image is in the response body."""
    return FileResponse(open(path, "rb"), content_type=content_type)


@admin_required
async def FetchImage(request: HttpRequest, username: str):
    verify_method = verifyGet(request)
    if verify_method:
        return verify_method
    try:
        result = await sync_to_async(_fetch_image_sync)(username)
        if result is None:
            return JsonResponse({"image": None})
        path, content_type = result
        return await sync_to_async(_open_image_response_sync)(path, content_type)
    except Http404:
        return JsonResponse({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)


# ==================== updateUsername ====================
# Update username for a user.
# URL: {{baseurl}}/accounts/updateUsername/<username>/
# Method: POST
def _update_username_sync(username, new_username):
    """Sync helper: DB update for username."""
    User.objects.filter(username=username).update(username=new_username)


@csrf_exempt
async def updateUsername(request: HttpRequest, username: str):
    verify_method = verifyPost(request)
    if verify_method:
        return verify_method
    new_u = request.POST.get("new_username")
    try:
        await sync_to_async(_update_username_sync)(username, new_u)
        return HttpResponse("username updated")
    except Exception as e:
        return HttpResponse("Error occured")


# Filter-based views (get_branches, get_roles, get_designations, get_departments_and_functions)
# are imported from .filters and used directly as async views.
