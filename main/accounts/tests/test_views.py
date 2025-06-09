# accounts/test_views.py
import pytest
from rest_framework import status
from accounts.models import User
from accounts.enums import UserType

@pytest.mark.django_db
class TestUserViewSet:
    print("======== Running Accounts Views Tests ========")
    def test_unauthenticated_access(self, api_client):
        response = api_client.get('/api/users/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_sees_all_users(self, api_client, admin_user, customer_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/users/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 3  # Admin + customer

    def test_reseller_sees_only_their_customers(self, api_client, reseller_user, customer_user):
        # Create another customer not belonging to this reseller
        User.objects.create_user(
            username='othercustomer',
            email='other@example.com',
            password='testpass',
            user_type=3
        )
        
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get('/api/users/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1  # Only their customer
        assert response.data['data'][0]['username'] == customer_user.username

    def test_customer_sees_only_themselves(self, api_client, customer_user):
        api_client.force_authenticate(user=customer_user)
        response = api_client.get('/api/users/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['username'] == customer_user.username

    def test_user_creation_by_admin(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'testpass123',
            'user_type': 3
        }
        response = api_client.post('/api/users/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username='newuser').exists()

    def test_user_update_permissions(self, api_client, reseller_user, customer_user):
        # Reseller tries to update their customer
        api_client.force_authenticate(user=reseller_user)
        response = api_client.patch(
            f'/api/users/{customer_user.id}/',
            {'first_name': 'Updated'}
        )
        
        print("\n[Reseller updating customer]")
        print("Status code:", response.status_code)
        print("Response data:", response.data)
        assert response.status_code == status.HTTP_200_OK
        
        # Customer tries to update reseller (should fail)
        api_client.force_authenticate(user=customer_user)
        response = api_client.patch(
            f'/api/users/{reseller_user.id}/',
            {'first_name': 'ShouldFail'}
        )
        
        print("\n[Customer updating reseller]")
        print("Status code:", response.status_code)
        print("Response data:", response.data)
        assert response.status_code == status.HTTP_403_FORBIDDEN