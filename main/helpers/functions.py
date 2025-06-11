from accounts.permissions import has_access_to_user
from django.contrib.auth import get_user_model

from rest_framework.exceptions import PermissionDenied

# Filter queries based on access permission function
def filter_objects_by_user_access(model_class, user_field, request_user):
    User = get_user_model()
    
    user_ids = model_class.objects.values_list(user_field, flat=True).distinct()
    permitted_users = User.objects.filter(id__in=user_ids)
    permitted_users = [u for u in permitted_users if has_access_to_user(request_user, u)]
    
    if not permitted_users:
        # If user is not supposed to access anything, block instead of returning empty
        if not (request_user.is_superuser or request_user.user_type in [1, 2]):  # Admin/Reseller
            raise PermissionDenied("You do not have permission to access this data.")

    
    return model_class.objects.filter(**{f"{user_field}__in": permitted_users})
