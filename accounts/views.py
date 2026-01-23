from accounts.RequiredImports import *
from .models import *

    # "Appended Query" = Table.Combine({#"Changed Type",#"Changed Type"}),
    # "Removed Duplicates" = Table.Distinct(#"Appended Query", {"Column1"}),
    # "Removed Duplicates1" = Table.Distinct(#"Removed Duplicates", {"Column1"})
# in
# "Removed Duplicates1"

# # # # # #  baseurl="http://localhost:8000" # # # # # # # # # # # # 
from datetime import date

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
    not_required_field=["Branch","Designation","Department","Teamlead","Function"]
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
                # foreign key references to Branch and Designation in the table Profile
                # foreign key reference to Role in the table Profile
            except Http404 as e:
                print(e)
                return  JsonResponse({"messege":f"{e}"})
            except Exception as e:
                print(e)
                return JsonResponse({"messege":f"{e}"})
            else:
                Profile.objects.create(**profile_values)
                return JsonResponse({"messege":"user profile created successfully"},status=status.HTTP_200_OK)
            
#Get a view of all employees/users present in the record. 
@login_required
def get_all_employees(request: HttpRequest):
        admin_role=get_role_object(role="Admin")
        profile_data=Profile.objects.exclude(Role=admin_role).select_related("Role","Designation","Branch","Department")
        users_data=[]
        for pd in profile_data:
            role=pd.Role.role_name
            if  role != "MD":
                user={"Employee_id":pd.Employee_id.username,
                    "Name":pd.Name,
                    "Role":pd.Role.role_name,
                    "Branch":pd.Branch.branch_name,
                    "Designation":pd.Designation.designation,
                    "Date_of_birth":pd.Date_of_birth,
                    "Date_of_join":pd.Date_of_join,
                    "Number_of_days_from_joining":completed_years_and_days(start_date=pd.Date_of_join),
                    "Email_id":pd.Email_id,
                    "Photo_link":pd.Photo_link.url,
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
                    "Photo_link":pd.Photo_link.url,
                    "teamlead":None,
                    "function":None}
                users_data.append(user)
                
        return  JsonResponse(users_data,safe=False)

# get the session data of a logged_in user.
@login_required
def get_session_data(request: HttpRequest):
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

#Login view.    
@csrf_exempt
def user_login(request:HttpRequest):
    # request content type is in json format
    verify_method=verifyPost(request)
    if not verify_method:
        if request.content_type=="application/json":
            data=json.loads(request.body)
            u= data.get('username')
            p = data.get('password')
    # for other types of body content 
        else:
            data=request.POST
            u=data.get('username')
            p=data.get('password')
    else: 
        return verify_method
    try:
        if not u or not p:
            return JsonResponse({"message":"username or password is missing"},status=status.HTTP_204_NO_CONTENT)
        else:
            # print(u,p)
            user= authenticate(request,username=u,password=p)
            if not user:
                    return  JsonResponse({"messege":"Incorrect userID/Password,Try again"},status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                login(request,user)
                user_role=get_user_role(user)
                if isinstance(user_role,str):
                    return  JsonResponse({"messege":"You are logged in","username":f"{user.username}","Role":user_role},status=status.HTTP_200_OK)
                elif user.is_superuser:
                    return  JsonResponse({"messege":"You are logged in","username":f"{user.username}","Role":"Admin"},status=status.HTTP_200_OK)
                else:
                    return JsonResponse(user_role,status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
                    return JsonResponse({"messege":f"{e}"})

# Get logged_in users Profile data
@login_required
def employee_dashboard(request: HttpRequest):
    user_role=get_user_role(user=request.user)
    if request.user.is_superuser and user_role and user_role=="Admin":
        profile=Profile.objects.filter(Employee_id=request.user).select_related("Role").annotate(role=F("Role__role_name")).values("Employee_id","Email_id","Date_of_birth","Date_of_join","Name","Photo_link","role")
    elif request.user.is_superuser and user_role and user_role=="MD":
        profile=Profile.objects.filter(Employee_id=request.user).annotate(role=F("Role__role_name")).select_related("Role").values("Employee_id","Email_id","Date_of_birth","Date_of_join","Name","Photo_link","role")
    else:
        profile=Profile.objects.filter(Employee_id=request.user).select_related("Department","Branch","Designation","Role").annotate(department=F("Department__dept_name"),
                role=F("Role__role_name"),designation=F("Designation__designation"),branch=F("Branch__branch_name")).values("Employee_id",
                    "Email_id","designation","Date_of_birth","Date_of_join","branch","Name","Photo_link","role","department")
        
    return  JsonResponse(list(profile),safe=False)

# Logout the logged_in user and delete the sessions.
@login_required
def user_logout(request: HttpRequest):
    user_id=request.user.username
    logout(request)
    request.session.flush()
    return  JsonResponse({"messege":f"Logout successfully {user_id}"},status=status.HTTP_200_OK)

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
    else:
        fields=['Name','Role','Email_id','Designation','Date_of_join','Date_of_birth','Branch',"Department","Teamlead","Function"]
        not_required_fields=["Designation","Branch","Department","Teamlead","Function"]
        profile_values={}
        try:
            data=request.POST
            files=request.FILES
            for i in fields:
                if i!= "Photo_link":
                    field_value=data.get(i)
                else:
                    field_value=files.get(i)
                
                if not field_value and i not in not_required_fields:
                    print("error1")
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
        else:
            photo= profile_values.pop("Photo_link",None)
            if profile.Photo_link and photo:
                profile.Photo_link.delete(save=True)
                profile.Photo_link=photo
                profile.save(force_update=True)
            try:
                    Profile.objects.filter(Employee_id=user).update(**profile_values)
            except Http404 as e:
                print(e)
                return  JsonResponse({"messege":f"{e}"},status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                    print(e)
                    return  JsonResponse({"messege":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
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


