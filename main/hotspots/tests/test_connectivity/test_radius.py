# hotspots/tests/test_radius.py
from django.test import TestCase
from hotspots.radius.auth import radius_authenticate
from pyrad.packet import AccessAccept, AccessReject
from django.contrib.auth import get_user_model
from django.utils import timezone
from billing.models import Subscription, Plan

User = get_user_model()

class RadiusAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            is_active=True,
            user_type=3,  # CUSTOMER
            credit=0.00
        )
        cls.plan = Plan.objects.create(
            name='Test Plan',
            price=9.99,
            duration_days=30
        )

    def test_valid_auth_with_subscription(self):
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
            is_active=True
        )
        result = radius_authenticate('testuser', 'testpass')
        self.assertEqual(result, AccessAccept)  # Compare with constant

    def test_valid_auth_with_credit(self):
        self.user.credit = 50.00
        self.user.save()
        result = radius_authenticate('testuser', 'testpass')
        self.assertEqual(result, AccessAccept)

    def test_invalid_auth_no_subscription_or_credit(self):
        result = radius_authenticate('testuser', 'testpass')
        self.assertEqual(result, AccessReject)

    def test_invalid_credentials(self):
        result = radius_authenticate('wrong', 'credentials')
        self.assertEqual(result, AccessReject)

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        result = radius_authenticate('testuser', 'testpass')
        self.assertEqual(result, AccessReject)

    def test_radius_constants(self):
        """Verify pyrad constants are the expected values"""
        self.assertEqual(AccessAccept, 2)
        self.assertEqual(AccessReject, 3)


# import pytest
# from django.test import TestCase
# from hotspots.radius.auth import radius_authenticate
# from pyrad.packet import AccessAccept, AccessReject
# from django.contrib.auth import get_user_model
# from django.utils import timezone
# from billing.models import Subscription, Plan

# User = get_user_model()

# @pytest.mark.django_db
# class TestRadiusAuth:
#     @classmethod
#     def setUpTestData(cls):
#         # Create test plans
#         cls.plan = Plan.objects.create(
#             name='Premium Plan',
#             price=19.99,
#             duration_days=30,
#         )
#         cls.basic_plan = Plan.objects.create(
#             name='Basic Plan',
#             price=4.99,
#             duration_days=7,
#         )
        
#         # Create test user
#         cls.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123',
#             user_type='CUSTOMER'
#         )

#     def test_premium_subscription_access(self):
#         """Test premium users get full access with proper attributes"""
#         Subscription.objects.create(
#             user=self.user,
#             plan=self.plan,
#             start_date=timezone.now(),
#             end_date=timezone.now() + timezone.timedelta(days=30),
#             is_active=True
#         )
        
#         result = radius_authenticate(self.user.username, self.user.password)
#         assert result.code == AccessAccept
#         assert result.reply_attributes['Filter-Id'] == 'PREMIUM_ACCESS'
#         assert result.reply_attributes['Mikrotik-Rate-Limit'] == '100M/100M'

#     def test_basic_subscription_access(self):
#         """Test basic tier gets restricted bandwidth"""
#         Subscription.objects.create(
#             user=self.user,
#             plan=self.basic_plan,
#             start_date=timezone.now(),
#             end_date=timezone.now() + timezone.timedelta(days=7),
#             is_active=True
#         )
        
#         result = radius_authenticate(self.user.username, self.user.password)
#         assert result.code == AccessAccept
#         assert result.reply_attributes['Filter-Id'] == 'BASIC_ACCESS'
#         assert result.reply_attributes['Mikrotik-Rate-Limit'] == '5M/5M'

#     def test_connect_but_no_internet(self):
#         """Test users can connect but get walled garden access"""
#         result = radius_authenticate(self.user.username, self.user.password)
#         assert result.code == AccessAccept
#         assert result.reply_attributes['Filter-Id'] == 'WALLED_GARDEN'
#         assert 'Session-Timeout' in result.reply_attributes

#     def test_credit_based_access(self):
#         """Test users with credit get appropriate access"""
#         self.user.credit = 10.00
#         self.user.save()
        
#         result = radius_authenticate(self.user.username, self.user.password)
#         assert result.code == AccessAccept
#         assert result.reply_attributes['Filter-Id'] == 'PAYG_ACCESS'
#         assert 'Session-Timeout' in result.reply_attributes

#     def test_invalid_credentials(self):
#         result = radius_authenticate('wrong', 'credentials')
#         assert result.code == AccessReject

#     def test_inactive_user(self):
#         self.user.is_active = False
#         self.user.save()
#         result = radius_authenticate(self.user.username, self.user.password)
#         assert result.code == AccessReject