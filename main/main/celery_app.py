import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
app = Celery('main')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Commands
# 1. Check Celery Workers:
# celery -A main worker --loglevel=info
# 2. Verify Task Execution:
# celery -A main inspect active
# 3. Test Hotspot Control Command Manually:
# python manage.py hotspot_control start --hotspot-id=1
# 4. Check System Processes:
# ps aux | grep hostapd
# iwconfig
# 5. Review Hostapd Logs:
# journalctl -u hostapd -f


# sudo modprobe -r iwlwifi && sudo modprobe iwlwifi)