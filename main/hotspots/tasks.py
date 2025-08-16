import os
from celery import shared_task
from .models import Hotspot
from .services import HotspotControlService
import time
import logging
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    name='hotspots.control_hotspot_async',
    time_limit=300,  # 5 minutes timeout
    soft_time_limit=280,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 10},
    retry_backoff=True,
    retry_jitter=True
)
def control_hotspot_async(self, hotspot_id, action):
    """Enhanced async task with robust timeout handling and detailed diagnostics"""
    task_id = self.request.id
    start_time = datetime.now()
    retry_count = self.request.retries
    
    try:
        logger.info(
            f"[Task:{task_id}|Retry:{retry_count}] Starting {action} for hotspot:{hotspot_id}",
            extra={'hotspot_id': hotspot_id, 'action': action, 'retry': retry_count}
        )
        
        # Get hotspot instance
        hotspot = Hotspot.objects.get(id=hotspot_id)
        logger.debug(
            f"Retrieved hotspot {hotspot_id}: {hotspot.ssid}",
            extra={'ssid': hotspot.ssid, 'interface': hotspot.interface}
        )
        
        service = HotspotControlService()
        
        # Generate config files for start/restart operations
        if action in ['start', 'restart']:
            logger.info("Generating configuration files...")
            try:
                env_path = service.generate_env_file(hotspot)
                service_path = service.generate_systemd_service(hotspot)
                logger.debug(
                    "Config files generated",
                    extra={'env_path': env_path, 'service_path': service_path}
                )
                
                # Verify service file exists
                if not os.path.exists(service_path):
                    logger.warning("Service file missing, regenerating...")
                    service_path = service.generate_systemd_service(hotspot)
                    if not os.path.exists(service_path):
                        raise Exception(f"Service file creation failed at {service_path}")
            except Exception as e:
                logger.error("Config generation failed", exc_info=True)
                raise Exception(f"Config generation failed: {str(e)}")

        # Execute command with enhanced monitoring
        logger.info(f"Executing {action} command...")
        try:
            result = service.execute_hotspot_command(action, hotspot_id)
            logger.debug(
                "Command execution result",
                extra={'success': result.get('success'), 'timed_out': result.get('timed_out')}
            )
        except Exception as e:
            logger.error("Command execution failed", exc_info=True)
            raise Exception(f"Command execution failed: {str(e)}")
        
        # Handle timeout cases
        if result.get('timed_out'):
            logger.warning(
                "Command timed out, verifying hotspot status...",
                extra={'timeout': True}
            )
            time.sleep(5)  # Additional time for service initialization
            
            # Check if service actually started despite timeout
            is_running = service.is_hotspot_running(hotspot_id)
            if is_running:
                logger.info(
                    "Hotspot started despite timeout",
                    extra={'running': True}
                )
                result.update({
                    'success': True,
                    'timed_out_but_running': True
                })
            else:
                logger.error(
                    "Hotspot not running after timeout",
                    extra={'running': False}
                )
                raise Exception("Command timed out and hotspot not running")

        if not result['success']:
            error_details = {
                'stdout': result.get('stdout'),
                'stderr': result.get('stderr'),
                'command': result.get('command')
            }
            logger.error(
                f"{action} command failed",
                extra=error_details
            )
            raise Exception(f"{action} failed: {result.get('stderr', 'Unknown error')}")

        # Enhanced post-action verification
        if action in ['start', 'restart']:
            logger.info("Performing post-start verification...")
            
            # Verification with progressive backoff
            max_attempts = 5
            running = False
            for attempt in range(max_attempts):
                running = service.is_hotspot_running(hotspot_id)
                if running:
                    break
                
                wait_time = (attempt + 1) * 3  # 3, 6, 9, 12, 15s
                logger.debug(
                    f"Verification attempt {attempt+1}/{max_attempts}",
                    extra={'wait_seconds': wait_time}
                )
                time.sleep(wait_time)

            if not running:
                service_status = service.get_service_status(hotspot_id)
                logger.error(
                    "Hotspot not running after start",
                    extra={'service_status': service_status}
                )
                raise Exception(f"Hotspot not running after {action}. Service status: {service_status}")
            
            # Update hotspot status
            hotspot.is_active = True
            hotspot.save()
            logger.info("Hotspot status updated to active")

        elif action == 'stop':
            # Verify stop was successful
            time.sleep(2)  # Brief delay for shutdown
            if service.is_hotspot_running(hotspot_id):
                logger.warning("Hotspot still running, forcing stop...")
                service._force_stop_hotspot(hotspot_id)
                
                if service.is_hotspot_running(hotspot_id):
                    raise Exception("Failed to stop hotspot after force stop")
            
            # Update hotspot status
            hotspot.is_active = False
            hotspot.save()
            logger.info("Hotspot status updated to inactive")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Successfully completed {action}",
            extra={
                'duration_seconds': duration,
                'hotspot_status': hotspot.is_active
            }
        )
        
        return {
            'success': True,
            'action': action,
            'hotspot_id': hotspot_id,
            'is_running': hotspot.is_active,
            'output': result.get('stdout'),
            'error': result.get('stderr'),
            'task_id': task_id,
            'duration_seconds': duration,
            'timed_out': result.get('timed_out', False),
            'timed_out_but_running': result.get('timed_out_but_running', False)
        }
        
    except Hotspot.DoesNotExist as e:
        error_msg = f"Hotspot {hotspot_id} not found"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'hotspot_id': hotspot_id,
            'action': action,
            'task_id': task_id
        }
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f"Failed after {duration:.2f}s: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Try to update hotspot status based on actual state
        if 'hotspot' in locals():
            try:
                actual_status = service.is_hotspot_running(hotspot_id) if 'service' in locals() else None
                if actual_status is not None:
                    hotspot.is_active = actual_status
                    hotspot.save()
                    logger.info(
                        "Updated hotspot status based on actual state",
                        extra={'is_active': actual_status}
                    )
            except Exception as update_error:
                logger.error(
                    "Failed to update hotspot status",
                    exc_info=True
                )
        
        return {
            'success': False,
            'error': error_msg,
            'hotspot_id': hotspot_id,
            'action': action,
            'task_id': task_id,
            'duration_seconds': duration,
            'traceback': traceback.format_exc()
        }