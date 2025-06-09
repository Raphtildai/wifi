from rest_framework import serializers
from .models import DailyUsage, RevenueRecord

class DailyUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyUsage
        fields = ['id', 'user', 'hotspot', 'date', 'data_used', 'session_count', 'duration_seconds']


class RevenueRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueRecord
        fields = ['id', 'reseller', 'date', 'total_sales', 'commissions_earned', 'new_customers']