from django.contrib.auth.models import User
from .models import GroupMembers,GroupChats
from django.http.response import JsonResponse

def add_participant_to_groupMembers(group_chat:GroupChats,participant:User):
    try:
        GroupMembers.objects.create(groupchat=group_chat,participant=participant)
    except Exception as e:
        print(e)
        return  JsonResponse({"message":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
    else:
        return "Inserted"
    