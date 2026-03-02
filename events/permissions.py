from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from ems.RequiredImports import HttpRequest


def _get_user_role_name(request):
    """Return the request user's role name from Profile, or None if no profile."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return None
    try:
        from accounts.filters import _get_user_role_sync
        return _get_user_role_sync(request.user)
    except Exception:
        return None


class IsAdminOrMD(BasePermission):
    """
    Custom permission to only allow Admins or users with role 'MD'.
    """
    def has_permission(self, request: HttpRequest, view):
        if request.user.is_superuser:
            return True
        role = _get_user_role_name(request)
        return role == "MD"


class IsAdminOrMDOrHR(BasePermission):
    """
    Allows superuser, or users with role 'Admin', 'MD', or 'HR' to perform any action
    (GET, POST, PUT, PATCH, DELETE) on the view. Used for events modelsets so HR has full access.
    """
    def has_permission(self, request: HttpRequest, view):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = _get_user_role_name(request)
        return role in ("Admin", "MD", "HR")

