# accounts/permissions.py

from rest_framework import permissions
from accounts.enums import UserType
from rest_framework.exceptions import PermissionDenied

def has_access_to_user(request_user, target_user):
    if request_user.is_superuser:
        return True
    if request_user.user_type == 1 and target_user.user_type in [2, 3]:  # Admin
        return True
    if request_user.user_type == 2 and getattr(target_user, "parent_reseller_id", None) == request_user.id:  # Reseller
        return True
    if request_user.pk == target_user.pk:
        return True
    return False

class IsAdminOrSelf(permissions.BasePermission):
    """
    Custom permission to allow superusers, admins, or object owners to perform unsafe actions.
    """

    def has_permission(self, request, view):
        # Allow any authenticated user for safe methods
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Allow authenticated users for write methods — detailed check in has_object_permission
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Superuser or admin
        if request.user.is_superuser or getattr(request.user, "user_type", None) == UserType.ADMIN:
            return True

        # Reseller editing customer-related object (assuming object has .user or .reseller)
        target_user = getattr(obj, "user", None) or getattr(obj, "reseller", None)
        if target_user and has_access_to_user(request.user, target_user):
            return True

        # Fallback to exact ownership, if applicable
        for field in ["owner", "user", "reseller"]:
            if getattr(obj, field, None) == request.user:
                return True

        return False
