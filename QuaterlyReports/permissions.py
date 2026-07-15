from rest_framework import permissions
from accounts.filters import _get_user_role_sync
from ems.RequiredImports import HttpRequest


class EntryPermission(permissions.BasePermission):
    def has_permission(self, request: HttpRequest, view):
        if not request.user.is_authenticated:
            return False

        # Allow all authenticated users to use GET / HEAD / OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True

        # Deny MD from creating actionable entries (POST)
        if request.method == "POST":
            return _get_user_role_sync(user=request.user) != "MD"

        # Allow PATCH / PUT / DELETE for authenticated users, including MD,
        # so MD can complete shared-with entries (view-level checks still apply).
        if request.method in ["PUT", "PATCH", "DELETE"]:
            return True

        return False
