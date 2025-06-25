# tests/hotspots/conftest.py
import pytest
from hotspots.models import HotspotLocation, Hotspot, Session
from tests.conftest_base import api_client, admin_user, reseller_user, customer_user

@pytest.fixture
def location(db):
    return HotspotLocation.objects.create(
        name="Base Location",
        address="123 Admin St",
        latitude=1.0,
        longitude=36.0
    )

@pytest.fixture
def admin_hotspot(db, admin_user, location):
    return Hotspot.objects.create(
        ssid="AdminNet",
        password="adminpass",
        location=location,
        hotspot_type="PUB",
        max_users=25,
        bandwidth_limit=100,
        owner=admin_user
    )

@pytest.fixture
def reseller_hotspot(db, reseller_user, location):
    return Hotspot.objects.create(
        ssid="ResellerNet",
        password="resellerpass",
        location=location,
        hotspot_type="COM",
        max_users=15,
        bandwidth_limit=50,
        owner=reseller_user
    )

@pytest.fixture
def admin_session(db, admin_user, admin_hotspot):
    return Session.objects.create(
        user=admin_user,
        hotspot=admin_hotspot,
        ip_address="192.168.1.10",
        mac_address="AA:BB:CC:DD:EE:FF"
    )

@pytest.fixture
def reseller_session(db, reseller_user, reseller_hotspot):
    return Session.objects.create(
        user=reseller_user,
        hotspot=reseller_hotspot,
        ip_address="192.168.1.20",
        mac_address="00:11:22:33:44:55"
    )

@pytest.fixture
def customer_session(db, customer_user, admin_hotspot):
    return Session.objects.create(
        user=customer_user,
        hotspot=admin_hotspot,
        ip_address="192.168.1.30",
        mac_address="11:22:33:44:55:66"
    )