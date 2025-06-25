# analytics/conftest.py

import pytest
from datetime import date
from tests.conftest_base import api_client, admin_user, reseller_user, customer_user
from hotspots.models import Hotspot, HotspotLocation
from analytics.models import DailyUsage, RevenueRecord

@pytest.fixture
def hotspot(customer_user):
    location = HotspotLocation.objects.create(
        name="Test Location",
        address="123 Main St",  
        latitude=0.0,
        longitude=0.0
    )
    return Hotspot.objects.create(
        ssid="TestSSID",  
        password="password123",
        owner=customer_user,
        location=location,
        hotspot_type="PUB",
        max_users=10,
        bandwidth_limit=20
    )

@pytest.fixture
def daily_usage(customer_user, hotspot):
    return DailyUsage.objects.create(
        user=customer_user,
        hotspot=hotspot,
        date=date.today(),
        data_used=500,
        session_count=10,
        duration_seconds=3600
    )

@pytest.fixture
def revenue_record(reseller_user):
    return RevenueRecord.objects.create(
        reseller=reseller_user,
        date=date.today(),
        total_sales=1000.00,
        commissions_earned=100.00,  
        new_customers=5
    )