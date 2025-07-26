# test_pyrad.py
import pytest
from pyrad.packet import AccessAccept, AccessReject

def test_pyrad_constants():
    """Verify pyrad constants are the expected integer values"""
    assert AccessAccept == 2
    assert AccessReject == 3

def test_pyrad_constants_not_callable():
    """Verify the constants are not callable"""
    assert not callable(AccessAccept)
    assert not callable(AccessReject)

def test_pyrad_constant_types():
    """Verify the types of the constants"""
    assert isinstance(AccessAccept, int)
    assert isinstance(AccessReject, int)

def test_pyrad_instantiation_fails():
    """Verify attempting to instantiate raises TypeError"""
    with pytest.raises(TypeError, match="'int' object is not callable"):
        AccessAccept()
    
    with pytest.raises(TypeError, match="'int' object is not callable"):
        AccessReject()

def test_pyrad_usage_in_auth():
    """Test how these would be used in authentication"""
    # This simulates how you'd use them in your radius_authenticate function
    auth_result = AccessAccept if True else AccessReject
    assert auth_result == AccessAccept
    
    auth_result = AccessAccept if False else AccessReject
    assert auth_result == AccessReject