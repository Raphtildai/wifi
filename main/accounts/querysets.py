# accounts/querysets.py
def get_user_filtered_queryset(request_user, queryset):
    if request_user.is_superuser:
        return queryset
    if request_user.user_type == 1:
        return queryset.filter(user__user_type__in=[2, 3])
    if request_user.user_type == 2:
        return queryset.filter(user__parent_reseller=request_user)
    return queryset.filter(user=request_user)
