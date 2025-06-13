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
    Allow superusers/admins full access.
    Allow users to access their own object.
    Restrict creation and deletion to admins/superusers only.
    """

    def has_permission(self, request, view):
        # Allow safe methods to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # For POST (create) and DELETE (list or detail delete), restrict to admins/superusers
        if request.method in ['POST', 'DELETE']:
            return bool(
                request.user and 
                request.user.is_authenticated and 
                (request.user.is_superuser or request.user.user_type == UserType.ADMIN)
            )

        # For other unsafe methods (PATCH, PUT), allow authenticated and check object permission later
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Safe methods allowed
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admins and superusers can do anything
        if request.user.is_superuser or request.user.user_type == UserType.ADMIN:
            return True

        # Resellers can modify users they have access to
        target_user = getattr(obj, "user", None) or getattr(obj, "reseller", None)
        if target_user and has_access_to_user(request.user, target_user):
            return True

        # Exact ownership fallback
        for field in ["owner", "user", "reseller"]:
            if getattr(obj, field, None) == request.user:
                return True

        return False
    
class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows full access only to superusers and admins.
    Read-only for others.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user and request.user.is_authenticated and
            (request.user.is_superuser or request.user.user_type == UserType.ADMIN)
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)