# hotspots/views.py
from celery import shared_task
from rest_framework import serializers 
from django.db import IntegrityError
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

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from django.contrib.auth import authenticate
from pyrad.packet import AccessAccept, AccessReject
from .models import Hotspot

class HotspotAuthViewSet(ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='authenticate')
    def authenticate_user(self, request):
        """
        POST /hotspot-auth/authenticate/
        {
            "username": "...",
            "password": "...",
            "hotspot_ssid": "..."
        }
        """
        username = request.data.get('username')
        password = request.data.get('password')
        hotspot_ssid = request.data.get('hotspot_ssid')

        # Validate required fields
        if not all([username, password, hotspot_ssid]):
            return Response(
                {"error": "Missing required fields (username, password, hotspot_ssid)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            hotspot = Hotspot.objects.get(ssid=hotspot_ssid, is_active=True)
        except Hotspot.DoesNotExist:
            return Response(
                {"error": "Hotspot not found or inactive"},
                status=status.HTTP_404_NOT_FOUND
            )

        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Debug logging (optional)
        print(f"User: {user} (type={user.user_type})")
        print(f"Hotspot owner: {hotspot.owner} (type={hotspot.owner.user_type})")
        print(f"Hotspot owner.parent_reseller: {getattr(hotspot.owner, 'parent_reseller', None)}")
        print(f"User.parent_reseller: {getattr(user, 'parent_reseller', None)}")

        # Authorization check
        if not (
            user.is_superuser or
            user.user_type == 1 or  # Admin
            (user.user_type == 2 and hotspot.owner == user) or  # Reseller owns hotspot
            (user.user_type == 3 and hotspot.owner == user.parent_reseller)  # Customer's reseller owns hotspot
        ):
            return Response(
                {"error": "User not authorized for this hotspot"},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            "status": "access_granted",
            "message": "Authentication successful",
            "hotspot": hotspot.ssid,
            "user": user.username
        }, status=status.HTTP_200_OK)

class HotspotLocationViewSet(viewsets.ModelViewSet):
    serializer_class = HotspotLocationSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in [1, 2]:  # Admin or Reseller
            return HotspotLocation.objects.all()
        return HotspotLocation.objects.none()

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

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return HotspotLocation.objects.all()
        elif user.user_type == 1:  # Admin
            return HotspotLocation.objects.all()
        elif user.user_type == 2:
            return HotspotLocation.objects.filter(hotspot__owner=user)
        elif user.user_type == 3:
            return HotspotLocation.objects.filter(hotspot__owner__parent_reseller=user)
        return HotspotLocation.objects.none()


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

# @shared_task(bind=True)
# def control_hotspot_async(self, hotspot_id, action):
#     try:
#         from django.core.management import call_command
#         from io import StringIO
#         import json
        
#         # Capture command output
#         out = StringIO()
#         err = StringIO()
        
#         call_command(
#             'hotspot_control', 
#             action, 
#             f'--hotspot-id={hotspot_id}',
#             '--json',
#             stdout=out,
#             stderr=err
#         )
        
#         output = out.getvalue()
#         error_output = err.getvalue()
        
#         try:
#             return json.loads(output)
#         except json.JSONDecodeError:
#             return {
#                 'success': False,
#                 'error': f"Invalid JSON response: {output}",
#                 'raw_output': output,
#                 'error_output': error_output
#             }
            
#     except Exception as e:
#         return {
#             'success': False,
#             'error': f"Task execution failed: {str(e)}"
#         }

@shared_task(bind=True)
def control_hotspot_async(self, hotspot_id, action):
    try:
        from django.core.management import call_command
        from hotspots.models import Hotspot
        
        hotspot = Hotspot.objects.get(id=hotspot_id)
        
        # Capture command output
        from io import StringIO
        import sys
        from contextlib import redirect_stdout
        
        output = StringIO()
        with redirect_stdout(output):
            call_command(
                'hotspot_control', 
                action, 
                f'--hotspot-id={hotspot_id}'
            )
        
        # Verify the hotspot actually started
        if action == 'start':
            import time
            time.sleep(3)  # Give it time to start
            is_running = hotspot.get_status()
            if not is_running:
                raise Exception(f"Hotspot failed to start. Command output: {output.getvalue()}")
        
        return {
            'success': True,
            'action': action,
            'hotspot_id': hotspot_id,
            'ssid': hotspot.ssid,
            'output': output.getvalue(),
            'is_running': hotspot.get_status() if action == 'start' else False
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'hotspot_id': hotspot_id,
            'action': action
        }

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
    
    # def perform_create(self, serializer):
    #     try:
    #         hotspot = serializer.save(owner=self.request.user)
    #         print(f"Hotspot created: {hotspot.ssid}")
            
    #         try:
    #             # Start the hotspot and store the task ID
    #             task = control_hotspot_async.delay(hotspot.id, 'start')
    #             hotspot.current_task_id = task.id
    #             hotspot.save()
                
    #         except Exception as e:
    #             print(f"Failed to start hotspot async: {str(e)}")
    #             raise serializers.ValidationError(
    #                 {"error": f"Failed to start hotspot: {str(e)}"}
    #             )
                
    #     except IntegrityError as e:
    #         print(f"IntegrityError: {str(e)}")
    #         raise serializers.ValidationError(
    #             {"error": "You already have a hotspot with this SSID"}
    #         )
    #     except Exception as e:
    #         print(f"General Error: {str(e)}")
    #         hotspot.delete()
    #         raise serializers.ValidationError(
    #             {"error": f"Hotspot creation failed: {str(e)}"}
    #         )
    def perform_create(self, serializer):
        try:
            hotspot = serializer.save(owner=self.request.user)
            print(f"Hotspot created: {hotspot.ssid}")
            
            # Start the hotspot
            task = control_hotspot_async.delay(hotspot.id, 'start')
            hotspot.current_task_id = task.id
            print(f"Hotspot task id: {task.id}")
            
            # Wait briefly for initial status
            import time
            time.sleep(2)
            hotspot.is_active = hotspot.get_status()
            print(f"Hotspot status: {hotspot.get_status()}")
            hotspot.save()
            
        except IntegrityError as e:
            raise serializers.ValidationError(
                {"error": "Hotspot with this SSID already exists"}
            )
        except Exception as e:
            if 'hotspot' in locals():
                hotspot.delete()
            raise serializers.ValidationError(
                {"error": f"Failed to create hotspot: {str(e)}"}
            )
            
    def perform_destroy(self, instance):
        # Stop the hotspot asynchronously before deletion
        try:
            control_hotspot_async.delay(instance.id, 'stop')
        except Exception as e:
            raise serializers.ValidationError(
                f"Failed to stop hotspot: {str(e)}"
            )
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """Restart hotspot asynchronously"""
        hotspot = self.get_object()
        try:
            task = control_hotspot_async.delay(hotspot.id, 'restart')
            hotspot.current_task_id = task.id
            hotspot.save()
            
            return Response({
                'status': 'restarting',
                'message': f'Hotspot {hotspot.ssid} is being restarted',
                'task_id': task.id
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 
    
    @action(detail=True, methods=['get'])
    def task_status(self, request, pk=None):
        """Check status of an async hotspot task"""
        hotspot = self.get_object()
        task_id = request.query_params.get('task_id', hotspot.current_task_id)
        
        if not task_id:
            return Response(
                {"error": "No task ID provided and no active task found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task = control_hotspot_async.AsyncResult(task_id)
        
        response_data = {
            'ready': task.ready(),
            'status': task.status,
            'hotspot_id': hotspot.id,
            'ssid': hotspot.ssid
        }
        
        if task.ready():
            result = task.result
            response_data.update({
                'success': result.get('success'),
                'message': result.get('message'),
                'error': result.get('error'),
                'details': result.get('details')
            })
        
        return Response(response_data)

    # @action(detail=True, methods=['get'])
    # def status(self, request, pk=None):
    #     """Check hotspot operational status"""
    #     hotspot = self.get_object()
    #     return Response({
    #         'is_running': hotspot.get_status(),
    #         'ssid': hotspot.ssid,
    #         'interface': hotspot.interface
    #     })

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Check hotspot operational status with verification"""
        hotspot = self.get_object()
        
        # Get system status
        is_running = hotspot.get_status()
        
        # If DB says active but system says not running, correct the DB
        if hotspot.is_active and not is_running:
            hotspot.is_active = False
            hotspot.save()
        
        return Response({
            'is_running': is_running,
            'is_active': hotspot.is_active,  # DB status
            'ssid': hotspot.ssid,
            'interface': hotspot.interface,
            'last_status_check': timezone.now()
        })

    @action(detail=True, methods=['get'])
    def verify(self, request, pk=None):
        """Force verification of hotspot status"""
        hotspot = self.get_object()
        was_running = hotspot.is_active
        actual_status = hotspot.get_status()
        
        if was_running != actual_status:
            hotspot.is_active = actual_status
            hotspot.save()
            message = f"Status corrected from {was_running} to {actual_status}"
        else:
            message = "Status consistent"
        
        return Response({
            'was_running': was_running,
            'is_running': actual_status,
            'message': message,
            'corrected': was_running != actual_status
        })

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