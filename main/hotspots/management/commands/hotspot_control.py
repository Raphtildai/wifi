# hotspots/management/commands/hotspotctl.py
import os
import subprocess
from django.core.management.base import BaseCommand
from hotspots.models import Hotspot

class Command(BaseCommand):
    help = 'Control hotspot operations'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'])
        parser.add_argument('hotspot_id', type=int, nargs='?')

    def handle(self, *args, **options):
        action = options['action']
        hotspot_id = options['hotspot_id']

        if action in ['start', 'restart'] and not hotspot_id:
            self.stderr.write("Error: hotspot_id is required for start/restart actions")
            return

        # Get the absolute path to the script
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        wifi_root = os.path.dirname(project_root)
        script_path = os.path.join(wifi_root, 'scripts', 'production', 'django_script.sh')

        try:
            if hotspot_id:
                # Generate the environment file first
                hotspot = Hotspot.objects.get(pk=hotspot_id)
                self.generate_env_file(hotspot)
                cmd = ['sudo', script_path, action, str(hotspot_id)]
            else:
                cmd = ['sudo', script_path, action]

            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.stdout.write(result.stdout)
        except subprocess.CalledProcessError as e:
            self.stderr.write(f"Error: {e.stderr}")
        except Hotspot.DoesNotExist:
            self.stderr.write(f"Error: Hotspot with ID {hotspot_id} does not exist")

    def generate_env_file(self, hotspot):
        config_dir = '/tmp/hostapd-prod'
        os.makedirs(config_dir, exist_ok=True)
        
        config = f"""# Hostapd production environment config
ENABLE_LOG="1"
LOG_FILE="/var/log/prod_ap_{hotspot.id}.log"
INTERFACE="wlo1"
SSID="{hotspot.ssid}"
PASSPHRASE="{hotspot.password}"
AP_IP="192.168.{hotspot.id}.1"
NETMASK="255.255.255.0"
CHANNEL={hotspot.channel or 6}

# DHCP config
DHCP_RANGE_START="192.168.{hotspot.id}.10"
DHCP_RANGE_END="192.168.{hotspot.id}.100"
DHCP_LEASE_TIME="12h"
INTERNET_IFACE="eth0"
"""

        with open(f'{config_dir}/hotspot_{hotspot.id}.env', 'w') as f:
            f.write(config)