from rest_framework.permissions import BasePermission

from accounts.filters import _get_user_role_sync

_JOB_MANAGER_ROLES = frozenset(
    {
        "Admin",
        "MD",
        "HR",
        "Hr",
        "TeamLead",
        "Teamlead",
    }
)
def user_can_manage_jobs(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = _get_user_role_sync(user)
    return role in _JOB_MANAGER_ROLES


class CanManageJobOpenings(BasePermission):
    """Create/update/soft-delete job openings (MD, HR, Admin, Team lead)."""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return user_can_manage_jobs(request.user)


class CanViewApplicationDetails(BasePermission):
    """See applicant lists / nested data on a job (same as managers)."""

    def has_permission(self, request, view):
        return user_can_manage_jobs(request.user)


class CanToggleJobState(BasePermission):
    """Allow only the creator of the job opening to open/close it."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return getattr(obj, "created_by_id", None) == getattr(user, "id", None)
