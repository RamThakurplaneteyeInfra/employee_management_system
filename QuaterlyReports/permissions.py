from rest_framework import permissions
from accounts.filters import _get_user_role_sync
from ems.RequiredImports import HttpRequest


class EntryPermission(permissions.BasePermission):
    def has_permission(self, request:HttpRequest, view):
        # 1. Allow all authenticated users to use GET
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # 2. POST logic: Deny MD, allow Admin and others
        if request.method in ['POST', "PUT","PATCH","DELETE"]:
            # Assuming you have a 'role' attribute on your User or Profile
            # Or checking group membership
            is_md = _get_user_role_sync(user=request.user) == "MD"
            if is_md:
                return False # Denies access with "Permission Denied"
            return True
        
        return False
