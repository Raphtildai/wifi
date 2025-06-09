# accounts/test_model.py
import pytest
from django.core.exceptions import ValidationError
from accounts.models import User, UserProfile
from accounts.enums import UserType


@pytest.mark.django_db
class TestUserModel:
    print("======== Running Accounts Model Tests ========")
    def test_user_creation(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.pk is not None
        assert not user.is_superuser
        assert user.user_type == 3  # Default to customer

    def test_superuser_creation(self):
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            user_type=1
        )
        assert admin.user_type == 1  # Admin
        assert admin.is_superuser
        assert admin.is_staff 

    def test_user_type_validation(self):
        user = User(username='test', email='test@test.com')
        with pytest.raises(ValidationError):
            user.user_type = 4  # Invalid choice
            user.full_clean()

    def test_user_str_representation(self):
        user = User.objects.create_user(
            username='testuser',
            first_name='John',
            last_name='Doe',
            user_type=2
        )
        assert str(user) == "John Doe (Reseller)"

    def test_user_properties(self, admin_user, reseller_user, customer_user):
        assert admin_user.user_type == 1
        assert reseller_user.user_type == 2
        assert customer_user.user_type == 3
        assert not customer_user.user_type == 1

@pytest.mark.django_db
class TestUserProfileModel:
    def test_profile_creation(self, reseller_user):
        profile = UserProfile.objects.get(user=reseller_user)
        assert profile.company_name == "Test Reseller"
        assert profile.commission_rate == 10.00

    def test_profile_str_representation(self, reseller_user):
        profile = reseller_user.profile
        assert str(profile) == f"Profile of {reseller_user.username}"