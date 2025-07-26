# hotspots/serializers.py

from rest_framework import serializers
from .models import HotspotLocation, Hotspot, Session
import re

class HotspotLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotspotLocation
        fields = '__all__'


# class HotspotSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Hotspot
#         fields = '__all__'
#         read_only_fields = ['owner', 'created_at', 'updated_at']

class HotspotSerializer(serializers.ModelSerializer):
    task_id = serializers.SerializerMethodField()
    class Meta:
        model = Hotspot
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def validate_ssid(self, value):
        """Validate SSID format"""
        if len(value) > 32:
            raise serializers.ValidationError("SSID cannot exceed 32 characters")
        if not re.match(r'^[a-zA-Z0-9 _-]+$', value):
            raise serializers.ValidationError("SSID contains invalid characters")
        return value

    def validate_password(self, value):
        """Validate WiFi password"""
        if len(value) < 8 or len(value) > 63:
            raise serializers.ValidationError(
                "Password must be between 8 and 63 characters"
            )
        return value

    def get_task_id(self, obj):
        return obj.current_task_id


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'
        read_only_fields = ['user', 'start_time', 'created_at', 'updated_at']
