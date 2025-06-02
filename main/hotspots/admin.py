# hotspots/admin.py
from django.contrib import admin
from .models import Hotspot, HotspotLocation, Session
from django.contrib.auth import get_user_model

User = get_user_model()

class HotspotLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'latitude', 'longitude')
    search_fields = ('name', 'address')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:
            return qs
        elif request.user.user_type == 2:
            return qs.filter(hotspots__owner=request.user).distinct()
        return qs.none()

class HotspotAdmin(admin.ModelAdmin):
    list_display = ('ssid', 'owner', 'location', 'hotspot_type', 'max_users', 'is_active')
    list_filter = ('hotspot_type', 'is_active')
    search_fields = ('ssid', 'owner__username', 'location__name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:
            return qs
        elif request.user.user_type == 2:
            return qs.filter(owner=request.user)
        return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "owner":
            if request.user.user_type == 2:  # Reseller
                kwargs["queryset"] = User.objects.filter(pk=request.user.pk)
            elif request.user.user_type == 1:  # Admin
                kwargs["queryset"] = User.objects.filter(user_type__in=[1, 2])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'hotspot', 'start_time', 'end_time', 'data_used')
    list_filter = ('hotspot', 'start_time')
    readonly_fields = ('user', 'hotspot', 'start_time', 'end_time', 'data_used', 'ip_address')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:
            return qs
        elif request.user.user_type == 2:
            return qs.filter(hotspot__owner=request.user)
        return qs.none()

admin.site.register(HotspotLocation, HotspotLocationAdmin)
admin.site.register(Hotspot, HotspotAdmin)
admin.site.register(Session, SessionAdmin)