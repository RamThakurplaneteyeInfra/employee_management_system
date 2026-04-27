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


def user_can_access_infra_project_forms(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = _get_user_role_sync(user)
    return role in _INFRA_PROJECT_FORM_ROLES


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
