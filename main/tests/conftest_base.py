# tests/conftest_base.py

import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from hotspots.models import Hotspot, HotspotLocation
from accounts.enums import UserType
from accounts.models import UserProfile

User = get_user_model()

# Shared helpers

# def create_user(username, email, password, user_type, parent_reseller=None):
#     return User.objects.create_user(
#         username=username,
#         email=email,
#         password=password,
#         user_type=user_type,
#         parent_reseller=parent_reseller
#     )
def create_user(username, email=None, password=None, user_type=None, parent_reseller=None, **kwargs):
    """Helper to create users with consistent defaults"""
    email = email or f"{username}@example.com"
    password = password or f"{username}_pass123"
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
        user_type=user_type,
        parent_reseller=parent_reseller,
        **kwargs
    )

# For Hotspot
def create_hotspot(owner, location=None, **kwargs):
    """Helper to create hotspots with consistent defaults"""
    if location is None:
        location = HotspotLocation.objects.create(
            name="Test Location",
            address="123 Test St",
            latitude=0.0,
            longitude=0.0
        )
    return Hotspot.objects.create(
        owner=owner,
        location=location,
        ssid=kwargs.get('ssid', 'TestHotspot'),
        password=kwargs.get('password', 'testpassword'),
        hotspot_type=kwargs.get('hotspot_type', 'PUB'),
        max_users=kwargs.get('max_users', 10),
        bandwidth_limit=kwargs.get('bandwidth_limit', 10),
        is_active=kwargs.get('is_active', True)
    )

def create_profile_for_reseller(user):
    return UserProfile.objects.create(user=user, company_name="Test Reseller")

# Shared base fixtures

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='testpass123',
        user_type=UserType.ADMIN
    )

@pytest.fixture
def reseller_user():
    user = User.objects.create_user(
        username='reseller',
        email='reseller@example.com',
        password='testpass123',
        user_type=UserType.RESELLER
    )
    UserProfile.objects.create(user=user, company_name="Test Reseller")
    return user

@pytest.fixture
def customer_user(reseller_user):
    user = User.objects.create_user(
        username='customer',
        email='customer@example.com',
        password='testpass123',
        user_type=UserType.CUSTOMER,
        parent_reseller=reseller_user
    )
    return user

@pytest.fixture
def test_location():
    return HotspotLocation.objects.create(
        name="Test Location",
        address="123 Test St",
        latitude=0.0,
        longitude=0.0
    )

@pytest.fixture
def test_hotspot(reseller_user, test_location):
    return create_hotspot(
        owner=reseller_user,
        location=test_location
    )

@pytest.fixture
def inactive_hotspot(reseller_user, test_location):
    return create_hotspot(
        owner=reseller_user,
        location=test_location,
        ssid="InactiveHotspot",
        is_active=False
    )

@pytest.fixture
def auth_user(db):
    return create_user(
        username='valid_user',
        email='valid@example.com',
        password='testpass123',
        user_type=UserType.CUSTOMER
    )

@pytest.fixture
def hotspot_user(admin_user, test_hotspot):
    user = create_user(
        username='valid_user',
        password='testpass123',
        email='valid_user@example.com',
        user_type=UserType.CUSTOMER,
        parent_reseller=reseller_user
    )
    test_hotspot.allowed_users.add(user)  # if you're restricting hotspot access
    return user

@pytest.fixture
def authenticated_client(api_client, auth_user):
    api_client.force_authenticate(user=auth_user)
    return api_client

@pytest.fixture
def reseller_client(api_client, reseller_user):
    api_client.force_authenticate(user=reseller_user)
    return api_client
