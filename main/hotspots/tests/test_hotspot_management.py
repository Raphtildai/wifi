# hotspots/tests/test_hotspot_management.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from hotspots.models import Hotspot, HotspotLocation

User = get_user_model()

# Fixtures
@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin',
        password='adminpass',
        email='admin@example.com',
        user_type=1
    )

@pytest.fixture
def reseller_user(db):
    return User.objects.create_user(
        username='reseller',
        password='resellerpass',
        user_type=2
    )

@pytest.fixture
def hotspot_location(db):
    return HotspotLocation.objects.create(
        name='Test Location',
        address='123 Test St',
        latitude=0.0,
        longitude=0.0
    )

# Hotspot Creation Tests
class TestHotspotCreation:
    def test_admin_can_create_hotspot(self, api_client, admin_user, hotspot_location):
        """Admin should be able to create hotspots"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/hotspots/',
            {
                'ssid': 'AdminHotspot',
                'password': 'adminpass123',
                'hotspot_type': 'PUB',
                'location': hotspot_location.id,
                'max_users': 10,
                'bandwidth_limit': 5
            },
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Hotspot.objects.filter(ssid='AdminHotspot').exists()

    def test_reseller_can_create_hotspot(self, api_client, reseller_user, hotspot_location):
        """Reseller should be able to create hotspots"""
        api_client.force_authenticate(user=reseller_user)
        response = api_client.post(
            '/hotspots/',
            {
                'ssid': 'ResellerHotspot',
                'password': 'resellerpass123',
                'hotspot_type': 'PRI',
                'location': hotspot_location.id,
                'max_users': 5,
                'bandwidth_limit': 2
            },
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        hotspot = Hotspot.objects.get(ssid='ResellerHotspot')
        assert hotspot.owner == reseller_user

    def test_invalid_hotspot_creation(self, api_client, reseller_user, hotspot_location):
        """Should validate hotspot data"""
        api_client.force_authenticate(user=reseller_user)
        response = api_client.post(
            '/hotspots/',
            {
                'ssid': '',  # Invalid empty SSID
                'password': 'short',  # Too short password
                'location': hotspot_location.id
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'ssid' in response.data
        assert 'password' in response.data

# Hotspot Control Tests
class TestHotspotControl:
    @patch('subprocess.run')
    def test_start_hotspot(self, mock_run, db, reseller_user, hotspot_location):
        """Should successfully start hotspot"""
        mock_run.return_value = MagicMock(returncode=0)
        hotspot = Hotspot.objects.create(
            ssid='TestHotspot',
            password='testpass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        hotspot.start()
        
        # Verify the command was called correctly
        mock_run.assert_called_once()
        assert 'start' in mock_run.call_args[0][0]

    @patch('subprocess.run')
    def test_stop_hotspot(self, mock_run, db, reseller_user, hotspot_location):
        """Should successfully stop hotspot"""
        mock_run.return_value = MagicMock(returncode=0)
        hotspot = Hotspot.objects.create(
            ssid='TestHotspot',
            password='testpass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        hotspot.stop()
        
        mock_run.assert_called_once()
        assert 'stop' in mock_run.call_args[0][0]

    @patch('subprocess.run')
    def test_restart_hotspot(self, mock_run, db, reseller_user, hotspot_location):
        """Should successfully restart hotspot"""
        mock_run.return_value = MagicMock(returncode=0)
        hotspot = Hotspot.objects.create(
            ssid='TestHotspot',
            password='testpass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        hotspot.restart()
        
        assert mock_run.call_count == 2  # stop then start
        calls = [args[0][0] for args in mock_run.call_args_list]
        assert 'stop' in calls[0]
        assert 'start' in calls[1]

    @patch('subprocess.run')
    def test_get_hotspot_status(self, mock_run, db, reseller_user, hotspot_location):
        """Should correctly report hotspot status"""
        # Simulate running hotspot
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="state: RUNNING\n"
        )
        hotspot = Hotspot.objects.create(
            ssid='TestHotspot',
            password='testpass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        assert hotspot.get_status() is True
        
        # Simulate stopped hotspot
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="state: STOPPED\n"
        )
        assert hotspot.get_status() is False

# API Endpoint Tests
class TestHotspotAPI:
    @patch('hotspots.models.Hotspot.start')
    def test_api_start_hotspot(self, mock_start, api_client, reseller_user, hotspot_location):
        """API should allow starting hotspots"""
        hotspot = Hotspot.objects.create(
            ssid='APIHotspot',
            password='apipass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        api_client.force_authenticate(user=reseller_user)
        response = api_client.post(f'/hotspots/{hotspot.id}/start/')
        
        assert response.status_code == status.HTTP_200_OK
        mock_start.assert_called_once()

    @patch('hotspots.models.Hotspot.restart')
    def test_api_restart_hotspot(self, mock_restart, api_client, reseller_user, hotspot_location):
        """API should allow restarting hotspots"""
        hotspot = Hotspot.objects.create(
            ssid='APIHotspot',
            password='apipass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        api_client.force_authenticate(user=reseller_user)
        response = api_client.post(f'/hotspots/{hotspot.id}/restart/')
        
        assert response.status_code == status.HTTP_200_OK
        mock_restart.assert_called_once()

    @patch('hotspots.models.Hotspot.stop')
    def test_api_stop_hotspot(self, mock_stop, api_client, reseller_user, hotspot_location):
        """API should allow stopping hotspots"""
        hotspot = Hotspot.objects.create(
            ssid='APIHotspot',
            password='apipass123',
            owner=reseller_user,
            location=hotspot_location,
            is_active=True
        )
        
        api_client.force_authenticate(user=reseller_user)
        response = api_client.post(f'/hotspots/{hotspot.id}/stop/')
        
        assert response.status_code == status.HTTP_200_OK
        mock_stop.assert_called_once()

    @patch('hotspots.models.Hotspot.get_status')
    def test_api_hotspot_status(self, mock_status, api_client, reseller_user, hotspot_location):
        """API should return hotspot status"""
        mock_status.return_value = True
        hotspot = Hotspot.objects.create(
            ssid='APIHotspot',
            password='apipass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        api_client.force_authenticate(user=reseller_user)
        response = api_client.get(f'/hotspots/{hotspot.id}/status/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_running'] is True
        mock_status.assert_called_once()

# Error Handling Tests
class TestErrorHandling:
    @patch('subprocess.run')
    def test_start_failure(self, mock_run, db, reseller_user, hotspot_location):
        """Should handle hotspot start failures"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Failed to start")
        hotspot = Hotspot.objects.create(
            ssid='FailingHotspot',
            password='failpass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        with pytest.raises(Exception):
            hotspot.start()

    @patch('subprocess.run')
    def test_stop_failure(self, mock_run, db, reseller_user, hotspot_location):
        """Should handle hotspot stop failures"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Failed to stop")
        hotspot = Hotspot.objects.create(
            ssid='FailingHotspot',
            password='failpass123',
            owner=reseller_user,
            location=hotspot_location
        )
        
        with pytest.raises(Exception):
            hotspot.stop()