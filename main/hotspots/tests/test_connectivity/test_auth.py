# # hotspots/tests/test_connectivity/test_auth.py
# hotspots/tests/test_connectivity/test_auth.py

import pytest
import subprocess
from time import sleep
from unittest.mock import patch
from tests.conftest_base import api_client, admin_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.mark.django_db
def test_full_auth_flow_mocked(api_client, test_hotspot, admin_user):
    """Test with mocked wireless functionality (CI-safe)"""
    auth_response = api_client.post(
        '/api-token-auth/',
        {'username': admin_user.username, 'password': 'testpass123'},
        format='json'
    )
    assert auth_response.status_code == 200
    token = auth_response.data['token']
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        response = api_client.post(
            '/api/hotspot-auth/authenticate/',
            {
                'username': admin_user.username,
                'password': 'testpass123',
                'hotspot_ssid': test_hotspot.ssid
            },
            format='json'
        )
        assert response.status_code == 200
        assert response.json()['data']['status'] == 'access_granted'


@pytest.mark.skipif(
    not subprocess.run(['which', 'hostapd'], stdout=subprocess.DEVNULL).returncode == 0,
    reason="hostapd is not installed"
)
@pytest.mark.skipif(
    not subprocess.run(['which', 'iwconfig'], stdout=subprocess.DEVNULL).returncode == 0,
    reason="iwconfig not available"
)
def test_full_auth_flow(api_client, test_hotspot, admin_user):
    """Real integration test using hostapd and actual wireless interface"""
    try:
        iface = subprocess.check_output(
            "iw dev | awk '$1==\"Interface\"{print $2}'",
            shell=True
        ).decode().strip().splitlines()[0]
    except Exception:
        pytest.skip("No wireless interface found")

    hostapd_config = f"""
interface={iface}
ssid={test_hotspot.ssid}
hw_mode=g
channel=6
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={test_hotspot.password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
logger_stdout=-1
logger_stdout_level=2
"""

    config_path = "/tmp/test_ap.conf"
    with open(config_path, "w") as f:
        f.write(hostapd_config)

    ap_process = None
    try:
        ap_process = subprocess.Popen(
            ["hostapd", "-B", config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        sleep(3)  # Wait for AP to start

        # Token auth
        auth_response = api_client.post(
            '/api-token-auth/',
            {'username': admin_user.username, 'password': 'testpass123'},
            format='json'
        )
        assert auth_response.status_code == 200
        token = auth_response.data['token']
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # Perform Wi-Fi auth
        response = api_client.post(
            '/api/hotspot-auth/authenticate/',
            {
                'username': admin_user.username,
                'password': 'testpass123',
                'hotspot_ssid': test_hotspot.ssid
            },
            format='json'
        )
        assert response.status_code == 200
        assert response.json()['data']['status'] == 'access_granted'

        # Optional: check radius logs (if in dev env)
        try:
            with open('/var/log/freeradius/radius.log') as log_file:
                logs = log_file.read()
                assert "Access-Accept" in logs
                assert test_hotspot.ssid in logs
        except FileNotFoundError:
            pass  # Not fatal

    finally:
        if ap_process:
            ap_process.terminate()
            ap_process.wait()
        subprocess.run(["rm", "-f", config_path], check=False)
        api_client.credentials()  # Clear token

# import pytest
# import subprocess
# from time import sleep
# from unittest.mock import patch
# from tests.conftest_base import api_client, admin_user #, reseller_user, customer_user

# pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# @pytest.mark.django_db
# def test_full_auth_flow_mocked(api_client, test_hotspot, admin_user):
#     """Test with mocked wireless functionality"""
#     # First authenticate to get token
#     auth_response = api_client.post(
#         '/api-token-auth/',
#         {'username': admin_user.username, 'password': 'testpass123'},
#         format='json'
#     )
#     print(f"Auth response: {auth_response.data}")
#     assert auth_response.status_code == 200
#     token = auth_response.data['token']
    
#     # Set the auth token for subsequent requests
#     api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    
#     with patch('subprocess.run') as mock_run:
#         mock_run.return_value.returncode = 0
#         response = api_client.post(
#             '/api/hotspot-auth/authenticate/',
#             {
#                 'username': admin_user.username,
#                 'password': 'testpass123',
#                 'hotspot_ssid': test_hotspot.ssid
#             },
#             format='json'
#         )
#         assert response.status_code == 200

# def test_full_auth_flow(api_client, test_hotspot, admin_user):
#     """Integration test for complete authentication flow"""
#     # Skip hostapd test if no wireless interface available
#     try:
#         # Check for any available wireless interface
#         wireless_iface = subprocess.check_output(
#             "iwconfig 2>/dev/null | grep -o '^[^ ]*'",
#             shell=True
#         ).decode().strip()
#         if not wireless_iface:
#             pytest.skip("No wireless interface available")
#     except subprocess.CalledProcessError:
#         pytest.skip("Wireless tools not available")

#     # Create proper hostapd configuration using found interface
#     hotspot_config = f"""interface={wireless_iface}
# ssid={test_hotspot.ssid}
# hw_mode=g
# channel=6
# macaddr_acl=0
# auth_algs=1
# ignore_broadcast_ssid=0
# wpa=2
# wpa_passphrase={test_hotspot.password}
# wpa_key_mgmt=WPA-PSK
# wpa_pairwise=TKIP
# rsn_pairwise=CCMP
# """
    
#     # Write config to temporary file
#     with open('/tmp/test_ap.conf', 'w') as f:
#         f.write(hotspot_config)

#     try:
#         # Start test AP
#         ap_process = subprocess.Popen([
#             "hostapd",
#             "-B",
#             "/tmp/test_ap.conf"
#         ])
        
#         # Wait for AP to initialize
#         sleep(2)
        
#         # Authenticate the test client first
#         auth_response = api_client.post(
#             '/api-token-auth/',
#             {'username': admin_user.username, 'password': 'testpass123'},
#             format='json'
#         )
#         print(f"Auth response: {auth_response.data}")
#         assert auth_response.status_code == 200
#         token = auth_response.data['token']
        
#         # Set the auth token for subsequent requests
#         api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
#         # Test hotspot authentication
#         response = api_client.post(
#             '/api/hotspot-auth/authenticate/',
#             {
#                 'username': admin_user.username,
#                 'password': 'testpass123',
#                 'hotspot_ssid': test_hotspot.ssid
#             },
#             format='json'
#         )
#         print(f"Auth response: {response.json()}")
        
#         assert response.status_code == 200, (
#             f"Expected 200 OK, got {response.status_code}. "
#             f"Response: {response.json()}"
#         )
#         assert response.json()['data']['status'] == 'access_granted'
        
#         # Verify RADIUS log if possible
#         try:
#             with open('/var/log/freeradius/radius.log') as f:
#                 log_content = f.read()
#                 assert "Access-Accept" in log_content
#                 assert test_hotspot.ssid in log_content
#         except FileNotFoundError:
#             pytest.skip("FreeRADIUS log not available")

#     finally:
#         # Cleanup
#         if 'ap_process' in locals():
#             ap_process.terminate()
#             ap_process.wait()
#         subprocess.run(["rm", "-f", "/tmp/test_ap.conf"], check=False)
#         api_client.credentials()  # Clear auth credentials