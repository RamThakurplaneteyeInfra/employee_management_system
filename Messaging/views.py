from .models import *
from .permissions import *
from .snippet import add_participant_to_groupMembers
from accounts.RequiredImports import *
from django.http import Http404

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
                try:
                    current_user_name=Profile.objects.get(Employee_id=request.user).Name
                except Exception as e:
                    print(e)
                    return JsonResponse({"message":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
                else:
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
def get_group_members(request: HttpRequest,group_id:int):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    get_group_object=GroupChats.objects.get(group_id=group_id)
    Members_object=GroupMembers.objects.filter(groupchat=get_group_object).select_related("participant").annotate(participant_name=F("participant__accounts_profile__Name")).values("participant_name")
    # print(Members_object)
    # return HttpResponse("done")
    # info=[{
    #     "paticipant":gm.participant,
    # } for gm in Members_object]
    
    return JsonResponse(list(Members_object),safe=False)




# @login_required
# def update_group(request: HttpRequest,group_id:int):
#     verify_method=verifyPatch(request)
#     if verify_method:
#             return verify_method
#     has_permission=has_group_create_or_add_member_permission(request.user)
#     try:
#         if has_permission:
#             group_create_fields=["group_name","description","participants"]
#             temp_dict={}
#             data=load_data(request=request)
#             for i in group_create_fields:
#                 if (i=="group_name" or i=="participants") and not data.get(i):
#                     return JsonResponse({"message":"Participants are required"},status=status.HTTP_406_NOT_ACCEPTABLE)
#                 elif i=="participants":
#                     temp_dict[i]=len(data.get(i))
#                 else:
#                     temp_dict[i]=data.get(i)
                
#             chat=get_group_object(user)
#             chat.save()
#         # else:
#     except:
#         ...
#     else:
#         ...
#     ...
@login_required
def add_user(request: HttpRequest,group_id:int):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    group_obj=get_object_or_404(GroupChats,group_id=group_id)
    check_permiss=has_group_create_or_add_member_permission(request.user)
    try:
        if check_permiss:
            data=load_data(request)
            participants_data:dict=data.get("participants")
            user=get_user_object(username=participants_data["username"])
            if isinstance(user,User):
                add_participant_to_groupMembers(group_chat=group_obj,participant=user)
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
    

@login_required
def delete_user(request: HttpRequest,group_id:int,user_id:str):
    verify_method=verifyDelete(request)
    if verify_method:
        return verify_method
    group_obj=get_object_or_404(GroupChats,group_id=group_id)
    check_permiss=has_group_create_or_add_member_permission(request.user)
    try:
        if check_permiss:
            user=get_object_or_404(User,username=user_id)
            GroupMembers.objects.filter(group_id=group_obj,participant=user).first().delete()
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=status.HTTP_403_FORBIDDEN)
    else:
        return JsonResponse({"Message":"user deleted Successfully"},status=status.HTTP_201_CREATED)


@csrf_exempt
@login_required
def delete_group(request: HttpRequest,group_id:int):
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
@csrf_exempt
@login_required
def post_message(request,chat_id:int,is_group=True):
    verify_method=verifyPost(request)
    if verify_method:
        return verify_method
    if is_group:
            chat_obj=get_group_object(group_id=chat_id)
    data=load_data(request.body)
    message=data.get("Message")
    if not message:
        return JsonResponse({"message":"Message is empty"},status=status.HTTP_204_NO_CONTENT)
    sender=request.user
    GroupMessages.objects.create(group=chat_obj,sender=sender,content=message).save()
    return JsonResponse({"message":"Message sent successfully"},status=status.HTTP_201_CREATED)
        
@login_required
def get_messages(request: HttpRequest,chat_id:int):
    request_method=verifyGet(request)
    if request_method:
        return request_method
    else:
        try:
            group_obj= get_object_or_404(GroupChats, group_id=chat_id)
        except Http404 as e:
            print(e)
            is_group=False
        finally:
            if is_group:
                participants=GroupMembers.objects.filter(group_chat=group_obj).select_related("participant","participant__accounts_profile__Name")
                Flag=False
                try:
                    for i in participants:
                        if request.user==i.participant:
                            Flag=True
                    if not Flag:
                        raise PermissionDenied("Not authorised")
                except PermissionDenied:
                    return JsonResponse({"message":"you are not authorised to accessed this conversation"},status=status.HTTP_403_FORBIDDEN)
                else:
                    messages= GroupMessages.objects.filter(group=group_obj).order_by("-created_at")
                    GroupMembers.objects.filter(groupchat=group_obj,participant=request.user).update(seen=True)
            else:
                messages=IndividualMessages.objects.filter(chat_id=chat_id).order_by("-created_at")

        data = [
            {
                "sender": getattr(m,"sender__accounts_profile__Name"),
                "message": m.content,
                "date":m.created_at.strftime("%d/%m/%y"),
                "time": m.created_at.strftime("%H:%M"),
            }
            for m in messages
        ]

        return JsonResponse(data, safe=False)

@login_required
def load_groups_and_chats(request: HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
        return verify_method
    groups=GroupMembers.objects.filter(participant=request.user)
    # chats=IndividualChats.objects.filter(Q(participant1=request.user)|Q(participant2=request.user))
    groups_info=[{
        "group_id":g.groupchat.group_id,
        "group_name":g.groupchat.group_name,
        "description":g.groupchat.description
    } for g in groups]
    return JsonResponse(groups_info,safe=False)
# Create your views here.

@login_required
def search_or_find_conversation(request:HttpRequest):
    verify_method=verifyGet(request)
    if verify_method:
            return verify_method
    data=request.GET
    if data:
        search_name=request.get("search_name")
        profiles=Profile.objects.filter(Name__startswith=search_name).exclude(Employee_id=request.user).order_by("Name").values("Names")
    else:
        profiles=Profile.objects.exclude(Employee_id=request.user).order_by("Name").values("Names")
    
    return JsonResponse(list(profiles),safe=False)

@login_required
def access_or_create_conversation(request: HttpRequest,user_id:int):
        """Get or create conversation with a specific user"""
        verify_method=verifyPost(request)
        if verify_method:
            return verify_method
        try:
            recipient = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse(
                {"message": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        else:
                as_participant1=IndividualChats.objects.filter(Q(participant1=request.user) & Q(participant2=recipient)).first()
                as_participant2=IndividualChats.objects.filter(Q(participant1=recipient)& Q(participant2=request.user)).first()
                if as_participant1 or as_participant2:
                    Individual_chat_id1=as_participant1.chat_id
                    Individual_chat_id2=as_participant2.chat_id
                    if Individual_chat_id1:
                        return get_messages(request,chat_id=Individual_chat_id1)
                    return get_messages(request,chat_id=Individual_chat_id2)
                else:
                    IndividualChats.get_or_create_indivisual_Chat(user1=request.user,user2=recipient)
                    messages=[{}]
                    return JsonResponse(list[messages],safe=False)