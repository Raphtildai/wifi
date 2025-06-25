# helpers/functions.py

from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied
from accounts.permissions import has_access_to_user

def check_user_access(request_user, target_user, access_check_func=None):
    """
    Check if request_user has access to target_user, raise PermissionDenied if not.

    access_check_func(request_user, target_user) can be customized.
    """
    if request_user.is_superuser:
        return

    if access_check_func:
        allowed = access_check_func(request_user, target_user)
    else:
        allowed = has_access_to_user(request_user, target_user)

    if not allowed:
        raise PermissionDenied("You do not have permission to access this user.")

def filter_objects_by_user_access(model_class, user_field, request_user, access_check_func=None):
    """
    Filters queryset of model_class by checking access to users related via user_field.

    - model_class: Django model class to filter
    - user_field: string, name of field on model_class that links to User (e.g. 'user' or 'owner')
    - request_user: user making the request
    - access_check_func: optional function(request_user, target_user) -> bool that returns True if allowed

    Returns filtered queryset or raises PermissionDenied if no access.
    """
    User = get_user_model()
    qs = model_class.objects.all()

    # Get all distinct user ids referenced by the model
    user_ids = qs.values_list(user_field, flat=True).distinct()

    # Get users queryset filtered by access_check_func if provided
    users_qs = User.objects.filter(id__in=user_ids)

    if access_check_func:
        # Filter users by access_check_func applied on each user (note: this is per-user in Python)
        permitted_users = [u for u in users_qs if access_check_func(request_user, u)]
    else:
        # Default to has_access_to_user from accounts.permissions
        permitted_users = [u for u in users_qs if has_access_to_user(request_user, u)]

    if not permitted_users:
        # If no access at all
        if not (request_user.is_superuser or getattr(request_user, 'user_type', None) in [1, 2]):
            raise PermissionDenied("You do not have permission to access this data.")

        # If superuser/admin/reseller but no permitted users, return empty queryset
        return model_class.objects.none()

    permitted_user_ids = [u.id for u in permitted_users]
    return qs.filter(**{f"{user_field}__in": permitted_user_ids})