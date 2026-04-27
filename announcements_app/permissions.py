from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.filters import _get_user_role_sync


def _normalize_role(role: str | None) -> str:
    if not role:
        return ""
    return " ".join(str(role).strip().upper().replace("_", " ").split())


class AnnouncementPostPermission(BasePermission):
    """
    Policy:
    - GET/HEAD/OPTIONS: any authenticated user
    - POST: any authenticated user (all employees can create)
    - PUT/PATCH/DELETE:
      - allowed for the creator of the post
      - or privileged roles (Team Lead / MD / Admin / HR)
      - or superuser
    """

    allowed_roles = {
        "TEAMLEAD",
        "TEAM LEAD",
        "TL",
        "LEAD",
        "MD",
        "ADMIN",
        "HR",
    }

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False

        # Any authenticated employee can create.
        if request.method == "POST":
            return True

        # For object-modifying methods, enforce object permission.
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False

        if getattr(user, "is_superuser", False):
            return True

        # Creator can edit/delete their own posts.
        if getattr(obj, "created_by_id", None) == getattr(user, "username", None):
            return True

        role = _get_user_role_sync(user)
        return _normalize_role(role) in self.allowed_roles

