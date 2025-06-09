# accounts/permissions.py

from rest_framework import permissions
from accounts.enums import UserType
from rest_framework.exceptions import PermissionDenied

class IsAdminOrSelf(permissions.BasePermission):
    """
    Custom permission to only allow superusers or the owner of the object to perform unsafe actions.
    """

    def has_permission(self, request, view):
        # Safe methods (GET, HEAD, OPTIONS) are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions are only allowed to authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Always allow safe methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow access if superuser
        if request.user.is_superuser or getattr(request.user, "user_type", None) == 1:
            return True
        
        # Reseller can edit their customers
        if (
            request.user.user_type == UserType.RESELLER and
            obj.parent_reseller == request.user
        ):
            return True

        # Allow access if the user is the owner
        return getattr(obj, "owner", None) == request.user

    def has_access_to_user(request_user, target_user):
        if request_user.is_superuser:
            return True
        if request_user.user_type == 1 and target_user.user_type in [2, 3]:  # Admin
            return True
        if request_user.user_type == 2 and target_user.parent_reseller_id == request_user.id:  # Reseller
            return True
        if request_user.pk == target_user.pk:
            return True
        raise PermissionDenied("You do not have permission to access this resource.")
