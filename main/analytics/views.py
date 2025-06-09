# analytics/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import DailyUsage, RevenueRecord
from .serializers import DailyUsageSerializer, RevenueRecordSerializer
from accounts.permissions import has_access_to_user


class DailyUsageViewSet(viewsets.ModelViewSet):
    queryset = DailyUsage.objects.all()
    serializer_class = DailyUsageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return DailyUsage.objects.filter(user__in=[
            u for u in DailyUsage.objects.values_list("user", flat=True).distinct()
            if has_access_to_user(user, u)
        ])

    def get_object(self):
        obj = get_object_or_404(DailyUsage, pk=self.kwargs['pk'])
        if not has_access_to_user(self.request.user, obj.user):
            return Response(
                {"message": "You do not have permission to access this usage record."},
                status=status.HTTP_401_UNAUTHORIZED
            )
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
        user = self.request.user
        return RevenueRecord.objects.filter(reseller__in=[
            u for u in RevenueRecord.objects.values_list("reseller", flat=True).distinct()
            if has_access_to_user(user, u)
        ])

    def get_object(self):
        obj = get_object_or_404(RevenueRecord, pk=self.kwargs['pk'])
        if not has_access_to_user(self.request.user, obj.reseller):
            return Response(
                {"message": "You do not have permission to access this revenue record."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return obj

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Revenue records retrieved successfully",
            "data": serializer.data
        })