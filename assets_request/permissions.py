from __future__ import annotations

from typing import Optional, Set

from rest_framework.permissions import BasePermission


ALLOWED_ROLE_NAMES: Set[str] = {"Admin", "Hr", "MD", "TeamLead"}


def get_role_name(user) -> Optional[str]:
    """
    Resolve the user's role name from accounts.Profile.
    Returns None if profile/role is missing.
    """
    if not getattr(user, "is_authenticated", False):
        return None

    if getattr(user, "is_superuser", False):
        return "Admin"

    profile = getattr(user, "accounts_profile", None)
    if not profile:
        return None

    role_obj = getattr(profile, "Role", None)
    if not role_obj:
        return None

    return getattr(role_obj, "role_name", None)


class IsAssetRequestAllowedRole(BasePermission):
    """
    Only TeamLead / Hr / Admin / MD can access this module.
    """

    def has_permission(self, request, view) -> bool:
        role_name = get_role_name(request.user)
        return role_name in ALLOWED_ROLE_NAMES

