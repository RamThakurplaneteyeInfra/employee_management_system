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


def user_can_view_farm_service_request(user, obj) -> bool:
    """Visible only to MD (or superuser) and the request creator."""
    if not user or not user.is_authenticated:
        return False
    if user_is_farm_service_md(user):
        return True
    return obj.created_by_id == user.pk


def user_can_edit_farm_service_request(user, obj) -> bool:
    """Edit allowed for the same people who can view: MD / superuser / creator."""
    return user_can_view_farm_service_request(user, obj)


class CanEditFarmServiceRequest(BasePermission):
    """
    View/edit access allowed for:
    - creator of the request
    - MD
    - superuser
    """

    message = "You do not have permission to access this farm service request."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.method in ("PATCH", "PUT", "DELETE"):
            return user_can_view_farm_service_request(request.user, obj)
        return bool(request.user and request.user.is_authenticated)
