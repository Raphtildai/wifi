# accounts/permissions.py

from rest_framework import permissions

from accounts.enums import UserType

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