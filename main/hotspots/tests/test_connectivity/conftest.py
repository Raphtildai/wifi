# hotspots/tests/test_connectivity/conftest.py
import pytest
from tests.conftest_base import (
    api_client,
    admin_user as test_admin_user,
    reseller_user as test_reseller_user,
    test_location,
    test_hotspot,
    inactive_hotspot
)

# Re-export the fixtures with their original names
pytest_plugins = ['tests.conftest_base']

# You can keep any connectivity-specific fixtures here
# For example, if you need a specialized hotspot fixture:
@pytest.fixture
def public_hotspot(test_location, test_reseller_user):
    """Special public hotspot fixture for connectivity tests"""
    return Hotspot.objects.create(
        owner=test_reseller_user,
        location=test_location,
        ssid="PublicHotspot",
        password="",
        hotspot_type="PUB",
        max_users=50,
        bandwidth_limit=20,
        is_active=True
    )