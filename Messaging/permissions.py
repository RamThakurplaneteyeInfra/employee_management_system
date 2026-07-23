from accounts.filters import _get_user_role_sync
from .models import GroupChats
from django.contrib.auth import get_user_model

User = get_user_model()

_GROUP_CREATE_ROLES = frozenset({"MD", "TeamLead", "Teamlead", "HR", "Hr"})


def can_manage_group_members(user: User, group: GroupChats) -> bool:
    """MD or the group creator may add/remove members in this group."""
    if group.created_by_id == user.username:
        return True
    if _get_user_role_sync(user=user) == "MD":
        return True
    return False


def can_create_group(user: User) -> bool:
    """Who may create a new group (creator check does not apply until after creation)."""
    return _get_user_role_sync(user=user) in _GROUP_CREATE_ROLES


def can_Delete_group(group: GroupChats, user: User):
    if group.created_by == user:
        return True
    return False
