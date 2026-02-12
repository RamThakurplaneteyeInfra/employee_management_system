from ems.verify_methods import *
from .models import *
from .snippet import admin_required
from .filters import *

# # # # # #  baseurl="http://localhost:8000" # # # # # # # # # # # # 
# a get method for home page
# endpoint-{{baseurl}}/
def home(request: HttpRequest):
    # return JsonResponse({"messege":"You are at Accounts section"})
    # return redirect("/accounts/login")
    # return redirect("login")
    return HttpResponse(status=204)

@csrf_exempt
@admin_required
def create_employee_login(request: HttpRequest):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    fields=['Employee_id','password','Name','Role','Email_id','Designation','Date_of_join','Date_of_birth','Branch','Photo_link',"Department","Teamlead","Function"]
    not_required_field=["Branch","Designation","Department","Teamlead","Function","Photo_link"]
    login_values={}
    profile_values={}
    try:
                data=request.POST
                files=request.FILES
                for i in fields:
                    if i!="Photo_link":
                        field_value=data.get(i)
                    else:
                        field_value=files.get(i)
                    
                    if not field_value and i not in not_required_field:
                        print("error1")
                        return JsonResponse({"messege":f"{i} is required"},status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif i=="Teamlead" and field_value:
                        teamlead_user_obj=get_object_or_404(User,username=field_value)
                        profile_values["Teamlead"]=teamlead_user_obj
                    elif i in not_required_field and not field_value:
                        ...
                    elif i=='Employee_id':
                        login_values["username"]=str(field_value)
                        profile_values["Employee_id"]=field_value
                    elif i=='password':
                        login_values[i]=field_value
                    elif i == 'Email_id':
                        login_values["email"]=field_value
                        profile_values[i]=field_value
                    else:
                        profile_values[i]=field_value
    except Http404 as e:
        print(e)
        return  JsonResponse({"messege":f"{e}"})
    except Exception as e:
        print("error3")
        return JsonResponse({"messege":f"{e}"},status=status.HTTP_406_NOT_ACCEPTABLE)
    except DatabaseError as e:
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        try:
            check_user=get_user_object(username=login_values["username"])
            if not isinstance(check_user,User):
                user = User(**login_values)
                user.set_password(login_values["password"])
                user.save()
            else:
                user=check_user
        except Exception as e:
            print("error4")
            return JsonResponse({"messege":f"{e}"},status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                profile_values["Employee_id"]=user
                if profile_values["Role"] not in ["MD","Admin"]:
                        get_branch=get_object_or_404(Branch,branch_name=profile_values["Branch"])
                        get_designation=get_object_or_404(Designation,designation=profile_values["Designation"])                    
                        get_department=get_object_or_404(Departments,dept_name=profile_values["Department"])
                        get_function=get_object_or_404(Functions,function=profile_values["Function"])
                        profile_values["Department"]=get_department
                        profile_values["Branch"]=get_branch
                        profile_values["Designation"]=get_designation
                        profile_values["Function"]=get_function
                get_role=get_object_or_404(Roles,role_name=profile_values["Role"])
                profile_values["Role"]=get_role
                Profile.objects.create(**profile_values)
            except Http404 as e:
                print(e)
                return  JsonResponse({"messege":f"{e}"})
            except Exception as e:
                print(e)
                return JsonResponse({"messege":f"{e}"})
            else:
                return JsonResponse({"messege":"user profile created successfully"},status=status.HTTP_200_OK)
            
#Get a view of all employees/users present in the record. 
@login_required
def get_all_employees(request: HttpRequest):
    try:
        admin_role=get_role_object(role="Admin")
        profile_data=Profile.objects.all().select_related("Role","Designation","Branch","Department","Function","Employee_id")
        users_data=[]
        for pd in profile_data:
            role=pd.Role.role_name
            if  role not in ["MD","Admin"]:
                user={"Employee_id":pd.Employee_id.username,
                    "Name":pd.Name,
                    "Role":pd.Role.role_name,
                    "Branch":pd.Branch.branch_name,
                    "Designation":pd.Designation.designation,
                    "Date_of_birth":pd.Date_of_birth,
                    "Date_of_join":pd.Date_of_join,
                    "Number_of_days_from_joining":completed_years_and_days(start_date=pd.Date_of_join),
                    "Email_id":pd.Email_id,
                    "Photo_link":get_photo_url(pd),
                    "department":pd.Department.dept_name,
                    "Teamleader":get_users_Name(pd.Teamlead),
                    "function":pd.Function.function}
                users_data.append(user)
            else:
                user={"Employee_id":pd.Employee_id.username,
                    "Name":pd.Name,
                    "Role":pd.Role.role_name,
                    "Branch":None,
                    "Designation":None,
                    "Date_of_birth":pd.Date_of_birth,
                    "Date_of_join":pd.Date_of_join,
                    "Number_of_days_from_joining":completed_years_and_days(start_date=pd.Date_of_join),
                    "Email_id":pd.Email_id,
                    "Photo_link":get_photo_url(pd),
                    "teamlead":None,
                    "function":None}
                users_data.append(user)
    except DatabaseError as e:
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:                
        return  JsonResponse(users_data,safe=False,status=status.HTTP_200_OK)

# get the session data of a logged_in user.
@login_required
def get_session_data(request: HttpRequest):
    try:
        verify_method=verifyGet(request)
        if verify_method:
            return verify_method
        if not request.user:
            return JsonResponse({"messege":"login credentials required"},status=status.HTTP_200_OK)
        else:
            session_data={}
            session_data["expiray-age"]=request.session.get_expiry_age()
            session_data["expiray-date"]=request.session.get_expiry_date()
            session_data["accessed"]=request.session.accessed
            session_data["is_empty"]=request.session.is_empty()
            return JsonResponse(session_data)
    except DatabaseError as e:
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#Login view.    
@csrf_exempt
def user_login(request:HttpRequest):
    # request content type is in json format
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    data=load_data(request)
    u=data.get("username")
    p=data.get("password")
    # for other types of body content    
    try:
        if not u or not p:
            return JsonResponse({"message":"username or password is missing"},status=status.HTTP_204_NO_CONTENT)
    
        user= authenticate(request,username=u,password=p)
        if not user:
                return  JsonResponse({"messege":"Incorrect userID/Password,Try again"},status=status.HTTP_400_BAD_REQUEST)
        else:
            login(request,user)
            user_role=get_user_role(user)
            if user_role:
                return  JsonResponse({"messege":"You are logged in","username":f"{user.username}","Role":user_role},status=status.HTTP_200_OK)
            return JsonResponse({"messege":"You are logged in","username":f"{user.username}","Role":None},status=status.HTTP_206_PARTIAL_CONTENT)
    except Exception as e:
                    return JsonResponse({"messege":f"{e}"},status=status.HTTP_403_FORBIDDEN)
    except DatabaseError as e:
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get logged_in users Profile data
@login_required
def employee_dashboard(request: HttpRequest):
    try:
        user_role=get_user_role(user=request.user)
        if request.user.is_superuser and user_role and user_role=="Admin":
            profile=Profile.objects.select_related("Role").filter(Employee_id=request.user).annotate(role=F("Role__role_name")).values("Employee_id","Email_id","Date_of_birth","Date_of_join","Name","Photo_link","role")
        elif request.user.is_superuser and user_role and user_role=="MD":
            profile=Profile.objects.select_related("Role").filter(Employee_id=request.user).annotate(role=F("Role__role_name")).values("Employee_id","Email_id","Date_of_birth","Date_of_join","Name","Photo_link","role")
        else:
            profile=Profile.objects.select_related("Department","Branch","Designation","Role","Function").filter(Employee_id=request.user).annotate(department=F("Department__dept_name"),
                role=F("Role__role_name"),designation=F("Designation__designation"),branch=F("Branch__branch_name"),function_name=F("Function__function")).values("Employee_id",
                    "Email_id","designation","Date_of_birth","Date_of_join","branch","Name","Photo_link","role","department","function_name")
            # profile=Profile.objects.filter(Employee_id=request.user).values()
    except DatabaseError as e:
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return  JsonResponse(list(profile),safe=False)

# Logout the logged_in user and delete the sessions.
@login_required
def user_logout(request: HttpRequest):
    try:
        user_id=request.user.username
        logout(request)
        request.session.flush()
        return  JsonResponse({"messege":f"Logout successfully {user_id}"},status=status.HTTP_200_OK)
    except DatabaseError as e:
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#Update particular user profile using his/her username.
@csrf_exempt
@admin_required
def update_profile(request: HttpRequest,username):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    try:
        user=get_object_or_404(User,username=username)
        profile=Profile.objects.get(Employee_id=user)
    except Http404 as e:
        print(e)
        return JsonResponse({"messege":"User Not Found. Incorrect Username Passed in the URL"},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(e)
        return  JsonResponse({"messege":"User Profile is missing."},status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        fields=['Name','Role','Email_id','Designation','Date_of_join','Date_of_birth','Branch',"Department","Teamlead","Function"]
        not_required_fields=["Designation","Branch","Department","Teamlead","Function"]
        profile_values={}
        try:
            data=request.POST
            # return HttpResponse(data.items())
            for i in fields:
                field_value=data.get(i)
                if not field_value and i not in not_required_fields:
                    # print("error1")
                    return JsonResponse({"messege":f"{i} is empty"},status=status.HTTP_406_NOT_ACCEPTABLE)
                elif i in not_required_fields and not field_value:
                    ...
                elif i == 'Email_id':
                    setattr(user,'email',field_value)
                    user.save()
                    profile_values[i]=field_value
                elif i=="Teamlead" and field_value:
                    get_teamlead_obj=get_object_or_404(User,username=field_value)
                    profile_values[i]=get_teamlead_obj
                elif i=="Branch" and field_value:
                        get_branch=get_object_or_404(Branch,branch_name=field_value)
                        profile_values[i]=get_branch
                elif i=="Department" and field_value:
                        get_department=get_object_or_404(Departments,dept_name=field_value)
                        profile_values[i]=get_department
                elif i=="Designation" and field_value:
                        get_designation=get_object_or_404(Designation,designation=field_value)                  
                        profile_values[i]=get_designation
                elif i=="Function" and field_value:
                        get_function=get_object_or_404(Functions,function=field_value)
                        profile_values[i]=get_function
                elif i=="Role" and field_value:
                    get_role=get_object_or_404(Roles,role_name=field_value)
                    profile_values[i]=get_role
                else:
                    profile_values[i]=field_value
            # print(profile_values)
        except Http404 as e:
                print(e)
                return  JsonResponse({"messege":f"{e}"})
        except Exception as e:
            print(e)
            return  JsonResponse({"messege":f"{e}"},status=status.HTTP_406_NOT_ACCEPTABLE)
        except DatabaseError as e:
            return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            try:
                    Profile.objects.filter(Employee_id=user).update(**profile_values)
            # except Http404 as e:
            #     print(e)
            #     return  JsonResponse({"messege":f"{e}"},status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                    print(e)
                    return  JsonResponse({"messege":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
            except DatabaseError as e:
                return  JsonResponse({"message":f"{e}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return  JsonResponse({"messege":"user details update successfully"},status=status.HTTP_205_RESET_CONTENT)

@csrf_exempt
@login_required
def changePassword(request: HttpRequest,u):
    verify_method=verifyPatch(request)
    if verify_method:
        return verify_method
    data=load_data(request)
    new_password=data.get("new_password")
    if not new_password:
        return JsonResponse({"messege":"Password is empty"},status=status.HTTP_406_NOT_ACCEPTABLE)
    try:
        user=get_object_or_404(User,username=u)
    except Http404 as e:
        print(e)
        return  JsonResponse({"messege":f"{e}"})
    else:
        user.password=new_password
        user.set_password(new_password)
        user.save(force_update=True)
        return JsonResponse({"messege":f"Password is changed to {new_password}"},status=status.HTTP_200_OK)

# View Individual Employee Profile. 
@admin_required
def view_employee(request: HttpRequest,u):
    try:
        user=get_object_or_404(User,username=u)
        profile=Profile.objects.filter(Employee_id=user)
    except Http404:
        return JsonResponse({"Message":"User not found.Incorrect username"},status=status.HTTP_404_NOT_FOUND)
    else:
        if profile:
            profile_data=profile.values("Employee_id","Email_id","Designation","Date_of_birth","Date_of_join","Branch","Name","Photo_link","Role")
            return JsonResponse(list(profile_data),safe=False)
        return JsonResponse([{}],safe=False)
    
# Delete Employee from all Records.
@admin_required
@csrf_exempt
def delete_user_profile(request: HttpRequest,u):
    if request.method=='DELETE':
        try:
            user=get_object_or_404(User,username=u)
        except Http404 as e:
            print(e)
            return JsonResponse({"Message":"User not found.Incorrect username"},status=status.HTTP_404_NOT_FOUND)
        else:
            user.delete()
            return JsonResponse({"message":"user deleted successfully"})
    else:
            return JsonResponse({"message":"Request method must be 'DELETE'"},status=status.HTTP_400_BAD_REQUEST)

@login_required
def get_teamLeads(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    try:
        allowed_roles=["Employee","Intern"]
        data=request.GET
        query_role=data.get("Role")
        if query_role in allowed_roles:
            role=get_role_object(role="TeamLead")
            teamleads=Profile.objects.filter(Role=role).order_by("Name")
            data=[{"Name":tl.Name,
            "Employee_id":tl.Employee_id.username} 
            for tl in teamleads]
        else:
            data=[{}]
    except Exception as e:
        print(e)
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(list(data),safe=False,status=status.HTTP_200_OK)

@csrf_exempt
@admin_required
def update_photo(request: HttpRequest,username:str):
    verify_method=verifyPost(request)
    if verify_method:
        verify_method
    try:
        user_obj=get_object_or_404(User,username=username)
        user_profile=get_user_profile_object(user=user_obj)
        data=request.FILES
        users_name=user_profile.Name
        if not data:
            return JsonResponse({"messege":f"upload file is missing"},status=status.HTTP_406_NOT_ACCEPTABLE)
        photo_link=data.get("Photo_link")
        old_photo=user_profile.Photo_link
        if old_photo and photo_link:
            old_photo.delete(save=True)
            user_profile.Photo_link=photo_link
            user_profile.save(force_update=True)
        else:
            user_profile.Photo_link=photo_link
            user_profile.save(force_update=True)
    except Http404 as e:
        print(e)
        return  JsonResponse({"messege":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(e)
        return  JsonResponse({"messege":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
    else:
        return JsonResponse({"messege":f"{users_name}'s Photo updated successfully"},status=status.HTTP_205_RESET_CONTENT)

@admin_required
def FetchImage(request: HttpRequest,username:str):
    # baseurl="http://localhost:8000/"
    # try:
    #     user_obj=get_object_or_404(User,username=username)
    #     user_profile=get_user_profile_object(user_obj)
    #     photo_link=user_profile.Photo_link
    #     if photo_link:
    #         response=requests.get(url=f"{baseurl}media/{photo_link}")
    #         response.headers["Content-Type"]="image/png"
    #         return response
    #     return JsonResponse({"message":"File not found"},status=status.HTTP_404_NOT_FOUND)
    # except Http404 as e:
    #     print(e)
    #     return  JsonResponse({"messege":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    # except Exception as e:
    #     print(e)
    #     return  JsonResponse({"messege":f"{e}"},status=status.HTTP_501_NOT_IMPLEMENTED)
    return HttpResponse("None")
    ...
    
@csrf_exempt
def updateUsername(request: HttpRequest,username:str):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    
    data=request.POST
    new_u=data.get("new_username")
    try:
        user_obj=User.objects.filter(username=username)
    except Exception as e:
        return HttpResponse("Error occured")
    else:
        user_obj.update(username=new_u)
        # user_obj.save()
        return HttpResponse("username updated")
    
    