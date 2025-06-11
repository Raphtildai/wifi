# analytics/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from helpers.functions import filter_objects_by_user_access

from .models import DailyUsage, RevenueRecord
from .serializers import DailyUsageSerializer, RevenueRecordSerializer
from django.contrib.auth import get_user_model
from accounts.permissions import has_access_to_user


class DailyUsageViewSet(viewsets.ModelViewSet):
    queryset = DailyUsage.objects.all()
    serializer_class = DailyUsageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):        
        return filter_objects_by_user_access(DailyUsage, "user", self.request.user)

    def get_object(self):
        obj = get_object_or_404(DailyUsage, pk=self.kwargs['pk'])
        if not has_access_to_user(self.request.user, obj.user):
            raise PermissionDenied("You do not have permission to access this usage record.")
        return obj

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Daily usage records retrieved successfully",
            "data": serializer.data
        })

class RevenueRecordViewSet(viewsets.ModelViewSet):
    queryset = RevenueRecord.objects.all()
    serializer_class = RevenueRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return filter_objects_by_user_access(RevenueRecord, 'reseller', self.request.user)

    def get_object(self):
        obj = get_object_or_404(RevenueRecord, pk=self.kwargs['pk'])
        if not has_access_to_user(self.request.user, obj.reseller):
            raise PermissionDenied("You do not have permission to access this revenue record.")
        return obj

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Revenue records retrieved successfully",
            "data": serializer.data
        })