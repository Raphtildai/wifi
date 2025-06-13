# accounts/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer
from .permissions import IsAdminOrSelf
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
    
    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)
        print(f"Auth headers: {request.META.get('HTTP_AUTHORIZATION')}")
        return request
    
    def get_object(self):
        obj = get_object_or_404(User, pk=self.kwargs['pk'])
        user = self.request.user
        if user.is_superuser:
            return obj
        elif user.user_type == 1 and obj.user_type in [2, 3]:
            return obj
        elif user.user_type == 2 and obj.parent_reseller_id == user.id:
            return obj
        elif user.pk == obj.pk:
            return obj
        raise PermissionDenied("You do not have permission to access this user.")
    
    def get_queryset(self):
        user = self.request.user
        print(f"User in get_queryset: {user} (authenticated: {user.is_authenticated})")
        
        if not user.is_authenticated:
            print("User not authenticated")
            return User.objects.none()  # FIXED here - return queryset, NOT Response
            
        if user.is_superuser:
            return User.objects.all()
        elif user.user_type == 1:
            return User.objects.filter(user_type__in=[2, 3])
        elif user.user_type == 2:
            return User.objects.filter(parent_reseller=user)
        return User.objects.filter(pk=user.pk)

    def list(self, request, *args, **kwargs):
        print(f"User in list: {request.user} (authenticated: {request.user.is_authenticated})")
        if not request.user.is_authenticated:
            print("Returning 401 - no auth credentials")
            print("All headers:", request.META)
            return Response(
                {"message": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"message": "Users retrieved successfully", "data": serializer.data})
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"message": "User created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "User retrieved successfully", "data": serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "User updated successfully", "data": serializer.data})

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        # Critical fields that only super admins can update
        critical_fields = ['user_type', 'is_verified', 'credit']

        if any(field in validated_data for field in critical_fields):
            if not (user.is_authenticated and user.is_superuser):
                raise PermissionDenied("Only super-admins can update critical fields")

        serializer.save()