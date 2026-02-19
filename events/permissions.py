from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from ems.RequiredImports import HttpRequest


class IsAdminOrMD(BasePermission):
    """
    Custom permission to only allow Admins or users with role 'MD'.
    Assumes your User model has a 'role' attribute or similar.
    """
    def has_permission(self, request:HttpRequest, view):
        # Allow if user is staff (Admin)
        if request.user.is_superuser:
            return True
        return False     
        # Check for 'MD' role (Adjust 'role' attribute name as per your User model)

