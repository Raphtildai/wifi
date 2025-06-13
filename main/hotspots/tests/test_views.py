# hotspots/test_views.py

import pytest
from django.urls import reverse
from rest_framework import status
from hotspots.models import HotspotLocation, Hotspot, Session


@pytest.mark.django_db
class TestHotspotViews:

    # --------------------- LOCATION TESTS ---------------------

    def test_create_hotspot_location_as_admin(self, admin_user, api_client):
        api_client.force_authenticate(user=admin_user)
        data = {"name": "Admin Location", "address": "Main St", "latitude": 1.2, "longitude": 2.2}
        response = api_client.post('/api/locations/', data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_hotspot_location_as_non_admin_denied(self, reseller_user, customer_user, api_client):
        for user in [reseller_user, customer_user]:
            api_client.force_authenticate(user=user)
            response = api_client.post('/api/locations/', {"name": "Invalid", "address": "N/A"})
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_location_as_admin(self, admin_user, api_client, location):
        api_client.force_authenticate(user=admin_user)
        Hotspot.objects.filter(location=location).delete()
        response = api_client.delete(f'/api/locations/{location.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_location_as_non_admin_denied(self, reseller_user, customer_user, api_client, location):
        for user in [reseller_user, customer_user]:
            api_client.force_authenticate(user=user)
            response = api_client.delete(f'/api/locations/{location.id}/')
            assert response.status_code == status.HTTP_403_FORBIDDEN

    # --------------------- HOTSPOT TESTS ---------------------

    def test_create_hotspot_as_reseller(self, reseller_user, api_client, location):
        api_client.force_authenticate(user=reseller_user)
        data = {
            "ssid": "ResellerNet", "password": "pass", "location": location.id,
            "hotspot_type": "COM", "max_users": 10, "bandwidth_limit": 50
        }
        response = api_client.post('/api/hotspots/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_hotspot_as_customer_denied(self, customer_user, api_client, location):
        api_client.force_authenticate(user=customer_user)
        data = {
            "ssid": "InvalidNet", "password": "bad", "location": location.id,
            "hotspot_type": "COM", "max_users": 5, "bandwidth_limit": 10
        }
        response = api_client.post('/api/hotspots/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_hotspot_as_admin(self, admin_user, api_client, reseller_hotspot):
        api_client.force_authenticate(user=admin_user)
        url = f'/api/hotspots/{reseller_hotspot.id}/'
        response = api_client.put(url, {
            "ssid": "AdminUpdated", "password": "adminpass", "location": reseller_hotspot.location.id,
            "hotspot_type": "PRI", "max_users": 20, "bandwidth_limit": 100, "owner": reseller_hotspot.owner.id
        })
        assert response.status_code == status.HTTP_200_OK

    def test_update_hotspot_invalid_data(self, admin_user, api_client, reseller_hotspot):
        api_client.force_authenticate(user=admin_user)
        url = f'/api/hotspots/{reseller_hotspot.id}/'
        response = api_client.put(url, {"ssid": ""})  # Missing fields
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_hotspot_as_admin(self, admin_user, api_client, reseller_hotspot):
        api_client.force_authenticate(user=admin_user)
        url = f'/api/hotspots/{reseller_hotspot.id}/'
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_hotspot_as_non_owner_denied(self, customer_user, api_client, admin_hotspot):
        api_client.force_authenticate(user=customer_user)
        url = f'/api/hotspots/{admin_hotspot.id}/'
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # --------------------- SESSION TESTS ---------------------

    def test_create_session_as_customer(self, customer_user, api_client, admin_hotspot):
        api_client.force_authenticate(user=customer_user)
        data = {
            "hotspot": admin_hotspot.id,
            "ip_address": "192.168.1.99",
            "mac_address": "FF:EE:DD:CC:BB:AA"
        }
        response = api_client.post('/api/sessions/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['user'] == customer_user.id

    def test_create_session_invalid_data(self, customer_user, api_client):
        api_client.force_authenticate(user=customer_user)
        response = api_client.post('/api/sessions/', {"ip_address": "1.1.1.1"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


    def test_update_session_as_admin(self, admin_user, api_client, customer_session):
        api_client.force_authenticate(user=admin_user)
        url = f'/api/sessions/{customer_session.id}/'
        response = api_client.put(url, {
            "hotspot": customer_session.hotspot.id,
            "ip_address": "1.1.1.1",
            "mac_address": customer_session.mac_address,
            "is_active": False
        })
        assert response.status_code == status.HTTP_200_OK

    def test_delete_session_as_admin(self, admin_user, api_client, reseller_session):
        api_client.force_authenticate(user=admin_user)
        url = f'/api/sessions/{reseller_session.id}/'
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_get_session_detail_as_owner(self, customer_user, api_client, customer_session):
        api_client.force_authenticate(user=customer_user)
        url = f'/api/sessions/{customer_session.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_get_session_detail_as_owner_allowed(self, api_client, customer_user, customer_session):
        api_client.force_authenticate(user=customer_user)
        url = f'/api/sessions/{customer_session.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_session_detail_as_reseller_allowed(self, reseller_user, api_client, customer_session):
        api_client.force_authenticate(user=reseller_user)
        url = f'/api/sessions/{customer_session.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
    def test_get_session_detail_as_non_owner_denied(self, django_user_model, api_client, customer_session):
        random_user = django_user_model.objects.create_user(username='random', password='pass1234')
        api_client.force_authenticate(user=random_user)
        url = f'/api/sessions/{customer_session.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_sessions_by_active(self, admin_user, api_client, admin_hotspot):
        api_client.force_authenticate(user=admin_user)
        Session.objects.create(
            user=admin_user, hotspot=admin_hotspot,
            ip_address="192.168.1.50", mac_address="22:33:44:55:66:77", is_active=False
        )
        url = '/api/sessions/?is_active=False'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert all(not s['is_active'] for s in response.data['data'])

    def test_non_admin_cannot_access_location_list(self, reseller_user, api_client):
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get('/api/locations/')
        assert response.status_code == status.HTTP_200_OK