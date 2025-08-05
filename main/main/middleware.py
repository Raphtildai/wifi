# main/middleware.py
import logging
import time
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class DebugHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("Incoming headers:", request.META)
        response = self.get_response(request)
        return response

class CustomExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, AttributeError) and 'user_type' in str(exception):
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return None

class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request | {request.method} {request.path} | "
            f"User: {request.user} | "
            f"IP: {request.META.get('REMOTE_ADDR')}"
        )
        
        response = self.get_response(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Response | {request.method} {request.path} | "
            f"Status: {response.status_code} | "
            f"Duration: {duration:.2f}s"
        )
        
        return response