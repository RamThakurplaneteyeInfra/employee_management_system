"""Role checks for infra project forms only (does not alter global DRF settings)."""

from rest_framework.permissions import BasePermission

from accounts.filters import _get_user_role_sync

_INFRA_PROJECT_FORM_ROLES = frozenset(
    {
        "Admin",
        "MD",
        "HR",
        "Hr",
        "TeamLead",
        "Teamlead",
    }
)


def _role_name(user) -> str:
    try:
        return (_get_user_role_sync(user) or "").strip()
    except Exception:
        return ""


def user_can_access_infra_project_forms(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = _get_user_role_sync(user)
    return role in _INFRA_PROJECT_FORM_ROLES


def can_md_approve_infra_entry(user) -> bool:
    """Only MD (or superuser) may set entry approval."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _role_name(user) == "MD"


class CanAccessInfraProjectForms(BasePermission):
    """
    Team Lead (TeamLead / Teamlead), MD, HR (HR / Hr), Admin, or superuser.
    Used only on InfraProjectFormViewSet together with IsAuthenticated.
    """

    message = "You do not have permission to access infra project forms."

    def has_permission(self, request, view):
        return user_can_access_infra_project_forms(request.user)

    def has_object_permission(self, request, view, obj):
        return user_can_access_infra_project_forms(request.user)
