# # analytics/test_views.py
import pytest
from datetime import date
from rest_framework import status
from django.urls import reverse
from analytics.models import DailyUsage, RevenueRecord
from tests.conftest_base import api_client, admin_user, reseller_user, customer_user

@pytest.mark.django_db
class TestDailyUsageViewSet:
    def test_unauthenticated_access(self, api_client):
        response = api_client.get(reverse('daily-usage-list'))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_sees_all_usage(self, api_client, admin_user, daily_usage):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse('daily-usage-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) >= 1

    def test_reseller_sees_their_customers_usage(self, api_client, reseller_user, customer_user, daily_usage):
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get(reverse('daily-usage-list'))
        assert response.status_code == status.HTTP_200_OK
        assert any(usage['user'] == customer_user.id for usage in response.data['data'])

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
        assert all(usage['user'] == customer_user.id for usage in response.data['data'])

    def test_usage_detail_permissions(self, api_client, customer_user, daily_usage):
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(reverse('daily-usage-detail', args=[daily_usage.pk]))
        assert response.status_code == status.HTTP_200_OK

        another_user = customer_user.__class__.objects.create(
            username='othercustomer2',
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
        
    def test_reseller_cannot_access_unrelated_customer_usage(self, api_client, reseller_user, daily_usage):
        unrelated_reseller = reseller_user.__class__.objects.create(username="otherreseller", user_type=2)
        daily_usage.user.parent_reseller_id = unrelated_reseller.id
        daily_usage.user.save()

        api_client.force_authenticate(user=reseller_user)
        response = api_client.get(reverse('daily-usage-detail', args=[daily_usage.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # Create DailyUsage
    def test_create_daily_usage(self, api_client, admin_user, customer_user, hotspot):
        api_client.force_authenticate(user=admin_user)
        data = {
            "user": customer_user.id,
            "hotspot": hotspot.id,
            "date": str(date.today()),
            "data_used": 150
        }
        response = api_client.post(reverse('daily-usage-list'), data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['data_used'] == 150
    
    # Should be rejected by the view
    def test_customer_cannot_create_daily_usage(self, api_client, customer_user, hotspot):
        api_client.force_authenticate(user=customer_user)
        data = {
            "user": customer_user.id,
            "hotspot": hotspot.id,
            "date": str(date.today()),
            "data_used": 150
        }
        response = api_client.post(reverse('daily-usage-list'), data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cannot_create_duplicate_daily_usage(self, api_client, admin_user, daily_usage):
        api_client.force_authenticate(user=admin_user)
        data = {
            "user": daily_usage.user.id,
            "hotspot": daily_usage.hotspot.id,
            "date": str(daily_usage.date),
            "data_used": 123
        }
        response = api_client.post(reverse('daily-usage-list'), data)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
        
    def test_reject_negative_data_used(self, api_client, admin_user, customer_user, hotspot):
        api_client.force_authenticate(user=admin_user)
        data = {
            "user": customer_user.id,
            "hotspot": hotspot.id,
            "date": str(date.today()),
            "data_used": -10
        }
        response = api_client.post(reverse('daily-usage-list'), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_admin_can_filter_usage_by_user(self, api_client, admin_user, daily_usage):
        api_client.force_authenticate(user=admin_user)
        url = reverse('daily-usage-list') + f"?user={daily_usage.user.id}"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert all(u['user'] == daily_usage.user.id for u in response.data['data'])

    def test_reseller_cannot_create_daily_usage_for_others(self, api_client, reseller_user, customer_user, hotspot):
        # Ensure the customer is not owned by the reseller
        customer_user.parent_reseller_id = None  # Or some other unrelated reseller id
        customer_user.save()

        api_client.force_authenticate(user=reseller_user)
        data = {
            "user": customer_user.id,
            "hotspot": hotspot.id,
            "date": str(date.today()),
            "data_used": 150
        }

        response = api_client.post(reverse('daily-usage-list'), data)

        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    def test_reseller_can_create_daily_usage_for_their_customer(self, api_client, reseller_user, customer_user, hotspot):
        customer_user.parent_reseller_id = reseller_user.id
        customer_user.save()

        api_client.force_authenticate(user=reseller_user)
        data = {
            "user": customer_user.id,
            "hotspot": hotspot.id,
            "date": str(date.today()),
            "data_used": 150
        }

        response = api_client.post(reverse('daily-usage-list'), data)
        assert response.status_code == status.HTTP_201_CREATED

    # Update DailyUsage
    def test_update_daily_usage(self, api_client, admin_user, daily_usage):
        api_client.force_authenticate(user=admin_user)
        data = {
            "data_used": 999
        }
        response = api_client.patch(reverse('daily-usage-detail', args=[daily_usage.pk]), data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['data_used'] == 999

    def test_customer_cannot_update_others_daily_usage(self, api_client, customer_user, daily_usage):
        another_user = customer_user.__class__.objects.create(
            username='othercustomer3',
            user_type=3
        )
        another_usage = DailyUsage.objects.create(
            user=another_user,
            hotspot=daily_usage.hotspot,
            date=date.today(),
            data_used=100
        )
        api_client.force_authenticate(user=customer_user)
        data = {
            "data_used": 777
        }
        response = api_client.patch(reverse('daily-usage-detail', args=[another_usage.pk]), data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # Delete DailyUsage
    def test_delete_daily_usage(self, api_client, admin_user, daily_usage):
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(reverse('daily-usage-detail', args=[daily_usage.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_customer_cannot_delete_others_daily_usage(self, api_client, customer_user, daily_usage):
        another_user = customer_user.__class__.objects.create(
            username='othercustomer4',
            user_type=3
        )
        another_usage = DailyUsage.objects.create(
            user=another_user,
            hotspot=daily_usage.hotspot,
            date=date.today(),
            data_used=100
        )
        api_client.force_authenticate(user=customer_user)
        response = api_client.delete(reverse('daily-usage-detail', args=[another_usage.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRevenueRecordViewSet:
    def test_admin_sees_all_revenue(self, api_client, admin_user, revenue_record):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse('revenue-record-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) >= 1

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
        assert all(record['reseller'] == reseller_user.id for record in response.data['data'])

    def test_customer_cannot_access_revenue(self, api_client, customer_user):
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(reverse('revenue-record-list'))
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
    def test_reseller_cannot_access_others_revenue_detail(self, api_client, reseller_user, revenue_record):
        another_reseller = reseller_user.__class__.objects.create(username='r2', user_type=2)
        revenue_record.reseller = another_reseller
        revenue_record.save()
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get(reverse('revenue-record-detail', args=[revenue_record.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # Create RevenueRecord
    def test_admin_can_create_revenue_record(self, api_client, admin_user, reseller_user):
        api_client.force_authenticate(user=admin_user)
        data = {
            "reseller": reseller_user.id,
            "date": str(date.today()),
            "total_sales": 1000.00,
            "commissions_earned": 100.00,
        }
        response = api_client.post(reverse('revenue-record-list'), data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['total_sales'] == 1000.00

    def test_reseller_cannot_create_revenue_record(self, api_client, reseller_user):
        api_client.force_authenticate(user=reseller_user)
        data = {
            "reseller": reseller_user.id,
            "date": str(date.today()),
            "total_sales": 1000.00,
            "commissions_earned": 100.00,
        }
        response = api_client.post(reverse('revenue-record-list'), data)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    # Update RevenueRecord
    def test_admin_can_update_revenue_record(self, api_client, admin_user, revenue_record):
        api_client.force_authenticate(user=admin_user)
        data = {
            "total_sales": 2000.00
        }
        response = api_client.patch(reverse('revenue-record-detail', args=[revenue_record.pk]), data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total_sales'] == 2000.00

    def test_reseller_cannot_update_revenue_record(self, api_client, reseller_user, revenue_record):
        api_client.force_authenticate(user=reseller_user)
        data = {
            "total_sales": 2000.00
        }
        response = api_client.patch(reverse('revenue-record-detail', args=[revenue_record.pk]), data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # Delete RevenueRecord
    def test_admin_can_delete_revenue_record(self, api_client, admin_user, revenue_record):
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(reverse('revenue-record-detail', args=[revenue_record.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_reseller_cannot_delete_revenue_record(self, api_client, reseller_user, revenue_record):
        api_client.force_authenticate(user=reseller_user)
        response = api_client.delete(reverse('revenue-record-detail', args=[revenue_record.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN