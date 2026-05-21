from rest_framework.permissions import BasePermission

from accounts.filters import _get_user_role_sync

HR_ROLES = frozenset({"HR", "Hr"})


def get_role_name(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "Admin"
    return (_get_user_role_sync(user) or "").strip()


def is_hr(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return get_role_name(user) in HR_ROLES


def is_certificate_owner(user, certificate):
    return (
        certificate is not None
        and user
        and user.is_authenticated
        and certificate.employee_id == user.pk
    )


class CertificatePermission(BasePermission):
    """
    HR: full access to all certificates.
    Creator (owner): full access to own certificates only.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if is_hr(request.user):
            return True
        return is_certificate_owner(request.user, obj)
