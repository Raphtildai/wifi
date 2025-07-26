# # hotspots/tests/test_ap_connectivity.py
import pytest
from rest_framework.test import APIClient
from tests.conftest_base import api_client, customer_user, inactive_hotspot, test_hotspot

@pytest.mark.django_db
def test_successful_auth(customer_user, test_hotspot):
    client = APIClient()

    # Step 1: Get auth token
    token_response = client.post('/api-token-auth/', {
        'username': customer_user.username,
        'password': 'testpass123'
    }, format='json')

    assert token_response.status_code == 200
    token = token_response.data.get('access')
    assert token is not None

    # Step 2: Use token for authentication
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    response = client.post('/api/hotspot-auth/authenticate/', {
        'username': customer_user.username,
        'password': 'testpass123',
        'hotspot_ssid': test_hotspot.ssid
    }, format='json')

    assert response.status_code == 200
    assert response.json().get('status') == 'access_granted'


@pytest.mark.django_db
def test_inactive_hotspot(customer_user, inactive_hotspot):
    client = APIClient()

    token_response = client.post('/api-token-auth/', {
        'username': customer_user.username,
        'password': 'testpass123'
    }, format='json')

    assert token_response.status_code == 200
    token = token_response.data.get('access')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    response = client.post('/api/hotspot-auth/authenticate/', {
        'username': customer_user.username,
        'password': 'testpass123',
        'hotspot_ssid': inactive_hotspot.ssid
    }, format='json')

    assert response.status_code == 403


@pytest.mark.django_db
def test_nonexistent_hotspot(customer_user):
    client = APIClient()

    token_response = client.post('/api-token-auth/', {
        'username': customer_user.username,
        'password': 'testpass123'
    }, format='json')

    assert token_response.status_code == 200
    token = token_response.data.get('access')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    response = client.post('/api/hotspot-auth/authenticate/', {
        'username': customer_user.username,
        'password': 'testpass123',
        'hotspot_ssid': 'nonexistent'
    }, format='json')

    assert response.status_code == 404


@pytest.mark.django_db
def test_admin_access(admin_user, test_hotspot):
    client = APIClient()

    token_response = client.post('/api-token-auth/', {
        'username': admin_user.username,
        'password': 'testpass123'  
    }, format='json')

    assert token_response.status_code == 200
    token = token_response.data.get('access')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    response = client.post('/api/hotspot-auth/authenticate/', {
        'username': admin_user.username,
        'password': 'testpass123',
        'hotspot_ssid': test_hotspot.ssid
    }, format='json')

    assert response.status_code == 200

# import pytest
# from hotspots.models import Hotspot
# from tests.conftest_base import api_client, customer_user, admin_user

# @pytest.mark.django_db
# def test_successful_auth(api_client, customer_user, test_hotspot):
#     # Authenticate client first
#     api_client.force_authenticate(user=customer_user)
    
#     response = api_client.post('/api/hotspot-auth/authenticate/', {
#         'username': customer_user.username,
#         'password': 'testpass123',
#         'hotspot_ssid': test_hotspot.ssid
#     }, content_type='application/json')

#     assert response.status_code == 200
#     assert response.json().get('status') == 'access_granted'

# @pytest.mark.django_db
# def test_inactive_hotspot(api_client, inactive_hotspot, customer_user):
#     # Authenticate client first
#     api_client.force_authenticate(user=customer_user)
#     response = api_client.post('/api/hotspot-auth/authenticate/', {
#         'username': customer_user.username,
#         'password': 'testpass123',
#         'hotspot_ssid': inactive_hotspot.ssid
#     }, content_type='application/json')
    
#     assert response.status_code == 403

# @pytest.mark.django_db
# def test_nonexistent_hotspot(api_client, customer_user):
#     api_client.force_authenticate(user=customer_user)  # Authenticate
#     response = api_client.post('/api/hotspot-auth/authenticate/', {
#         'hotspot_ssid': 'nonexistent',
#         'username': customer_user.username,
#         'password': 'testpass123',
#     }, content_type='application/json')
#     assert response.status_code == 404

# @pytest.mark.django_db
# def test_admin_access(api_client, admin_user, test_hotspot):
#     """Test admin user can access any hotspot"""
#     api_client.force_login(admin_user)
#     response = api_client.post('/api/hotspot-auth/authenticate/', {
#         'username': admin_user.username,
#         'password': admin_user.password,
#         'hotspot_ssid': test_hotspot.ssid
#     }, content_type='application/json')    
#     assert response.status_code == 200