from rest_framework.permissions import BasePermission

from accounts.filters import _get_user_role_sync


_FARM_SERVICE_EDIT_ROLES = frozenset({"Admin", "MD", "HR", "Hr"})


def user_can_edit_farm_service_request(user, obj) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = (_get_user_role_sync(user) or "").strip()
    if role in _FARM_SERVICE_EDIT_ROLES:
        return True
    return obj.created_by_id == user.pk


class CanEditFarmServiceRequest(BasePermission):
    """
    Edit access allowed for:
    - creator of the request
    - Admin / MD / HR (including role value "Hr")
    - superuser
    """

    message = "You do not have permission to edit this farm service request."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in ("PATCH", "PUT", "DELETE"):
            return user_can_edit_farm_service_request(request.user, obj)
        return bool(request.user and request.user.is_authenticated)

