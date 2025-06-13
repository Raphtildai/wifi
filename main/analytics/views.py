# analytics/views.py

from django.forms import ValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from accounts.permissions import has_access_to_user
from helpers.functions import check_user_access, filter_objects_by_user_access
from .models import DailyUsage, RevenueRecord
from .serializers import DailyUsageSerializer, RevenueRecordSerializer

from django.contrib.auth import get_user_model
User = get_user_model()


class DailyUsageViewSet(viewsets.ModelViewSet):
    queryset = DailyUsage.objects.all()
    serializer_class = DailyUsageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Use generic helper to filter queryset by user access
        return filter_objects_by_user_access(DailyUsage, "user", self.request.user)

    def get_object(self):
        obj = get_object_or_404(DailyUsage, pk=self.kwargs['pk'])
        # Use helper to check permission, raises PermissionDenied if no access
        check_user_access(self.request.user, obj.user)
        return obj

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Daily usage records retrieved successfully",
            "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response({
            "message": "Daily usage record retrieved successfully",
            "data": serializer.data
        })

    def _check_user_access_in_request(self, user_id):
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise PermissionDenied("Specified user does not exist.")
        check_user_access(self.request.user, target_user)
        return target_user

    def create(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or getattr(user, 'user_type', None) in [1, 2]):
            raise PermissionDenied("You do not have permission to create daily usage records.")

        user_id = request.data.get('user')
        if not user_id:
            raise ValidationError({"user": "User field is required."})

        # Get the target user instance
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise ValidationError({"user": "User does not exist."})

        # If reseller, check access
        if getattr(user, 'user_type', None) == 2:
            # Allow if creating usage record for self
            if str(user.pk) != str(user_id) and not has_access_to_user(user, target_user):
                raise PermissionDenied("Resellers cannot create usage records for this user.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            "message": "Daily usage record created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()

        user = request.user
        if not (user.is_superuser or obj.user == user):
            raise PermissionDenied("You do not have permission to update this daily usage record.")

        user_id = request.data.get('user')
        if user_id and str(obj.user.pk) != str(user_id):
            self._check_user_access_in_request(user_id)

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Daily usage record updated successfully",
            "data": serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        if not (user.is_superuser or obj.user == user):
            raise PermissionDenied("You do not have permission to delete this daily usage record.")
        self.perform_destroy(obj)
        return Response({
            "message": "Daily usage record deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)


class RevenueRecordViewSet(viewsets.ModelViewSet):
    queryset = RevenueRecord.objects.all()
    serializer_class = RevenueRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return filter_objects_by_user_access(RevenueRecord, "reseller", self.request.user)

    def get_object(self):
        obj = get_object_or_404(RevenueRecord, pk=self.kwargs['pk'])
        check_user_access(self.request.user, obj.reseller)
        return obj

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Revenue records retrieved successfully",
            "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response({
            "message": "Revenue record retrieved successfully",
            "data": serializer.data
        })

    def _check_reseller_access_in_request(self, reseller_id):
        try:
            target_reseller = User.objects.get(pk=reseller_id)
        except User.DoesNotExist:
            raise PermissionDenied("Specified reseller does not exist.")
        check_user_access(self.request.user, target_reseller)
        return target_reseller

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.is_superuser:
            raise PermissionDenied("You do not have permission to create revenue records.")

        reseller_id = request.data.get('reseller')
        if not reseller_id:
            raise PermissionDenied("Reseller field is required.")
        self._check_reseller_access_in_request(reseller_id)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            "message": "Revenue record created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        if not user.is_superuser:
            raise PermissionDenied("You do not have permission to update this revenue record.")

        reseller_id = request.data.get('reseller')
        if reseller_id and str(obj.reseller.pk) != str(reseller_id):
            self._check_reseller_access_in_request(reseller_id)

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Revenue record updated successfully",
            "data": serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        if not user.is_superuser:
            raise PermissionDenied("You do not have permission to delete this revenue record.")

        self.perform_destroy(obj)
        return Response({
            "message": "Revenue record deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)