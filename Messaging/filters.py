from ems.verify_methods import *
from accounts.filters import *
from .models import *

def get_group_object(group_id:int):
    try:
        group=GroupChats.objects.get(group_id=group_id)
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=404)
    else:
        return group
    
def get_groupmember_object(group:GroupChats,participant:User):
    try:
            member=GroupMembers.objects.get(groupchat=group,participant=participant)
    except Exception as e:
            print(e)
            return JsonResponse({"message":f"{e}"},status=404)
    else:
            return member
    
def check_user_member(user: User,group_id:int):
    group=get_group_object(user=user,group_id=group_id)
    if isinstance(group,GroupChats):
        member_instance=get_groupmember_object(group=group,participant=user)
        if isinstance(member_instance,GroupMembers):
            return member_instance
        else:
            return member_instance
    else:
        return group
    
def get_individual_chat_object(chat_id:int):
    try:
        chat=IndividualChats.objects.get(chat_id=chat_id)
    except Exception as e:
        print(e)
        return JsonResponse({"message":f"{e}"},status=404)
    else:
        return chat
    
def check_group_or_chat(chat_id,is_group=False):
    if chat_id[0]=="G":
        is_group=True
    else:
        is_group=False
    return is_group

def get_group_members(group_id:str):
    try:
        get_group_object=get_object_or_404(GroupChats,group_id=group_id)
    except Http404 as e:
        print(e)
        error_response=JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
        return error_response
    else:
        Members_object=GroupMembers.objects.filter(groupchat=get_group_object).select_related("participant").annotate(participant_name=F("participant__accounts_profile__Name")).values("participant","participant_name","groupchat")
        return JsonResponse(list(Members_object),safe=False)
    
def get_messages(request:HttpRequest,chat_id:str):
        try:
            is_group=True
            group_obj= get_object_or_404(GroupChats, group_id=chat_id)
        except Http404 as e:
            print(e)
            is_group=False
            # return JsonResponse({"message":f"{e}"},status=status.HTTP_403_FORBIDDEN)
        finally:
            if is_group:
                participants=GroupMembers.objects.filter(groupchat=group_obj).select_related("participant")
                Flag=False
                try:
                    for i in participants:
                        if request.user==i.participant:
                            Flag=True
                    if not Flag:
                        raise PermissionDenied("Not authorised") # type: ignore
                except PermissionDenied:
                    return JsonResponse({"message":"you are not authorised to accessed this conversation"},status=status.HTTP_403_FORBIDDEN)
                else:
                    messages= GroupMessages.objects.filter(group=group_obj).order_by("-created_at")
                    GroupMembers.objects.filter(groupchat=group_obj,participant=request.user).update(seen=True)
            else:
                try:
                    chat_obj=get_object_or_404(IndividualChats,chat_id=chat_id)
                except Http404 as e:
                    print(e)
                    return JsonResponse({"message":f"{e}"},status=status.HTTP_403_FORBIDDEN)
                else:
                    messages=IndividualMessages.objects.filter(chat=chat_obj).order_by("-created_at")

        data = [
            {
                "sender": get_users_Name(m.sender),
                "message": m.content,
                "date":m.created_at.strftime("%d/%m/%y"),
                "time": m.created_at.strftime("%H:%M"),
            }
            for m in messages
        ]
        return JsonResponse(data, safe=False)
