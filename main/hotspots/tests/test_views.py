# hotspots/tests/test_views.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from hotspots.models import HotspotLocation, Hotspot, Session

User = get_user_model()


class HotspotExtendedTests(APITestCase):
    print("======== Running HotSpots Views Tests ========")
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='pass', user_type=1)
        self.reseller = User.objects.create_user(username='reseller', password='pass', user_type=2)
        self.customer = User.objects.create_user(username='customer', password='pass', user_type=3)

        self.admin_token = Token.objects.create(user=self.admin)
        self.reseller_token = Token.objects.create(user=self.reseller)
        self.customer_token = Token.objects.create(user=self.customer)

        self.location = HotspotLocation.objects.create(
            name="Base Location", address="123 Admin St", latitude=1.0, longitude=36.0
        )
        self.hotspot = Hotspot.objects.create(
            ssid="AdminNet", password="adminpass", location=self.location,
            hotspot_type="PUB", max_users=25, bandwidth_limit=100, owner=self.admin
        )
        self.session = Session.objects.create(
            user=self.admin, hotspot=self.hotspot,
            ip_address="192.168.1.10", mac_address="AA:BB:CC:DD:EE:FF"
        )

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)

    # --------------------
    # Update Tests
    # --------------------
    def test_update_hotspot_location(self):
        url = reverse('hotspotlocation-detail', args=[self.location.id])
        data = {"name": "Updated Name", "address": "New Address", "latitude": 0.5, "longitude": 36.5}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Name")

    def test_update_hotspot(self):
        url = reverse('hotspot-detail', args=[self.hotspot.id])
        data = {
            "ssid": "UpdatedSSID",
            "password": "newpass",
            "location": self.location.id,
            "hotspot_type": "COM",
            "max_users": 30,
            "bandwidth_limit": 75,
            "owner": self.admin.id  
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ssid"], "UpdatedSSID")

    def test_update_session_end_time(self):
        url = reverse('session-detail', args=[self.session.id])
        data = {
            "hotspot": self.hotspot.id,
            "ip_address": "192.168.1.10",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "is_active": False,
            "end_time": "2025-06-02T20:00:00Z"
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_active"])

    # --------------------
    # Delete Tests
    # --------------------
    def test_delete_hotspot_location(self):
        # First delete all hotspots related to the location
        Hotspot.objects.filter(location=self.location).delete()
        
        url = reverse('hotspotlocation-detail', args=[self.location.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_hotspot(self):
        url = reverse('hotspot-detail', args=[self.hotspot.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Hotspot.objects.filter(id=self.hotspot.id).exists())

    def test_delete_session(self):
        url = reverse('session-detail', args=[self.session.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Session.objects.filter(id=self.session.id).exists())

    # --------------------
    # Filter Tests
    # --------------------
    def test_filter_hotspots_by_type(self):
        Hotspot.objects.create(
            ssid="PrivateNet", password="1234", location=self.location,
            hotspot_type="PRI", max_users=5, bandwidth_limit=10, owner=self.admin
        )
        response = self.client.get(reverse('hotspot-list') + "?hotspot_type=PRI")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(h["hotspot_type"] == "PRI" for h in response.data))

    def test_filter_sessions_by_active(self):
        Session.objects.create(
            user=self.admin, hotspot=self.hotspot,
            ip_address="192.168.1.20", mac_address="00:11:22:33:44:55", is_active=False
        )
        response = self.client.get(reverse('session-list') + "?is_active=False")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(not s["is_active"] for s in response.data))
