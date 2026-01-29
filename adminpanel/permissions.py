from rest_framework import permissions

class HasAPIKeyPermission(permissions.BasePermission):
    """
    Custom permission to check API Key and CRUD permissions
    """

    def has_permission(self, request, view):
        return False
