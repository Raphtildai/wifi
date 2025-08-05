# hotspots/tasks.py
import os
from celery import shared_task
from .models import Hotspot
from .services import HotspotControlService
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    name='hotspots.control_hotspot_async',
    time_limit=180,  # 3 minute timeout
    soft_time_limit=160,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=30,
    retry_jitter=True
)
def control_hotspot_async(self, hotspot_id, action):
    """Async task to control hotspot with comprehensive logging"""
    task_id = self.request.id
    start_time = datetime.now()
    
    try:
        retry_count = self.request.retries
        logger.info(f"[control_hotspot_async|Task:{task_id}|Retry:{retry_count}] Starting {action} operation for hotspot:{hotspot_id}")
        
        # Get hotspot instance
        hotspot = Hotspot.objects.get(id=hotspot_id)
        logger.debug(f"[Task {task_id}] Retrieved hotspot {hotspot_id}: {hotspot.ssid}")
        
        service = HotspotControlService()
        
        # Generate config
        logger.info(f"[Task {task_id}] Generating configuration files...")
        env_path = service.generate_env_file(hotspot)
        logger.debug(f"[Task {task_id}] Environment file generated at {env_path}")
        service_path = service.generate_systemd_service(hotspot)  # THIS IS CRITICAL
        
        logger.debug(f"[Task {task_id}] Config files generated - env: {env_path}, service: {service_path}")
        
        # Verify service file exists
        logger.debug(f"[Task {task_id}] Verifying systemd service file exists...")
        if action == 'start':
            service_path = f"/etc/systemd/system/hotspot_{hotspot_id}.service"
            if not os.path.exists(service_path):
                logger.error(f"[Task {task_id}] CRITICAL: Service file missing at {service_path}")
                # Try to regenerate as last resort
                try:
                    service_path = service.generate_systemd_service(hotspot)
                    logger.info(f"[Task {task_id}] Regenerated service file at {service_path}")
                except Exception as e:
                    logger.error(f"[Task {task_id}] Failed to regenerate service file: {str(e)}")
                    raise

        # Execute command
        logger.info(f"[Task {task_id}] Executing {action} command...")
        result = service.execute_hotspot_command(action, hotspot_id)
        logger.debug(f"[Task {task_id}] Command execution result: {result}")
        
        if not result['success']:
            error_msg = f"[Task {task_id}] {action} failed: {result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        # Additional verification for start actions
        if action == 'start':
            logger.info(f"[Task {task_id}] Performing post-start verification...")
            time.sleep(10)  # Allow time for service to stabilize
            
            running = service.is_hotspot_running(hotspot_id)
            try:
                status = hotspot.get_status()
            except NameError as e:
                logger.error(f"Hotspot model reference error: {str(e)}")
                raise Exception("Configuration error - check model imports")
            logger.debug(f"[Task {task_id}] Verification - running: {running}, status: {status}")
            
            if not running:
                error_msg = f"[Task {task_id}] Hotspot not running after start command"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            if not status:
                logger.warning(f"[Task {task_id}] Hotspot started but status check failed")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Task {task_id}] Successfully completed {action} in {duration:.2f}s")
        
        return {
            'success': True,
            'action': action,
            'hotspot_id': hotspot_id,
            'output': result.get('stdout', ''),
            'task_id': task_id,
            'duration_seconds': duration
        }
        
    except Hotspot.DoesNotExist as e:
        error_msg = f"[Task {task_id}] Hotspot {hotspot_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'hotspot_id': hotspot_id,
            'action': action,
            'task_id': task_id
        }
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f"[Task {task_id}] Failed after {duration:.2f}s: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log the error to hotspot model if needed
        if 'hotspot' in locals() and hasattr(hotspot, '_log_error'):
            hotspot._log_error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'hotspot_id': hotspot_id,
            'action': action,
            'task_id': task_id,
            'duration_seconds': duration
        }