# core/renderers.py
from rest_framework.renderers import JSONRenderer

class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response", None)

        status_code = getattr(response, "status_code", 200)
        success = 200 <= status_code < 300

        # Extract custom message from data if passed manually
        message = ""
        if isinstance(data, dict) and "message" in data:
            message = data.pop("message")

        return super().render({
            "success": success,
            "status": status_code,
            "message": message or response.status_text,
            "data": data if success else None,
            "errors": None if success else data
        }, accepted_media_type, renderer_context)
