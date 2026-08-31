from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.filters import _get_user_role_sync


_FARM_SERVICE_VIEW_ROLES = frozenset({"MD"})


def _user_role(user) -> str:
    return (_get_user_role_sync(user) or "").strip()


def user_is_farm_service_md(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _user_role(user) in _FARM_SERVICE_VIEW_ROLES


def user_is_farm_service_team_member(user, obj) -> bool:
    if not user or not user.is_authenticated or obj is None:
        return False
    return obj.tasks.filter(team_members=user).exists()


def user_can_view_farm_service_request(user, obj) -> bool:
    """Visible to MD/superuser, request creator, or any task team member."""
    if not user or not user.is_authenticated:
        return False
    if user_is_farm_service_md(user):
        return True
    if obj.created_by_id == user.pk:
        return True
    return user_is_farm_service_team_member(user, obj)


def user_can_edit_farm_service_request(user, obj) -> bool:
    """Edit allowed for MD / superuser / creator (not team members alone)."""
    if not user or not user.is_authenticated:
        return False
    if user_is_farm_service_md(user):
        return True
    return obj.created_by_id == user.pk


class CanEditFarmServiceRequest(BasePermission):
    """
    View access: creator, task team members, MD, superuser.
    Edit access: creator, MD, superuser.
    """

    message = "You do not have permission to access this farm service request."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return user_can_view_farm_service_request(request.user, obj)
        if request.method in ("PATCH", "PUT", "DELETE"):
            return user_can_edit_farm_service_request(request.user, obj)
        return bool(request.user and request.user.is_authenticated)
