# hotspots/management/commands/hotspot_control.py
import os
import subprocess
import json
from django.core.management.base import BaseCommand
from hotspots.models import Hotspot
from django.conf import settings

class Command(BaseCommand):
    help = 'Control WiFi hotspot functionality'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['start', 'stop', 'restart'])
        parser.add_argument('--hotspot-id', type=int, help='Hotspot ID to control')
        parser.add_argument('--json', action='store_true', help='Output in JSON format')

    def handle(self, *args, **options):
        action = options['action']
        hotspot_id = options['hotspot_id']
        json_output = options['json']
        
        results = {
            'success': False,
            'action': action,
            'hotspots': [],
            'errors': []
        }

        try:
            if hotspot_id:
                try:
                    hotspot = Hotspot.objects.get(pk=hotspot_id, is_active=True)
                    result = self._control_hotspot(action, hotspot, json_output)
                    results['hotspots'].append({
                        'id': hotspot.id,
                        'ssid': hotspot.ssid,
                        'result': result
                    })
                    results['success'] = True
                except Hotspot.DoesNotExist:
                    error = f"Hotspot with ID {hotspot_id} not found or inactive"
                    results['errors'].append(error)
                    if not json_output:
                        self.stderr.write(error)
            else:
                # Control all active hotspots
                for hotspot in Hotspot.objects.filter(is_active=True):
                    try:
                        result = self._control_hotspot(action, hotspot, json_output)
                        results['hotspots'].append({
                            'id': hotspot.id,
                            'ssid': hotspot.ssid,
                            'result': result
                        })
                        results['success'] = True
                    except Exception as e:
                        error = str(e)
                        results['errors'].append(error)
                        if not json_output:
                            self.stderr.write(error)

            if json_output:
                self.stdout.write(json.dumps(results))
                
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            results['errors'].append(error)
            self.stdout.write(json.dumps(results))
            return
            # if json_output:
            #     self.stdout.write(json.dumps(results))
            # else:
            #     self.stderr.write(error)

    def _detect_wireless_interface(self):
        """Detect the first available wireless interface"""
        try:
            result = subprocess.run(
                ['iw', 'dev'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    return line.split()[1]
            return 'wlan0'  # fallback
        except Exception:
            return 'wlan0'  # fallback

    def _control_hotspot(self, action, hotspot, json_output=False):
        # Get the absolute path to the script
        script_path = os.path.join(settings.BASE_DIR,'scripts', 'production', 'start-ap.sh')

        # Path debug logging
        print(f"Script path: {script_path}")
        print(f"Script exists: {os.path.exists(script_path)}")
        print(f"Script executable: {os.access(script_path, os.X_OK)}")
        
        if not os.path.exists(script_path):
            error = f"Hotspot script not found at {script_path}"
            if json_output:
                return {'success': False, 'error': error}
            raise Exception(error)
            
        if not os.access(script_path, os.X_OK):
            error = f"Hotspot script is not executable: {script_path}"
            if json_output:
                return {'success': False, 'error': error}
            raise Exception(error)

        env_file = '/tmp/hostapd-prod.env'
        self._update_env_file(hotspot, env_file)

        
        # Get interface name dynamically
        interface = self._detect_wireless_interface()
        
        # Full preparation sequence
        prep_commands = [
            ['sudo', 'systemctl', 'stop', 'NetworkManager.service'],
            ['sudo', 'systemctl', 'stop', 'wpa_supplicant.service'],
            ['sudo', 'rfkill', 'unblock', 'wifi'],
            ['sudo', 'ip', 'link', 'set', interface, 'down'],
            ['sudo', 'iw', interface, 'set', 'type', '__ap'],
            ['sudo', 'ip', 'link', 'set', interface, 'up'],
            ['sudo', 'systemctl', 'daemon-reload']
        ]
        
        # Execute preparation commands
        for cmd in prep_commands:
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as e:
                error_msg = f"Preparation command failed: {' '.join(cmd)}"
                if json_output:
                    return {'success': False, 'error': error_msg}
                raise Exception(error_msg)
        
        # Run the hotspot script with explicit environment
        env = {
            'INTERFACE': interface,
            'SSID': hotspot.ssid,
            'PASSPHRASE': hotspot.password,
            'CHANNEL': '6',
            'AP_IP': '192.168.50.1',
            'NETMASK': '255.255.255.0'
        }
        
        try:
            result = subprocess.run(
                ['sudo', script_path, action],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, **env}
            )
            
            output = {
                'success': True,
                'message': f"Successfully {action}ed hotspot: {hotspot.ssid}",
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if json_output:
                return output
                
            self.stdout.write(output['message'])
            if result.stdout:
                self.stdout.write(result.stdout)
            return output
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to {action} hotspot {hotspot.ssid}"
            if e.stderr:
                error_msg += f": {e.stderr}"
                
            output = {
                'success': False,
                'error': error_msg,
                'cmd': e.cmd,
                'stdout': e.stdout,
                'stderr': e.stderr
            }
            
            if json_output:
                return output
                
            self.stderr.write(error_msg)
            self.stderr.write(f"Command that failed: {e.cmd}")
            if e.stdout:
                self.stderr.write(f"Command output: {e.stdout}")
            raise Exception(error_msg)

    def _update_env_file(self, hotspot, env_file_path):
        """Update the environment file with hotspot settings"""
        # First detect the current wireless interface
        try:
            interface_result = subprocess.run(
                ['iw', 'dev'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            interface = None
            for line in interface_result.stdout.split('\n'):
                if 'Interface' in line:
                    interface = line.split()[1]
                    break
        except Exception as e:
            self.stderr.write(f"Failed to detect wireless interface: {str(e)}")
            interface = 'wlan0'  # fallback
        
        env_content = f"""# Hostapd production environment config
ENABLE_LOG="1"
LOG_FILE="/var/log/prod_ap.log"
INTERFACE="{interface}"
AP_IP="192.168.50.1"
NETMASK="255.255.255.0"
SSID="{hotspot.ssid}"
PASSPHRASE="{hotspot.password}"
CHANNEL=6

# DHCP config
DHCP_RANGE_START="192.168.50.10"
DHCP_RANGE_END="192.168.50.100"
DHCP_LEASE_TIME="12h"
INTERNET_IFACE="eth0"
"""

        try:
            os.makedirs('/tmp/hostapd-prod', exist_ok=True)
            hotspot_env_file = f'/tmp/hostapd-prod/hotspot_{hotspot.id}.env'
            
            with open(hotspot_env_file, 'w') as f:
                f.write(env_content)
            os.chmod(hotspot_env_file, 0o644)
            
            with open(env_file_path, 'w') as f:
                f.write(env_content)
                
        except Exception as e:
            self.stderr.write(f"Failed to write config: {str(e)}")
            raise