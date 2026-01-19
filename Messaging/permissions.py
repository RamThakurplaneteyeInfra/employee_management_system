from django.contrib.auth.models import User
from accounts.RequiredImports import *
from .filters import *

def has_group_create_or_add_member_permission(user:User):
    if user.is_superuser:
        return True
    elif get_user_role(user=user)=="TeamLead":
        return True
    return False

def can_Delete_group(group:GroupChats,user: User):
    if group.created_by==user:
        return True
    return False
