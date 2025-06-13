# billing/views.py
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied
from billing.models import Plan, Subscription, Transaction
from billing.serializers import PlanSerializer, SubscriptionSerializer, TransactionSerializer
# from accounts.permissions import has_access_to_user
from helpers.functions import filter_objects_by_user_access
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import has_access_to_user
from accounts.enums import UserType

class PlanViewSet(ModelViewSet):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    
    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_superuser and user.user_type != UserType.ADMIN:
            raise PermissionDenied("Only admins can create plans.")
        serializer.save()

    def update(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_superuser and user.user_type != UserType.ADMIN:
            raise PermissionDenied("Only admins can update plans.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_superuser and user.user_type != UserType.ADMIN:
            raise PermissionDenied("Only admins can delete plans.")
        return super().destroy(request, *args, **kwargs)

class SubscriptionViewSet(ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active', 'auto_renew', 'plan']
    ordering_fields = ['start_date', 'end_date']
    
    def get_object(self):
        obj = super().get_object()
        if not has_access_to_user(self.request.user, obj.user):
            raise PermissionDenied("You do not have permission to access this subscription.")
        return obj

    def get_queryset(self):
        return filter_objects_by_user_access(
            model_class=Subscription,
            user_field="user",
            request_user=self.request.user
        )
        
    def perform_create(self, serializer):
        user = self.request.user
        if user.user_type not in [UserType.ADMIN, UserType.RESELLER]:
            raise PermissionDenied("Only admins or resellers can create subscriptions.")
        serializer.save()
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_access_to_user(request.user, instance.user):
            raise PermissionDenied("You do not have access to modify this subscription.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_access_to_user(request.user, instance.user):
            raise PermissionDenied("You do not have access to delete this subscription.")
        return super().destroy(request, *args, **kwargs)

class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['transaction_type', 'is_successful']
    ordering_fields = ['timestamp', 'amount']
    search_fields = ['reference', 'description']

    def get_queryset(self):
        return filter_objects_by_user_access(
            model_class=Transaction,
            user_field="user",
            request_user=self.request.user
        )
    
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_access_to_user(request.user, instance.user):
            raise PermissionDenied("You do not have access to modify this Transaction.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_access_to_user(request.user, instance.user):
            raise PermissionDenied("You do not have access to delete this Transaction.")
        return super().destroy(request, *args, **kwargs)
