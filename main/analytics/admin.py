# analytics/admin.py
from django.contrib import admin
from .models import DailyUsage, RevenueRecord
from django.contrib.auth import get_user_model

User = get_user_model()

class DailyUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'hotspot', 'date', 'data_used', 'session_count')
    list_filter = ('date', 'hotspot')
    search_fields = ('user__username', 'hotspot__ssid')
    readonly_fields = ('user', 'hotspot', 'date', 'data_used', 'session_count', 'duration_seconds')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:  # Admin
            return qs
        elif request.user.user_type == 2:  # Reseller
            return qs.filter(user__parent_reseller=request.user)
        return qs.none()  # Customers see nothing

class RevenueRecordAdmin(admin.ModelAdmin):
    list_display = ('reseller', 'date', 'total_sales', 'commissions_earned', 'new_customers')
    list_filter = ('date', 'reseller')
    readonly_fields = ('reseller', 'date', 'total_sales', 'commissions_earned', 'new_customers')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:  # Admin
            return qs
        elif request.user.user_type == 2:  # Reseller
            return qs.filter(reseller=request.user)
        return qs.none()  # Customers see nothing

admin.site.register(DailyUsage, DailyUsageAdmin)
admin.site.register(RevenueRecord, RevenueRecordAdmin)