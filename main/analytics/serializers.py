from rest_framework import serializers
from .models import DailyUsage, RevenueRecord

class DailyUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyUsage
        fields = ['id', 'user', 'hotspot', 'date', 'data_used', 'session_count', 'duration_seconds']


class RevenueRecordSerializer(serializers.ModelSerializer):
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Convert total_sales string to float for consistency
        if 'total_sales' in ret:
            ret['total_sales'] = float(ret['total_sales'])
        return ret
    class Meta:
        model = RevenueRecord
        fields = ['id', 'reseller', 'date', 'total_sales', 'commissions_earned', 'new_customers']