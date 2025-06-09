"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from accounts.views import UserViewSet
from hotspots.views import HotspotLocationViewSet, HotspotViewSet, SessionViewSet
from analytics.views import DailyUsageViewSet, RevenueRecordViewSet
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = DefaultRouter()
# For accounts
router.register(r'users', UserViewSet) 

# For hotspots
router.register('locations', HotspotLocationViewSet)
router.register('hotspots', HotspotViewSet)
router.register('sessions', SessionViewSet)

# For analytics
router.register('analytics/daily-usage', DailyUsageViewSet, basename='dailyusage'),
router.register('analytics/revenue-record', RevenueRecordViewSet, basename='revenuerecord')

schema_view = get_schema_view(
    openapi.Info(
        title="WiFi Reselling API",
        default_version='v1',
    ),
    public=True,
)

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('', include('accounts.urls')),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('api-token-auth/', obtain_auth_token),  # For token authentication
]
