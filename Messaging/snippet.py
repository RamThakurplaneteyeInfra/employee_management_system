from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import GroupMembers,GroupChats
from rest_framework import status

def add_participant_to_groupMembers(group_chat:GroupChats,participant:User):
    try:
        GroupMembers.objects.create(groupchat=group_chat,participant=participant)
    except Exception as e:
        print(e)
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return "Inserted"
    