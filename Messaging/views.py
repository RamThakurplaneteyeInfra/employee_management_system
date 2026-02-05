# from accounts.filters import get_user_object, get_users_Name
# from accounts.models import Profile,User
# from .models import *
from .permissions import *
from .snippet import add_participant_to_groupMembers
from .filters import *

@csrf_exempt
@login_required
def access_or_create_conversation(request: HttpRequest):
        """Get or create conversation with a specific user"""
        verify_method=verifyPost(request)
        if verify_method:
            return verify_method
        data=load_data(request)
        print(data)
        try:
            user1=User.objects.get(username=data.get("participant"))
            user2=request.user
        except User.DoesNotExist:
            return JsonResponse(
                {"message": "Invalid User."},
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            object,is_created=IndividualChats.get_or_create_indivisual_Chat(user1=user1,user2=user2)
            print(object,is_created)
            if not is_created:
                other_user=object.get_other_participant(request.user)
                chat_details={"chat_id":object.chat_id,
                        "participant":get_users_Name(other_user),
                        "messages":{}}
                return JsonResponse(chat_details)
            else:
                messages=get_messages(request,chat_id=object.chat_id)
                return messages

# create groups here
# endpoint-
@csrf_exempt
@login_required
def create_group(request:HttpRequest):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    has_permission=has_group_create_or_add_member_permission(request.user)
    try:
        current_user_name=Profile.objects.get(Employee_id=request.user).Name
        if not current_user_name:
            return JsonResponse({"message":"You cannot create your group, untill you Complete your profile"},status=status.HTTP_304_NOT_MODIFIED)
        if has_permission:
            group_create_fields=["group_name","description","participants"]
            temp_dict={}
            data=load_data(request=request)
            for i in group_create_fields:
                if (i=="group_name" or i=="participants") and not data.get(i):
                    return JsonResponse({"message":"Participants are required"},status=status.HTTP_406_NOT_ACCEPTABLE)
                elif i=="participants":
                    temp_dict[i]=len(data.get(i))+1
                else:
                    temp_dict[i]=data.get(i)
                
            temp_dict["created_by"]=request.user
            temp_dict["group_id"]=generate_group_id()
            print(temp_dict)
            chat=GroupChats.objects.create(**temp_dict)
            chat.save()
        else:
            raise PermissionDenied("Not allowed")
    except PermissionDenied:
            return JsonResponse({"message":"you cannot create a Group. Kindly contact your TeamLead/Admin"},status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
    else:
            chat_id=getattr(chat,"group_id")
            if not chat_id:
                return JsonResponse({"Messsage":"Group not created"},status=status.HTTP_304_NOT_MODIFIED)
            else:
                    participants_data:dict=data.get("participants")
                    participants_data.update({f"{current_user_name}":request.user.username})
                    for i in participants_data:
                        user=get_user_object(username=participants_data[i])
                        if isinstance(user,User):
                            add_participant_to_groupMembers(group_chat=chat,participant=user)
                        else:
                            return JsonResponse(user,status=status.HTTP_304_NOT_MODIFIED)
                        
            return JsonResponse({"Messsage":"Group created successfully"},status=status.HTTP_201_CREATED)

@login_required
def show_created_groups(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    # Groups=request.user.created_groups.orderby("created_at")
    groups=GroupChats.objects.filter(created_by=request.user).order_by("-created_at")
    info=[{
        "group_id":g.group_id,
        "name":g.group_name,
        "description":g.description,
        "created_at":g.created_at.strftime("%d/%m/%y-%H:%M")
    } for g in groups]
    
    return JsonResponse(info,safe=False)
    
@login_required
def api_to_get_group_members(request: HttpRequest,group_id:str):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    data=get_group_members(group_id=group_id)
    return data

@csrf_exempt
@login_required
def update_group(request: HttpRequest,group_id:str):
    verify_method=verifyPatch(request)
    if verify_method:
            return verify_method
    try:
        group_obj:GroupChats|Http404=get_object_or_404(GroupChats,group_id=group_id)
        if request.user==group_obj.created_by:
            fields=["group_name","description"]
            data=load_data(request=request)
            for i in fields:
                field_value=data.get(i)
                if not field_value:
                    return JsonResponse({"message":f"{i} is missing"},status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    setattr(group_obj,"group_name",field_value)
        else:
            raise PermissionDenied("Not Allowed")
    except Http404 as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    except PermissionDenied as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({"Messsage":"Group details updated successfully"},status=status.HTTP_201_CREATED)
    
@csrf_exempt
@login_required
def add_user(request: HttpRequest,group_id:str):
    verify_method=verifyPost(request)
    if verify_method:
        print("e")
        return verify_method
    group_obj=get_object_or_404(GroupChats,group_id=group_id)
    check_permiss=has_group_create_or_add_member_permission(request.user)
    try:
        if check_permiss:
            request_data=load_data(request)
            present_members=get_group_members(group_id=group_id)
            data=json.loads(present_members.content.decode('utf-8'))
            for i in data:
                if i.get("participant")==request_data.get("participant"):
                    return JsonResponse({"Message":"user Already Exists"},status=status.HTTP_302_FOUND)                   
                elif i.get("message"):
                    return present_members
            
            user=get_user_object(username=request_data.get("participant"))
            if isinstance(user,User):
                add_participant_to_groupMembers(group_chat=group_obj,participant=user)
                # setattr(group_obj,"participants",)
                # print(group_obj.participants)
                group_obj.participants+=1
                group_obj.save()
            else:
                return JsonResponse(user,status=status.HTTP_304_NOT_MODIFIED)
        else:
            raise PermissionDenied("Not allowed")
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_403_FORBIDDEN)
    except PermissionDenied as error:
            print(error)
            return JsonResponse({"message":"you cannot create a Group. Kindly contact your TeamLead/Admin"},status=status.HTTP_403_FORBIDDEN)
    else:
        return JsonResponse({"Message":"user added Successfully"},status=status.HTTP_201_CREATED)
    
# endpoint-{{baseurl}}/messaging/deleteUser/{group_id}/{user_id}/
@csrf_exempt
@login_required
def delete_user(request: HttpRequest,group_id:str,user_id:str):
    verify_method=verifyDelete(request)
    if verify_method:
        return verify_method
    group_obj=get_object_or_404(GroupChats,group_id=group_id)
    check_permiss=has_group_create_or_add_member_permission(request.user)
    try:
        if check_permiss:
            present_members=get_group_members(group_id=group_id)
            data=json.loads(present_members.content.decode('utf-8'))
            can_Delete=False
            for i in data:
                if  user_id==request.user.username:
                    return JsonResponse({"Message":"self deletion is prohibited"},status=status.HTTP_404_NOT_FOUND) 
                elif group_obj.created_by.username==user_id:
                    return JsonResponse({"Message":"Cannot delete the Group Admin"},status=status.HTTP_404_NOT_FOUND)
                elif i["participant"]==user_id:
                    can_Delete=True
                    
            if can_Delete:
                user=get_object_or_404(User,username=user_id)
                group_member_obj=GroupMembers.objects.filter(groupchat=group_obj,participant=user).first()
                if group_obj.participants>2:
                # group_obj.participants=group_obj.participants-1
                    group_member_obj.delete()
                    group_obj.participants-=1
                    group_obj.save()
                    message={"Message":"user deleted Successfully"}
                elif not group_member_obj:
                    message={"Message":"selected user is not a group member"}
                else:
                    raise Http404("there should be at least 2 members in the group")
        else:
            raise PermissionDenied("Not allowed")
    except Http404 as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse(message,status=status.HTTP_200_OK)

@csrf_exempt
@login_required
def delete_group(request: HttpRequest,group_id:str):
    verify_method=verifyDelete(request)
    if verify_method:
        return verify_method
    try:
        group_obj=get_group_object(group_id=group_id)
        if isinstance(group_obj,GroupChats):
                check_delete_permiss=can_Delete_group(group=group_obj,user=request.user)
                if check_delete_permiss:
                    group_obj.delete()
                    return JsonResponse({"message":"group deleted successfully"},status=status.HTTP_202_ACCEPTED)
                else:
                    raise PermissionDenied("Not allowed")
        return group_obj
    except PermissionDenied:
        return JsonResponse({"message":"you cannot delete a Group."},status=status.HTTP_403_FORBIDDEN)
    
# The above code is a Python Django application that handles sending and retrieving messages in a chat
# application. Here is a breakdown of the main functionalities:
@csrf_exempt
@login_required
def post_message(request,chat_id:str):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    sender=request.user
    data=load_data(request)
    print(data)
    message=data.get("Message")
    if not message:
        return JsonResponse({"message":"Message is empty"},status=status.HTTP_204_NO_CONTENT)
    is_group=check_group_or_chat(chat_id=chat_id)
    if is_group:
        try:
            chat_obj=get_group_object(group_id=chat_id)
            if not isinstance(chat_obj,GroupChats):
                raise PermissionDenied("Invalid Group_id")
        except:
            return chat_obj
        else:
            GroupMessages.objects.create(group=chat_obj,sender=sender,content=message).save()
            chat_obj.save()
    else:
        try:
            chat_obj=get_individual_chat_object(chat_id=chat_id)
            if not isinstance(chat_obj,IndividualChats):
                    raise PermissionDenied("Invalid chat_id")
        except:
            return chat_obj
        else:
            IndividualMessages.objects.create(chat=chat_obj,sender=sender,content=message).save()
            chat_obj.save()

    return JsonResponse({"message":"Message sent successfully"},status=status.HTTP_201_CREATED)
    
@login_required
def get_chats(request: HttpRequest,chat_id:str):
    request_method=verifyGet(request)
    if request_method:
        return request_method
    return get_messages(request=request,chat_id=chat_id)
        

@login_required
def load_groups_and_chats(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    groups=GroupMembers.objects.filter(participant=request.user)
    chats=IndividualChats.objects.filter(Q(participant1=request.user)|Q(participant2=request.user))
    groups_info=[{
        "group_id":g.groupchat.group_id,
        "group_name":g.groupchat.group_name,
        "description":g.groupchat.description
    } for g in groups]
    chats_info=[{
        "chat_id":c.chat_id,
        "with":get_users_Name(c.get_other_participant(request.user))
    } for c in chats]
    response={"Group_info":groups_info,"chats_info":chats_info}
    return JsonResponse(response,safe=False)

# Create your views here.

@login_required
def search_or_find_conversation(request:HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
            return verify_method
    data=request.GET
    if data:
        search_name=data.get("search_name")
        profiles=Profile.objects.filter(Name__startswith=search_name).exclude(Employee_id=request.user).order_by("Name").values("Names")
    else:
        profiles=Profile.objects.exclude(Employee_id=request.user).order_by("Name").values("Names")
    
    return JsonResponse(list(profiles),safe=False)

def delete_message(request: HttpRequest,chat_id:str,msg_id:int):
    ...
    