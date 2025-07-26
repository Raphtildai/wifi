# management/commands/generate_hotspot_env.py
from django.core.management.base import BaseCommand
from hotspots.models import Hotspot
import os

class Command(BaseCommand):
    help = 'Generate hotspot-specific environment files'

    def add_arguments(self, parser):
        parser.add_argument('hotspot_id', type=int)

    def handle(self, *args, **options):
        try:
            # Ensure directory exists
            os.makedirs('/tmp/hostapd-prod', exist_ok=True)
            
            hotspot = Hotspot.objects.get(pk=options['hotspot_id'])
            
            config = f"""# Hostapd production environment config for hotspot {hotspot.id}
ENABLE_LOG="1"
LOG_FILE="/var/log/prod_ap_{hotspot.id}.log"
INTERFACE="wlo1"
SSID="{hotspot.ssid or "TestNet"}"
PASSPHRASE="{hotspot.password or "1234567890"}"
AP_IP="192.168.{hotspot.id}.1"
NETMASK="255.255.255.0"
CHANNEL={hotspot.channel or 6}

# DHCP config
DHCP_RANGE_START="192.168.{hotspot.id}.10"
DHCP_RANGE_END="192.168.{hotspot.id}.100"
DHCP_LEASE_TIME="12h"
INTERNET_IFACE="eth0"
"""
            
            file_path = f'/tmp/hostapd-prod/hotspot_{hotspot.id}.env'
            with open(file_path, 'w') as f:
                f.write(config)
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created config at {file_path}'))
            
        except Hotspot.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Hotspot with ID {options["hotspot_id"]} does not exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating config: {str(e)}'))