from rest_framework import viewsets, permissions
from .models import HotspotLocation, Hotspot, Session
from .serializers import (
    HotspotLocationSerializer,
    HotspotSerializer,
    SessionSerializer
)
from accounts.permissions import IsAdminOrSelf

class HotspotLocationViewSet(viewsets.ModelViewSet):
    queryset = HotspotLocation.objects.all()
    serializer_class = HotspotLocationSerializer
    permission_classes = [permissions.IsAuthenticated]


class HotspotViewSet(viewsets.ModelViewSet):
    queryset = Hotspot.objects.all()
    serializer_class = HotspotSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type == 1:  # Admin
            return Hotspot.objects.all()
        elif user.user_type == 2:  # Reseller
            return Hotspot.objects.filter(owner=user)
        return Hotspot.objects.none()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in [1, 2]:  # Admin or Reseller
            return Session.objects.all()
        return Session.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
