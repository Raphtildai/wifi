# core/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response

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
