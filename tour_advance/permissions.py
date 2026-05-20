from rest_framework.permissions import BasePermission

from accounts.filters import _get_user_role_sync


def get_role_name(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "Admin"
    return (_get_user_role_sync(user) or "").strip()


def is_admin_or_md(user):
    role = get_role_name(user)
    return user.is_superuser or role in ("Admin", "MD")


class IsAdminOrMD(BasePermission):
    def has_permission(self, request, view):
        return is_admin_or_md(request.user)
