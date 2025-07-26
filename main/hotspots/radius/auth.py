# hotspots/radius/auth.py
from django.contrib.auth import get_user_model
from pyrad.packet import AccessAccept, AccessReject
from django.contrib.auth import authenticate
from pyrad import __version__

User = get_user_model()

if not __version__.startswith('2.4'):
    import warnings
    warnings.warn(f"pyrad {__version__} may behave differently than expected")

def radius_authenticate(username, password):
    """Authenticate user against RADIUS server.
    Returns AccessAccept (2) or AccessReject (3) from pyrad.packet
    """
    user = authenticate(username=username, password=password)
    
    if not user or not user.is_active:
        return AccessReject  
    
    if hasattr(user, 'has_active_subscription') and user.has_active_subscription():
        return AccessAccept  
        
    return AccessReject


# def radius_authenticate(username, password):
#     try:
#         user = User.objects.get(username=username)
#         if not user.is_active:
#             # Return AccessReject packet
#             return create_reject_packet()
            
#         if not user.check_password(password):
#             # Return AccessReject packet
#             return create_reject_packet()
            
#         # Create and return AccessAccept packet with attributes
#         return create_accept_packet(user)
        
#     except User.DoesNotExist:
#         # Return AccessReject packet
#         return create_reject_packet()