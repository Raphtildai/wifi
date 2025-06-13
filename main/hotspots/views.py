from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from .models import HotspotLocation, Hotspot, Session
from .serializers import HotspotLocationSerializer, HotspotSerializer, SessionSerializer
from accounts.permissions import IsAdminOrReadOnly, IsAdminOrSelf
from accounts.permissions import has_access_to_user
from helpers.functions import filter_objects_by_user_access
from main.exceptions import safe_destroy


class HotspotLocationViewSet(viewsets.ModelViewSet):
    serializer_class = HotspotLocationSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in [1, 2]:  # Admin or Reseller
            return Session.objects.all()
        return Session.objects.none()

    def get_object(self):
        obj = get_object_or_404(HotspotLocation, pk=self.kwargs['pk'])
        user = self.request.user
        if user.is_superuser:
            return obj
        elif user.user_type == 1:  # Admin
            return obj
        elif user.user_type == 2 and obj.hotspot.owner.parent_reseller_id == user.id:
            return obj
        elif obj.hotspot.owner == user:
            return obj
        raise PermissionDenied("You do not have permission to access this hotspot location.")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"message": "Hotspot locations retrieved successfully", "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"message": "Hotspot location created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "Hotspot location retrieved successfully", "data": serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Hotspot location updated successfully", "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        return safe_destroy(instance, self.perform_destroy)

class HotspotViewSet(viewsets.ModelViewSet):
    serializer_class = HotspotSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['hotspot_type']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Hotspot.objects.none()
        if user.is_superuser or user.user_type in [1, 2]:  # Admin and Reseller
            return Hotspot.objects.all()
        return Hotspot.objects.none()

    def get_object(self):
        obj = get_object_or_404(Hotspot, pk=self.kwargs['pk'])
        user = self.request.user
        if user.is_superuser:
            return obj
        elif user.user_type == 1 and obj.owner.user_type == 2:  # Admin can access reseller hotspots
            return obj
        elif user.user_type == 2 and obj.owner == user:
            return obj
        raise PermissionDenied("You do not have permission to access this hotspot.")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"message": "Hotspots retrieved successfully", "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"message": "Hotspot created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "Hotspot retrieved successfully", "data": serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Example critical field restriction: only superuser can change owner or hotspot_type (optional)
        critical_fields = ['owner', 'hotspot_type']
        if any(field in serializer.validated_data for field in critical_fields):
            if not (request.user.is_superuser):
                raise PermissionDenied("Only super-admins can update critical fields")

        self.perform_update(serializer)
        return Response({"message": "Hotspot updated successfully", "data": serializer.data})

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        return safe_destroy(instance, self.perform_destroy)

class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']

    def get_queryset(self):
        return filter_objects_by_user_access(
            model_class=Session,
            user_field="user",
            request_user=self.request.user
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"message": "Sessions retrieved successfully", "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Session created successfully", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "Session retrieved successfully", "data": serializer.data})

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_access_to_user(request.user, instance.user):
            raise PermissionDenied("You do not have access to modify this Sessions.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_access_to_user(request.user, instance.user):
            raise PermissionDenied("Only admins can update sessions.")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.user_type == 1):
            raise PermissionDenied("Only admins can delete sessions.")
        instance = self.get_object()
        return safe_destroy(instance, self.perform_destroy)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)