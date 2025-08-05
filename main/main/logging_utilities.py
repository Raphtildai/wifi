# core/logging_utils.py
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def log_view_request(view_func):
    """Decorator to log view requests"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        logger.info(
            f"View {view_func.__name__} called | "
            f"User: {request.user} | "
            f"Method: {request.method} | "
            f"Path: {request.path}"
        )
        try:
            response = view_func(request, *args, **kwargs)
            logger.info(
                f"View {view_func.__name__} completed | "
                f"Status: {response.status_code}"
            )
            return response
        except Exception as e:
            logger.error(
                f"View {view_func.__name__} failed | "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    return wrapped_view

def log_model_operations(model_class):
    """Decorator to log model operations"""
    original_save = model_class.save
    original_delete = model_class.delete
    
    def save(self, *args, **kwargs):
        logger.debug(
            f"Saving {model_class.__name__} | "
            f"ID: {getattr(self, 'id', 'NEW')} | "
            f"Data: {self.__dict__}"
        )
        try:
            result = original_save(self, *args, **kwargs)
            logger.info(
                f"Saved {model_class.__name__} | "
                f"ID: {self.id}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to save {model_class.__name__} | "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def delete(self, *args, **kwargs):
        logger.debug(
            f"Deleting {model_class.__name__} | "
            f"ID: {self.id}"
        )
        try:
            result = original_delete(self, *args, **kwargs)
            logger.info(
                f"Deleted {model_class.__name__} | "
                f"ID: {self.id}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to delete {model_class.__name__} | "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    model_class.save = save
    model_class.delete = delete
    return model_class