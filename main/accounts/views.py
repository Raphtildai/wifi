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
        # print(f"User before auth: {request.user}")
        return request
    
    # Override get_object() for secure access checks
    def get_object(self):
        obj = get_object_or_404(User, pk=self.kwargs['pk'])

        # Role-based access control
        user = self.request.user
        if user.is_superuser:
            return obj
        elif user.user_type == 1 and obj.user_type in [2, 3]:  # Admin sees resellers/customers
            return obj
        elif user.user_type == 2 and obj.parent_reseller_id == user.id:  # Reseller sees own customers
            return obj
        elif user.pk == obj.pk:  # Self-access
            return obj

        raise PermissionDenied("You do not have permission to access this user.")
    
    def get_queryset(self):
        user = self.request.user
        print(f"User in get_queryset: {user} (authenticated: {user.is_authenticated})")
        
        if not user.is_authenticated:
            print("User not authenticated")
            return Response({
                "message": "User not authenticated",
                "data": User.objects.none()
            })
            
        if user.is_superuser:
            return User.objects.all()
        elif user.user_type == 1:  # Admin
            return User.objects.filter(user_type__in=[2, 3])
        elif user.user_type == 2:  # Reseller
            return User.objects.filter(parent_reseller=user)
        return User.objects.filter(pk=user.pk)

    def list(self, request, *args, **kwargs):
        print(f"User in list: {request.user} (authenticated: {request.user.is_authenticated})")
        if not request.user.is_authenticated:
            print("Returning 401 - no auth credentials")
            # Print all headers for debugging
            print("All headers:", request.META)
            return Response(
                {"message": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Users retrieved successfully",
            "data": serializer.data
        })