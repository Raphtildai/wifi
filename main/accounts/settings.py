# settings.py
ADMIN_SITE_HEADER = "WiFi Reselling Admin"
ADMIN_SITE_TITLE = "WiFi Reselling Portal"
ADMIN_INDEX_TITLE = "Welcome to WiFi Reselling Portal"

# Custom admin site class
from django.contrib import admin

class CustomAdminSite(admin.AdminSite):
    site_header = ADMIN_SITE_HEADER
    site_title = ADMIN_SITE_TITLE
    index_title = ADMIN_INDEX_TITLE

    def has_permission(self, request):
        """
        Only allow superusers and admins to access the admin
        """
        return request.user.is_active and (
            request.user.is_superuser or 
            request.user.user_type == 1 or 
            request.user.user_type == 2
        )

# Replace default admin site
admin_site = CustomAdminSite(name='custom_admin')
admin.site = admin_site