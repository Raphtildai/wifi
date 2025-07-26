# hotspots/services.py
import os
import subprocess
from django.conf import settings

class HotspotControlService:
    """Service for controlling hotspots"""
    
    # Get absolute path to script
    HOTSPOT_SCRIPT_PATH = os.path.join(
        settings.BASE_DIR, 
        'scripts', 
        'production', 
        'django_script.sh'
    )
    
    @classmethod
    def _verify_script(cls):
        """Verify script exists and is executable"""
        if not os.path.exists(cls.HOTSPOT_SCRIPT_PATH):
            raise FileNotFoundError(f"Script not found at {cls.HOTSPOT_SCRIPT_PATH}")
        if not os.access(cls.HOTSPOT_SCRIPT_PATH, os.X_OK):
            raise PermissionError(f"Script not executable: {cls.HOTSPOT_SCRIPT_PATH}")

    @classmethod
    def generate_env_file(cls, hotspot):
        """Generate environment file for hotspot"""
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
        config_path = f'{config_dir}/hotspot_{hotspot.id}.env'
        with open(config_path, 'w') as f:
            f.write(config)
        
        os.chmod(config_path, 0o644)
        return config_path
    
    @classmethod
    def execute_hotspot_command(cls, action, hotspot_id=None):
        """Execute hotspot control command"""
        cls._verify_script()
        
        cmd = ['sudo', cls.HOTSPOT_SCRIPT_PATH, action]
        if hotspot_id:
            cmd.append(str(hotspot_id))
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f"Command failed (code {result.returncode}): {result.stderr}",
                    'output': result.stdout
                }
            return {
                'success': True,
                'output': result.stdout,
                'error': result.stderr
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Command failed (code {e.returncode}): {e.stderr}",
                'returncode': e.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def is_hotspot_running(cls, hotspot_id):
        """Check if hotspot is running through systemd"""
        try:
            service_name = f"hostapd_{hotspot_id}.service"
            status = subprocess.run(
                ['sudo', 'systemctl', 'is-active', service_name],
                capture_output=True,
                text=True
            )
            return status.returncode == 0
        except Exception:
            return False
            
    @classmethod
    def is_process_running(cls, hotspot):
        """Check if hostapd process is running for this hotspot"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'hostapd' in proc.name().lower():
                    if any(f'hotspot_{hotspot.id}' in cmd for cmd in proc.cmdline()):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    @classmethod
    def get_process_id(cls, hotspot):
        """Get PID of hostapd process for this hotspot"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'hostapd' in proc.name().lower():
                    if any(f'hotspot_{hotspot.id}' in cmd for cmd in proc.cmdline()):
                        return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None