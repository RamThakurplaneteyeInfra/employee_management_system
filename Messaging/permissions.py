from accounts.filters import _get_user_role_sync
from .models import GroupChats
from django.contrib.auth import get_user_model

User = get_user_model()


def has_group_create_or_add_member_permission(user: User):
    if user.is_superuser:
        return True
    elif _get_user_role_sync(user=user) == "TeamLead":
        return True
    return False

def can_Delete_group(group: GroupChats, user: User):
    if group.created_by==user:
        return True
    return False
