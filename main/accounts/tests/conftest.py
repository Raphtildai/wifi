# accounts/conftest.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from accounts.models import UserProfile
from accounts.enums import UserType

User = get_user_model()

# Return API client
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