import pytest
from rest_framework import status
from accounts.models import User
from accounts.enums import UserType
from tests.conftest_base import api_client, admin_user, reseller_user, customer_user

@pytest.mark.django_db
class TestUserViewSet:
    print("======== Running Accounts Views Tests ========")

    def test_unauthenticated_access(self, api_client):
        response = api_client.get('/api/users/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_sees_all_users(self, api_client, admin_user, reseller_user, customer_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/users/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 3  # Admin + reseller + customer

    def test_reseller_sees_only_their_customers(self, api_client, reseller_user, customer_user):
        # Create unrelated customer
        User.objects.create_user(
            username='unrelated',
            email='unrelated@example.com',
            password='pass123',
            user_type=UserType.CUSTOMER
        )
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get('/api/users/')
        assert response.status_code == status.HTTP_200_OK
        usernames = [u['username'] for u in response.data['data']]
        assert customer_user.username in usernames
        assert 'unrelated' not in usernames

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
            'user_type': UserType.CUSTOMER
        }
        response = api_client.post('/api/users/', data)
        if response.status_code != status.HTTP_201_CREATED:
            print("Creation failed with response data:", response.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username='newuser').exists()

    def test_user_creation_forbidden_for_non_admin(self, api_client, reseller_user):
        api_client.force_authenticate(user=reseller_user)
        data = {
            'username': 'illegaluser',
            'email': 'illegal@example.com',
            'password': 'pass123',
            'user_type': UserType.CUSTOMER
        }
        response = api_client.post('/api/users/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(username='illegaluser').exists()

    def test_user_detail_view(self, api_client, admin_user, customer_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(f'/api/users/{customer_user.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['username'] == customer_user.username

    def test_user_update_permissions(self, api_client, reseller_user, customer_user):
        # Reseller updates their customer
        api_client.force_authenticate(user=reseller_user)
        response = api_client.patch(f'/api/users/{customer_user.id}/', {'first_name': 'Updated'})
        print("Response data:", response.data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['first_name'] == 'Updated'

        # Customer tries to update reseller (should fail)
        api_client.force_authenticate(user=customer_user)
        response = api_client.patch(f'/api/users/{reseller_user.id}/', {'first_name': 'Hack'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_delete_by_admin(self, api_client, admin_user):
        user = User.objects.create_user(
            username='tobedeleted', email='del@example.com', password='pass123'
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f'/api/users/{user.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=user.id).exists()

    def test_user_delete_forbidden_for_non_admin(self, api_client, reseller_user, customer_user):
        api_client.force_authenticate(user=reseller_user)
        response = api_client.delete(f'/api/users/{customer_user.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert User.objects.filter(id=customer_user.id).exists()