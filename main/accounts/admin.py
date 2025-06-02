# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile
from hotspots.models import Hotspot, Session
from analytics.models import DailyUsage, RevenueRecord

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'user_type', 'credit', 'is_active')
    list_filter = ('user_type', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('User Type', {'fields': ('user_type', 'credit', 'phone', 'address', 'parent_reseller')}),
    )
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser and not (request.user.user_type == 1 and request.user.email == 'admin@example.com'):
            # Remove sensitive fields for non-admins
            fieldsets = list(fieldsets)
            for i, fieldset in enumerate(fieldsets):
                if fieldset[0] == 'Permissions':
                    fieldsets[i] = (fieldset[0], {
                        'fields': ('is_active', 'groups'),
                        'classes': ('collapse',)
                    })
        return fieldsets
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (request.user.user_type == 1 and request.user.email == 'admin@example.com'):
            return qs
        elif request.user.user_type == 1:  # Regular admin
            return qs.filter(user_type__in=[2, 3])  # See resellers and customers
        elif request.user.user_type == 2:  # Reseller
            return qs.filter(user_type=3, parent_reseller=request.user)  # Only their customers
        return qs.none()
    
    def get_inline_instances(self, request, obj=None):
        # Only show profile inline for admins and the user's own profile
        if (request.user.is_superuser or 
            (obj and (obj == request.user or request.user.user_type == 1))):
            return super().get_inline_instances(request, obj)
        return []

admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'commission_rate')
    search_fields = ('user__username', 'company_name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:
            return qs
        elif request.user.user_type == 2:
            return qs.filter(user__parent_reseller=request.user)
        return qs.none()