# accounts/permissions.py
from rest_framework import permissions

class IsAdminOrSelf(permissions.BasePermission):
    """
    Allow access to admins or the user themselves.
    """
    def has_permission(self, request, view):
        # Allow list views only for authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow admins or the user themselves
        return request.user.is_superuser or obj == request.user