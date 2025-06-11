import pytest
from datetime import date
from rest_framework import status
from django.urls import reverse
from analytics.models import DailyUsage, RevenueRecord

@pytest.mark.django_db
class TestDailyUsageViewSet:
    def test_unauthenticated_access(self, api_client):
        response = api_client.get(reverse('daily-usage-list'))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_sees_all_usage(self, api_client, admin_user, daily_usage):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse('daily-usage-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1

    def test_reseller_sees_their_customers_usage(self, api_client, reseller_user, customer_user, daily_usage):
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get(reverse('daily-usage-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['user'] == customer_user.id

    def test_customer_sees_only_their_usage(self, api_client, customer_user, daily_usage):
        another_user = customer_user.__class__.objects.create(
            username='othercustomer',
            user_type=3
        )
        DailyUsage.objects.create(
            user=another_user,
            hotspot=daily_usage.hotspot,
            date=date.today(),
            data_used=100
        )
        
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(reverse('daily-usage-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['user'] == customer_user.id

    def test_usage_detail_permissions(self, api_client, customer_user, daily_usage):
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(reverse('daily-usage-detail', args=[daily_usage.pk]))
        assert response.status_code == status.HTTP_200_OK

        another_user = customer_user.__class__.objects.create(
            username='othercustomer',
            user_type=3
        )
        another_usage = DailyUsage.objects.create(
            user=another_user,
            hotspot=daily_usage.hotspot,
            date=date.today(),
            data_used=100
        )
        response = api_client.get(reverse('daily-usage-detail', args=[another_usage.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRevenueRecordViewSet:
    def test_admin_sees_all_revenue(self, api_client, admin_user, revenue_record):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse('revenue-record-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1

    def test_reseller_sees_only_their_revenue(self, api_client, reseller_user, revenue_record):
        another_reseller = reseller_user.__class__.objects.create(
            username='otherreseller',
            user_type=2
        )
        RevenueRecord.objects.create(
            reseller=another_reseller,
            date=date.today(),
            total_sales=500.00,
            commissions_earned=30.0,
        )
        
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get(reverse('revenue-record-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['reseller'] == reseller_user.id

    def test_customer_cannot_access_revenue(self, api_client, customer_user):
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(reverse('revenue-record-list'))
        assert response.status_code == status.HTTP_403_FORBIDDEN
