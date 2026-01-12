from accounts.RequiredImports import *

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
    fields=['Employee_id','password','Name','Role','Email_id','Designation','Date_of_join','Date_of_birth','Branch','Photo_link']
    login_values={}
    profile_values={}
    try:
        if request.method == "POST":
                data=request.POST
                files=request.FILES
                for i in fields:
                    if i!="Photo_link":
                        field_value=data.get(i)
                    else:
                        field_value=files.get(i)
                    
                    if not field_value and i!="Designation" and i!="Branch":
                        print("error1")
                        return JsonResponse({"messege":f"{i} is required"},status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif i=="Designation" and not data.get(i):
                        ...
                    elif i=="Branch" and not data.get(i):
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
        else:
            # print("error2")
            return JsonResponse({"messege":"Request method must be 'POST'"},status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print("error3")
        return JsonResponse({"messege":f"{e}"},status=status.HTTP_406_NOT_ACCEPTABLE)
    else:
        try:
            # profile_values.update(login_values)
            print(profile_values)
            check_user=User.objects.filter(username=login_values["username"]).first()
            if not check_user:
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
                # foreign key references to Branch and Designation in the table Profile
                if data.get("Role") != "MD":
                    get_branch=get_branch_object(branch=profile_values["Branch"])
                    if isinstance(get_branch,Branch):
                        profile_values["Branch"]=get_branch
                    else:
                        print(get_branch)
                        return JsonResponse(get_branch,safe=False)
                
                    get_designation=get_designation_object(designation=profile_values["Designation"])
                    if isinstance(get_designation,Designation):
                        profile_values["Designation"]=get_designation
                    else:
                        print(get_designation)
                        return JsonResponse(get_designation,safe=False)
                    
                # foreign key reference to Role in the table Profile
                get_role=get_role_object(role=profile_values["Role"])
                if isinstance(get_role,Roles):
                    profile_values["Role"]=get_role
                else:
                    print(get_role)
                    return JsonResponse(get_role,safe=False)
                
                user_profile=Profile.objects.create(**profile_values)
                user_profile.save()
                return JsonResponse({"messege":"Employee Profile Created successfully"},status=status.HTTP_201_CREATED)
            except Exception as e:
                print(e)
                return JsonResponse({"messege":f"{e}"})
            
#Get a view of all employees/users present in the record. 
@login_required
def get_all_employees(request: HttpRequest):
        role=get_user_role(user=request.user)
        profile_data=Profile.objects.filter().select_related("Role","Designation","Branch")
        profile_data=[{"Employee_id":pd.Employee_id.username,
                      "Name":pd.Name,
                      "Role":pd.Role.role_name,
                      "Branch":pd.Branch.branch_name,
                      "Designation":pd.Designation.designation,
                      "Date_of_birth":pd.Date_of_birth,
                      "Date_of_join":pd.Date_of_join,
                      "Email_id":pd.Email_id,
                      "Photo_link":pd.Photo_link.url
                        } for pd in profile_data if pd.Role.role_name!="MD"]
        return  JsonResponse(profile_data,safe=False)

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
            print(u,p)
            user= authenticate(request,username=u,password=p)
            if not user:
                    return  JsonResponse({"messege":"Incorrect userID/Password,Try again"},status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                    login(request,user)
                    if not user.is_superuser:
                        user_role=get_user_role(user)
                        if isinstance(user_role,str):
                            return  JsonResponse({"messege":"You are logged in","username":f"{request.user.username}","Role":user_role},status=status.HTTP_200_OK)
                            # return JsonResponse({"message":"login successfull"})
                        else:
                            return JsonResponse(user_role,status=status.HTTP_404_NOT_FOUND)
                    else:
                        return  JsonResponse({"messege":"You are logged in","username":f"{request.user.username}","Role":"Admin"},status=status.HTTP_200_OK)
    except Exception as e:
                return JsonResponse({"messege":f"{e}"})
# Get logged_in users Profile data
@login_required
def employee_dashboard(request: HttpRequest):
    if request.user.is_superuser:
        return  JsonResponse({"messege":"This is a Admin information dashboard","username":f"{request.user.username}","Role":"Admin"})
    else:
        profile=Profile.objects.filter(Employee_id=request.user).values("Employee_id","Email_id","Designation","Date_of_birth","Date_of_join","Branch","Name","Photo_link","Role")
        
    return  JsonResponse(list(profile),safe=False)

# Logout the logged_in user and delete the sessions.
@login_required
def user_logout(request: HttpRequest):
    logout(request)
    request.session.flush()
    return  JsonResponse({"messege":"Logout successfully"},status=status.HTTP_200_OK)

#Update particular user profile using his/her username.
@csrf_exempt
@admin_required
def update_profile(request: HttpRequest,username):
    if request.method in ['POST']:
        fields=['password','Name','Role','Email_id','Designation','Date_of_join','Date_of_birth','Branch','Photo_link']
        login_values={}
        profile_values={}
        try:
                data=request.POST
                files=request.FILES
                for i in fields:
                    if i!= "Photo_link":
                        field_value=data.get(i)
                    else:
                        field_value=files.get(i)
                    if not field_value and i!="Designation" and i!="Branch":
                        return JsonResponse({"messege":f"{i} is empty"},status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif i=="Designation" and not data.get(i):
                        ...
                    elif i=="Branch" and not data.get(i):
                        ...
                    elif i=='password':
                        login_values[i]=field_value
                    elif i == 'Email_id':
                        login_values["email"]=field_value
                        profile_values[i]=field_value
                    else:
                        profile_values[i]=field_value
        except Exception as e:
            return  JsonResponse({"messege":f"{e}"},status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            try:
                user=User.objects.get(username=username)
            except Exception as e:
                return  JsonResponse({"messege":"User Not Found. Incorrect Username Passed in the URL"},status=status.HTTP_404_NOT_FOUND) 
            else:
                profile=Profile.objects.get(Employee_id=user)
        try:    
            setattr(user,'password',login_values['password'])
            setattr(user,'email',login_values['email'])
            user.set_password(login_values['password'])
            user.save()
            if profile.Photo_link:
                profile.Photo_link.delete(save=True)
        except Exception as e:
            return  JsonResponse({"messege":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
        else:
            if data.get("Branch") and data.get("Designation"):
                    get_branch=get_branch_object(branch=profile_values["Branch"])
                    if isinstance(get_branch,Branch):
                        profile_values["Branch"]=get_branch
                    else:
                        return JsonResponse(get_branch,safe=False)
                
                    get_designation=get_designation_object(designation=profile_values["Designation"])
                    if isinstance(get_designation,Designation):
                        profile_values["Designation"]=get_designation
                    else:
                        return JsonResponse(get_designation,safe=False)
                    
            get_role=get_role_object(role=profile_values["Role"])
            if isinstance(get_role,Roles):
                profile_values["Role"]=get_role
            else:
                return JsonResponse(get_role,safe=False)
            # profile_values["Branch"]=get_branch_object(branch=profile_values["Branch"])
            # profile_values["Designation"]=get_designation_object(designation=profile_values["Designation"])
            # profile_values["Role"]=get_role_object(role=profile_values["Role"])  
            updated_profile=Profile.objects.filter(Employee_id=user).update(**profile_values)
            return  JsonResponse({"messege":"user details update successfully"},status=status.HTTP_205_RESET_CONTENT)
    else:
        return  JsonResponse({"messege":"Request method must be 'POST'"},status=status.HTTP_400_BAD_REQUEST)
            # ...
# View Individual Employee Profile. 
@admin_required
def view_employee(request: HttpRequest,u):
    try:
        user=User.objects.get(username=u)
    except:
        return JsonResponse({"Message":"User not found.Incorrect username"},status=status.HTTP_404_NOT_FOUND)
    else:
        profile=get_user_profile_object(user=user).values("Employee_id","Email_id","Designation","Date_of_birth","Date_of_join","Branch","Name","Photo_link","Role")
    return JsonResponse(list(profile),safe=False)

# Delete Employee from all Records.
@admin_required
@csrf_exempt
def delete_user_profile(request: HttpRequest,u):
    if request.method=='DELETE':
        try:
            user=get_user_object(username=u)
        except:
            return JsonResponse({"Message":"User not found.Incorrect username"},status=status.HTTP_404_NOT_FOUND)
        else: 
            user.delete()
            return JsonResponse({"message":"user deleted successfully"})
    else:
            return JsonResponse({"message":"Request method must be 'DELETE'"},status=status.HTTP_400_BAD_REQUEST)