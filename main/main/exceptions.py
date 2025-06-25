# main/exceptions.py

from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    Wrap DRF’s default exception response into our standard JSON format:
    {
      "success": false,
      "status": <HTTP status code>,
      "message": "<error message>",
      "data": null,
      "errors": <original error details>
    }
    """
    # Let DRF build the standard error response first (if it can)
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        # By convention, any non‐2xx is "success": false
        success = False

        # Try to pull a human‐readable message out of response.data
        detail = None
        if isinstance(response.data, dict) and "detail" in response.data:
            detail = response.data.pop("detail")
        message = detail or response.status_text

        return Response(
            {
                "success": success,
                "status": status_code,
                "message": message,
                "data": None,
                "errors": response.data,
            },
            status=status_code,
        )

    # If DRF couldn’t build a Response (e.g. some non‐DRF exception), just bubble it
    return response

def handle_integrity_error(fn, *args, **kwargs):
    """
    Executes a function that may raise a database IntegrityError and 
    returns a standardized DRF JSON response if an error occurs.

    This helper is typically used to wrap operations that modify the database, 
    such as object creation or updates, which could violate database constraints
    (e.g. NOT NULL, UNIQUE, FOREIGN KEY).

    Args:
        fn (callable): The function to execute, usually containing the 
            database operation (e.g. create, update).
        *args: Positional arguments to pass to `fn`.
        **kwargs: Keyword arguments to pass to `fn`.

    Returns:
        Response: If no error occurs, returns the result of the `fn` call.
                  If an IntegrityError is caught, returns a DRF Response with 
                  HTTP 400 and error details.
    
    Example:
        def create_view(request):
            def create_fn():
                serializer.save()
                return Response(serializer.data, status=201)
            
            return handle_integrity_error(create_fn)
    """
    try:
        return fn(*args, **kwargs)
    except IntegrityError as e:
        return Response(
            {
                "message": "A database integrity error occurred.",
                "error": str(e)
            },
            status=status.HTTP_400_BAD_REQUEST
        )

def safe_destroy(instance, perform_destroy_fn):
    """
    Safely destroy a model instance, handling ProtectedError gracefully.
    
    Args:
        instance: The object to destroy.
        perform_destroy_fn: A callable (typically self.perform_destroy) to perform the actual deletion.
    
    Returns:
        A DRF Response indicating success or failure.
    """
    try:
        perform_destroy_fn(instance)
        return Response(
            {"message": f"{instance.__class__.__name__} deleted successfully", "data": None},
            status=status.HTTP_204_NO_CONTENT
        )
    except ProtectedError as e:
        related = [f"{obj.__class__.__name__}(id={obj.pk})" for obj in e.protected_objects]
        return Response(
            {
                "message": "Cannot delete this record because it is protected.",
                "error": "Referenced by: " + ", ".join(related)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
