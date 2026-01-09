from .models import *
# from django.http import JsonResponse,HttpRequest
from accounts.RequiredImports import *

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
    
