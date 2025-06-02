# hotspots/serializers.py

from rest_framework import serializers
from .models import HotspotLocation, Hotspot, Session

class HotspotLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotspotLocation
        fields = '__all__'


class HotspotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotspot
        fields = '__all__'
        read_only_fields = ['owner', 'created_at', 'updated_at']


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'
        read_only_fields = ['user', 'start_time', 'created_at', 'updated_at']
