# hotspots/tasks.py
from celery import shared_task
from .models import Hotspot
from .services import HotspotControlService
import time

@shared_task(
    bind=True,
    time_limit=180,  # 3 minute timeout
    soft_time_limit=160,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=30
)
def control_hotspot_async(self, hotspot_id, action):
    try:
        hotspot = Hotspot.objects.get(id=hotspot_id)
        service = HotspotControlService()
        
        # Generate config
        env_path = service.generate_env_file(hotspot)
        
        # Execute command
        result = service.execute_hotspot_command(action, hotspot_id)
        
        if not result['success']:
            raise Exception(result['error'])
            
        # Additional verification for start actions
        if action == 'start':
            time.sleep(10)
            running = service.is_hotspot_running(hotspot_id)
            status = hotspot.get_status()
            # if not (running and status):
            #     raise Exception(f"Hotspot verification failed. is_running={running}, get_status={status}")

        return {
            'success': True,
            'action': action,
            'hotspot_id': hotspot_id,
            'output': result['output']
        }
    except Exception as e:
        # Log the error to hotspot model if needed
        if hasattr(hotspot, '_log_error'):
            hotspot._log_error(str(e))
        
        return {
            'success': False,
            'error': str(e),
            'hotspot_id': hotspot_id,
            'action': action
        }