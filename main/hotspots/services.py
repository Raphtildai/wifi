# hotspots/services.py

import os
import time
import subprocess
import logging
import psutil
from datetime import datetime
from django.conf import settings
from hotspots.models import Hotspot

logger = logging.getLogger(__name__)

class HotspotControlService:
    """Service for controlling hotspots with comprehensive logging"""
    
    HOTSPOT_SCRIPT_PATH = os.path.join(
        settings.BASE_DIR, 'scripts', 'production', 'django_script.sh'
    )

    # Function to get detailed service status for debugging
    def get_service_status(self, hotspot_id):
        """Get detailed service status for debugging"""
        try:
            # Get systemd status
            systemd_status = subprocess.run(
                ['sudo', 'systemctl', 'status', f'hotspot_{hotspot_id}.service'],
                capture_output=True,
                text=True
            ).stdout
            
            # Get process info
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'hostapd' in proc.info['name'].lower() or 'dnsmasq' in proc.info['name'].lower():
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info['cmdline'] or [])
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Get interface info if available
            hotspot = Hotspot.objects.filter(id=hotspot_id).first()
            interface_info = None
            if hotspot and hotspot.interface:
                interface_info = subprocess.run(
                    ['sudo', 'ip', 'link', 'show', hotspot.interface],
                    capture_output=True,
                    text=True
                ).stdout
            
            return {
                'systemd_status': systemd_status,
                'processes': processes,
                'interface_info': interface_info,
                'is_running': self.is_hotspot_running(hotspot_id)
            }
            
        except Exception as e:
            return f"Failed to get status: {str(e)}"

    @classmethod
    def _verify_script(cls):
        """Verify script exists and is executable with logging"""
        logger.debug(f"Verifying hotspot script at {cls.HOTSPOT_SCRIPT_PATH}")
        if not os.path.exists(cls.HOTSPOT_SCRIPT_PATH):
            logger.error(f"Script not found at {cls.HOTSPOT_SCRIPT_PATH}")
            raise FileNotFoundError(f"Script not found at {cls.HOTSPOT_SCRIPT_PATH}")
        if not os.access(cls.HOTSPOT_SCRIPT_PATH, os.X_OK):
            logger.error(f"Script not executable: {cls.HOTSPOT_SCRIPT_PATH}")
            raise PermissionError(f"Script not executable: {cls.HOTSPOT_SCRIPT_PATH}")
        logger.debug("Hotspot script verification passed")

    @classmethod 
    def _activate_wireless_interfaces(cls):
        """Ensure wireless interfaces are ready for AP mode"""
        try:
            # Unblock all wireless devices
            subprocess.run(['sudo', 'rfkill', 'unblock', 'wifi'], check=True)
            
            # Bring up common wireless interfaces
            for iface in ['wlo1', 'wlan0', 'wlan1']:
                try:
                    subprocess.run(
                        ['sudo', 'ip', 'link', 'set', iface, 'up'],
                        check=True
                    )
                    logger.info(f"Activated interface {iface}")
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not activate wireless interfaces: {str(e)}")

    @classmethod
    def generate_env_file(cls, hotspot):
        """Generate only hotspot-specific variables"""
        config_dir = os.path.join(settings.BASE_DIR, 'tmp/hostapd-prod')
        try:
            os.makedirs(config_dir, exist_ok=True, mode=0o777)
            config_path = os.path.join(config_dir, f'hotspot_{hotspot.id}.env')
            
            with open(config_path, 'w') as f:
                f.write(f"""# Hotspot-specific overrides
SSID={hotspot.ssid}
PASSWORD={hotspot.password}
CHANNEL={hotspot.channel or 6}
""")
            os.chmod(config_path, 0o666)  # Make file writable by others
            return config_path
        except Exception as e:
            logger.error(f"Failed to create env file: {str(e)}")
            raise
    
    @classmethod
    def verify_ap_mode_support(cls, interface):
        """More robust AP mode verification"""
        try:
            # First check if interface exists
            if not os.path.exists(f'/sys/class/net/{interface}'):
                logger.warning(f"Interface {interface} not found in /sys/class/net")
                return False

            # Check rfkill status
            rfkill_result = subprocess.run(
                ['sudo', 'rfkill', 'list'],
                capture_output=True,
                text=True
            )
            if 'blocked: yes' in rfkill_result.stdout:
                logger.info(f"Wireless is blocked, attempting to unblock")
                subprocess.run(['sudo', 'rfkill', 'unblock', 'wifi'], check=True)

            # Check AP mode support with sudo
            result = subprocess.run(
                ['sudo', 'iw', interface, 'info'],
                capture_output=True,
                text=True
            )
            
            # Check both supported and current modes
            if 'AP' not in result.stdout and '* AP' not in result.stdout:
                logger.error(f"Interface {interface} doesn't support AP mode")
                logger.debug(f"iw info output:\n{result.stdout}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"AP mode verification failed: {str(e)}")
            return False

    @classmethod
    def _validate_interface_for_ap(cls, interface):
        """Enhanced interface validation"""
        try:
            # 1. Check interface exists
            if not os.path.exists(f'/sys/class/net/{interface}'):
                logger.warning(f"Interface {interface} not found")
                return False

            # 2. Ensure interface is up
            link_result = subprocess.run(
                ['sudo', 'ip', 'link', 'show', interface],
                capture_output=True,
                text=True
            )
            if 'state DOWN' in link_result.stdout:
                logger.info(f"Bringing up interface {interface}")
                subprocess.run(
                    ['sudo', 'ip', 'link', 'set', interface, 'up'],
                    check=True
                )

            # 3. Verify AP mode support
            return cls.verify_ap_mode_support(interface)

        except subprocess.CalledProcessError as e:
            logger.error(f"Interface validation command failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Interface validation error: {str(e)}")
            return False

    @classmethod
    def _detect_wireless_interfaces(cls):
        """Detect available wireless interfaces"""
        try:
            # Get list of wireless interfaces using iw
            result = subprocess.run(
                ['iw', 'dev'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Parse output to find interface names
            interfaces = []
            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    interfaces.append(line.split(' ')[1])
            
            # Fallback to checking standard wireless interface names
            if not interfaces:
                standard_names = ['wlo1', 'wlan0', 'wlan1', 'wlp2s0']
                for name in standard_names:
                    if os.path.exists(f'/sys/class/net/{name}'):
                        interfaces.append(name)
            
            logger.debug(f"Detected wireless interfaces: {interfaces}")
            return interfaces
            
        except subprocess.CalledProcessError:
            logger.warning("'iw dev' command failed, falling back to basic detection")
            return cls._fallback_detect_interfaces()
        except Exception as e:
            logger.error(f"Interface detection failed: {str(e)}")
            return []

    @classmethod
    def _fallback_detect_interfaces(cls):
        """Fallback method for interface detection"""
        try:
            # Check for wireless interfaces in /sys/class/net
            interfaces = []
            net_path = '/sys/class/net'
            if os.path.exists(net_path):
                for iface in os.listdir(net_path):
                    # Skip loopback and ethernet interfaces
                    if iface.startswith(('lo', 'eth', 'enp')):
                        continue
                    # Check if wireless by looking for wireless subdirectory
                    wireless_path = os.path.join(net_path, iface, 'wireless')
                    if os.path.exists(wireless_path):
                        interfaces.append(iface)
            return interfaces
        except Exception as e:
            logger.error(f"Fallback detection failed: {str(e)}")
            return []

    @classmethod
    def generate_systemd_service(cls, hotspot):
        """Generate systemd service file with comprehensive logging and verification"""
        logger.info(f"Generating systemd service for hotspot {hotspot.id}")
        service_name = f"hotspot_{hotspot.id}.service"
        service_path = f"/etc/systemd/system/{service_name}"
        
        try:
            # 1. First verify we can write to systemd directory
            test_path = "/etc/systemd/system/hotspot_test.service"
            try:
                subprocess.run(
                    ['sudo', 'touch', test_path],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                subprocess.run(['sudo', 'rm', test_path], check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Permission check failed: {e.stderr.decode().strip()}")
                raise Exception("Insufficient permissions to create systemd service files")

            # 2. Generate environment file
            env_file = cls.generate_env_file(hotspot)
            
            # 3. Create service file content
            service_content = f"""[Unit]
Description=Hotspot Service for {hotspot.ssid}
After=network.target
Requires=network.target

[Service]
Type=simple
EnvironmentFile={env_file}
ExecStart={cls.HOTSPOT_SCRIPT_PATH} start {hotspot.id}
ExecStop={cls.HOTSPOT_SCRIPT_PATH} stop {hotspot.id}
Restart=on-failure
RestartSec=5s
TimeoutStartSec=30s

[Install]
WantedBy=multi-user.target
"""

            # 4. Write directly to target location with sudo
            temp_path = f"/tmp/{service_name}"
            with open(temp_path, 'w') as f:
                f.write(service_content)
            
            # Move with sudo and verify
            result = subprocess.run(
                ['sudo', 'mv', temp_path, service_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 5. Verify file was created
            if not os.path.exists(service_path):
                raise Exception(f"Service file not created at {service_path}")
                
            # 6. Set permissions
            subprocess.run(
                ['sudo', 'chmod', '644', service_path],
                check=True
            )
            
            # 7. Reload systemd
            subprocess.run(
                ['sudo', 'systemctl', 'daemon-reload'],
                check=True
            )
            
            logger.info(f"Successfully created service file at {service_path}")
            return service_path

        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {e.stderr.decode().strip()}"
            logger.error(error_msg)
            
            # Cleanup if partial files exist
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(service_path):
                subprocess.run(['sudo', 'rm', service_path])
                
            raise Exception(f"Service generation failed: {error_msg}")
            
        except Exception as e:
            logger.error(f"Service generation failed: {str(e)}", exc_info=True)
            raise Exception(f"Service generation failed: {str(e)}")

    def execute_hotspot_command(self, action, hotspot_id):
        """Execute hotspot command with enhanced timeout handling"""
        try:
            self._verify_script()
            self._activate_wireless_interfaces()
            
            # Check if already running before attempting start
            if action == 'start' and self.is_hotspot_running(hotspot_id):
                return {
                    'success': True,
                    'stdout': 'Hotspot already running',
                    'stderr': '',
                    'already_running': True
                }
            
            # Prepare environment with default values
            env = os.environ.copy()
            env.update({
                'WIRED_IFACE': '',
                'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
            })
            
            # Execute with separate timeout for start vs other commands
            timeout = 120 if action == 'start' else 30
            
            try:
                result = subprocess.run(
                    ['sudo', self.HOTSPOT_SCRIPT_PATH, action, str(hotspot_id)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env
                )
            except subprocess.TimeoutExpired:
                # For start commands, check if it actually started despite timeout
                if action == 'start':
                    time.sleep(5)  # Additional time for startup
                    if self.is_hotspot_running(hotspot_id):
                        return {
                            'success': True,
                            'stdout': 'Hotspot started (despite timeout)',
                            'stderr': 'Command timed out but service is running',
                            'timed_out': True
                        }
                raise
            
            # For start commands, verify the service actually started
            if action == 'start':
                time.sleep(3)  # Brief delay for service initialization
                if not self.is_hotspot_running(hotspot_id):
                    return {
                        'success': False,
                        'stdout': result.stdout,
                        'stderr': result.stderr + '\nPost-start verification failed',
                        'already_running': False
                    }
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'already_running': False
            }
            
        except subprocess.TimeoutExpired as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': f"Command timed out after {e.timeout} seconds",
                'timed_out': True
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e)
            }

    def _force_stop_hotspot(self, hotspot_id):
        """Force stop hotspot by killing processes and resetting interface"""
        try:
            # Kill any remaining processes
            subprocess.run(['sudo', 'pkill', '-f', f'hotspot_{hotspot_id}'], timeout=10)
            subprocess.run(['sudo', 'pkill', '-f', 'hostapd'], timeout=10)
            subprocess.run(['sudo', 'pkill', '-f', 'dnsmasq'], timeout=10)
            
            # Reset the interface
            hotspot = Hotspot.objects.filter(id=hotspot_id).first()
            if hotspot and hotspot.interface:
                subprocess.run(['sudo', 'ip', 'link', 'set', hotspot.interface, 'down'], timeout=5)
            
            # Stop systemd service
            subprocess.run(['sudo', 'systemctl', 'stop', f'hotspot_{hotspot_id}.service'], timeout=10)
            
            time.sleep(1)
        except Exception as e:
            logger.error(f"Force stop failed: {str(e)}")
            
    # def execute_hotspot_command(self, action, hotspot_id):
    #     """Execute hotspot command with proper running state detection"""
    #     try:
    #         self._verify_script()
    #         self._activate_wireless_interfaces()
            
    #         # Check if already running before attempting start
    #         if action == 'start' and self.is_hotspot_running(hotspot_id):
    #             return {
    #                 'success': True,
    #                 'stdout': 'Hotspot already running',
    #                 'stderr': '',
    #                 'already_running': True
    #             }
            
    #         # Execute the command
    #         result = subprocess.run(
    #             ['sudo', self.HOTSPOT_SCRIPT_PATH, action, str(hotspot_id)],
    #             capture_output=True,
    #             text=True,
    #             timeout=30
    #         )
            
    #         # For start commands, verify the service actually started
    #         if action == 'start':
    #             time.sleep(2)  # Brief delay for service initialization
    #             if not self.is_hotspot_running(hotspot_id):
    #                 return {
    #                     'success': False,
    #                     'stdout': result.stdout,
    #                     'stderr': result.stderr + '\nPost-start verification failed',
    #                     'already_running': False
    #                 }
            
    #         return {
    #             'success': result.returncode == 0,
    #             'stdout': result.stdout,
    #             'stderr': result.stderr,
    #             'already_running': False
    #         }
            
    #     except Exception as e:
    #         return {
    #             'success': False,
    #             'stdout': '',
    #             'stderr': str(e),
    #             'already_running': False
    #         }

    def is_hotspot_running(self, hotspot_id):
        """Comprehensive hotspot status check"""
        try:
            # 1. Check systemd status first
            status_result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', f'hotspot_{hotspot_id}.service'],
                capture_output=True,
                text=True
            )
            
            # If systemd says it's active, trust that
            if status_result.stdout.strip() == 'active':
                return True
                
            # 2. Check for running processes (fallback)
            hostapd_running = False
            dnsmasq_running = False
            
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'hostapd' in proc.info['name'].lower() and f'hotspot_{hotspot_id}' in cmdline:
                        hostapd_running = True
                    if 'dnsmasq' in proc.info['name'].lower() and f'hotspot_{hotspot_id}' in cmdline:
                        dnsmasq_running = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 3. Check interface state if available
            hotspot = Hotspot.objects.filter(id=hotspot_id).first()
            interface_up = True  # Assume true if we can't check
            if hotspot and hotspot.interface:
                ifconfig = subprocess.run(
                    ['sudo', 'ip', 'link', 'show', hotspot.interface],
                    capture_output=True,
                    text=True
                )
                interface_up = "state UP" in ifconfig.stdout
            
            # Consider running if either:
            # - systemd reports active, OR
            # - both processes are running and interface is up
            return (
                status_result.stdout.strip() == 'active' or 
                (hostapd_running and dnsmasq_running and interface_up)
            )
            
        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
            return False
    
    def _verify_service_running(self, hotspot_id):
        """More accurate service verification"""
        try:
            # First check systemd status
            status = subprocess.run(
                ['sudo', 'systemctl', 'is-active', f'hotspot_{hotspot_id}.service'],
                capture_output=True,
                text=True
            )
            
            # Also check for running processes
            hostapd_running = False
            dnsmasq_running = False
            for proc in psutil.process_iter(['name']):
                if 'hostapd' in proc.info['name'].lower():
                    hostapd_running = True
                if 'dnsmasq' in proc.info['name'].lower():
                    dnsmasq_running = True
            
            # Service is considered running if either:
            # 1. Systemd reports it's active, OR
            # 2. Both required processes are running
            return (
                status.stdout.strip() == 'active' or 
                (hostapd_running and dnsmasq_running)
            )
            
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return False
            
    @classmethod
    def is_process_running(cls, hotspot):
        """Check hostapd process with logging"""
        logger.debug(f"Checking process for hotspot {hotspot.id}")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'hostapd' in proc.name().lower():
                        if any(f'hotspot_{hotspot.id}' in cmd for cmd in proc.cmdline()):
                            logger.debug(f"Found running process for hotspot {hotspot.id}")
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception as e:
            logger.error(f"Process check failed: {str(e)}")
            return False
    
    @classmethod
    def get_process_id(cls, hotspot):
        """Get PID with logging"""
        logger.debug(f"Getting PID for hotspot {hotspot.id}")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'hostapd' in proc.name().lower():
                        if any(f'hotspot_{hotspot.id}' in cmd for cmd in proc.cmdline()):
                            logger.debug(f"Found PID {proc.pid} for hotspot {hotspot.id}")
                            return proc.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
        except Exception as e:
            logger.error(f"PID lookup failed: {str(e)}")
            return None