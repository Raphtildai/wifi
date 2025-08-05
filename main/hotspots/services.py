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
        """Generate environment file for hotspot with logging and interface auto-detection"""
        logger.info(f"Generating env file for hotspot {hotspot.id}")
        config_dir = '/tmp/hostapd-prod'
        
        try:
            # First attempt to activate wireless interfaces
            cls._activate_wireless_interfaces()

            # Auto-detect wireless interface
            wireless_interfaces = cls._detect_wireless_interfaces()
            if not wireless_interfaces:
                raise Exception("No wireless interfaces found")
            
            # Find first interface that supports AP mode
            valid_interface = None
            for iface in wireless_interfaces:
                if cls._validate_interface_for_ap(iface):
                    valid_interface = iface
                    break
                    
            if not valid_interface:
                raise Exception("No suitable wireless interface found (must support AP mode)")
                
            logger.info(f"Using wireless interface: {valid_interface}")
                
            # Use the valid_interface found available wireless interface
            if valid_interface:
                wireless_interface = valid_interface
            else:
                raise Exception("No valid wireless interface found")
            logger.info(f"Auto-detected wireless interface: {wireless_interface}")
            
            os.makedirs(config_dir, exist_ok=True)
            logger.debug(f"Created config directory {config_dir}")
            
            config_path = f'{config_dir}/hotspot_{hotspot.id}.env'
            with open(config_path, 'w') as f:
                f.write(f"""# Hostapd production environment config
    ENABLE_LOG="1"
    LOG_FILE="/var/log/prod_ap_{hotspot.id}.log"
    INTERFACE="{wireless_interface}"
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
    """)
            os.chmod(config_path, 0o644)
            logger.info(f"Env file generated at {config_path}")
            return config_path
            
        except Exception as e:
            logger.error(f"Failed to generate env file: {str(e)}", exc_info=True)
            raise Exception(f"Environment file generation failed: {str(e)}")

    @classmethod
    def _validate_interface_for_ap(cls, interface):
        """Interface validation"""
        try:
            # 1. Check if interface exists and is up
            link_result = subprocess.run(
                ['ip', 'link', 'show', interface],
                capture_output=True,
                text=True
            )
            if 'state DOWN' in link_result.stdout:
                logger.warning(f"Interface {interface} is down, attempting to bring up")
                subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'], check=True)
            
            # 2. Check AP support
            iw_result = subprocess.run(
                ['iw', interface, 'info'],
                capture_output=True,
                text=True
            )
            
            # Check both '*' and supported modes
            if 'AP' not in iw_result.stdout and '* AP' not in iw_result.stdout:
                logger.error(f"Interface {interface} doesn't show AP mode support")
                return False
            
            # 3. Check rfkill status
            rfkill_result = subprocess.run(
                ['rfkill', 'list'],
                capture_output=True,
                text=True
            )
            if f'{interface}:' in rfkill_result.stdout and 'blocked: yes' in rfkill_result.stdout:
                logger.warning(f"Interface {interface} is blocked, attempting to unblock")
                subprocess.run(['sudo', 'rfkill', 'unblock', 'wifi'], check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Interface validation failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected validation error: {str(e)}")
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
                standard_names = ['wlan0', 'wlan1', 'wlo1', 'wlp2s0']
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

    @classmethod
    def execute_hotspot_command(cls, action, hotspot_id=None):
        """Enhanced command execution with pre/post verification"""
        try:
            cls._verify_script()
            
            if action in ['start', 'stop', 'restart'] and hotspot_id:
                service_name = f"hotspot_{hotspot_id}.service"
                service_path = f"/etc/systemd/system/{service_name}"
                
                # Enhanced verification
                if action == 'start':
                    if not os.path.exists(service_path):
                        logger.warning(f"Service file missing, attempting to regenerate")
                        cls.generate_systemd_service(Hotspot.objects.get(id=hotspot_id))
                        
                    # Double-check existence
                    if not os.path.exists(service_path):
                        raise Exception(f"Service file {service_name} does not exist at {service_path}")
                
                cmd = ['sudo', 'systemctl', action, service_name]
            else:
                cmd = ['sudo', cls.HOTSPOT_SCRIPT_PATH, action]
                if hotspot_id:
                    cmd.append(str(hotspot_id))

            # Execute with timeout and enhanced logging
            logger.debug(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            logger.debug(f"Command result: {result.returncode}")
            logger.debug(f"stdout: {result.stdout[:200]}...")
            logger.debug(f"stderr: {result.stderr[:200]}...")
            
            # Enhanced post-start verification
            if action == 'start' and hotspot_id:
                time.sleep(5)  # Give service time to start
                is_running = cls.is_hotspot_running(hotspot_id)
                if not is_running:
                    result.returncode = 1
                    result.stderr += "\nPost-start verification failed - service not running"
                    logger.error("Post-start verification failed")
                    
                    # Additional diagnostics
                    journal = subprocess.run(
                        ['sudo', 'journalctl', '-u', service_name, '-n', '10', '--no-pager'],
                        capture_output=True,
                        text=True
                    ).stdout
                    logger.error(f"Service journal:\n{journal}")
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(cmd),
                'verified': action == 'start' and hotspot_id and result.returncode == 0
            }
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'returncode': -2
            }
    

#     @classmethod
#     def generate_systemd_service(cls, hotspot):
#         """Generate systemd service file with comprehensive logging"""
#         logger.info(f"Generating systemd service for hotspot {hotspot.id}")
        
#         try:
#             # Create temp directory
#             temp_dir = '/tmp/hotspot_services'
#             os.makedirs(temp_dir, exist_ok=True)
#             logger.debug(f"Created temp directory {temp_dir}")

#             # Generate environment file
#             env_file = cls.generate_env_file(hotspot)
            
#             # Create service file content
#             service_content = f"""[Unit]
# Description=Hotspot Service for {hotspot.ssid}
# After=network.target
# Requires=network.target
# ConditionPathExists=/sys/class/net/{{INTERFACE}}
# ConditionCapability=CAP_NET_ADMIN

# [Service]
# Type=simple
# EnvironmentFile={env_file}
# ExecStart={cls.HOTSPOT_SCRIPT_PATH} start {hotspot.id}
# ExecStop={cls.HOTSPOT_SCRIPT_PATH} stop {hotspot.id}
# Restart=on-failure
# RestartSec=5s

# [Install]
# WantedBy=multi-user.target
# """
#             # Write to temp location
#             temp_path = f"{temp_dir}/hotspot_{hotspot.id}.service"
#             with open(temp_path, 'w') as f:
#                 f.write(service_content)
#             logger.debug(f"Temporary service file created at {temp_path}")

#             # Move to system directory
#             subprocess.run(
#                 ['sudo', 'mv', temp_path, '/etc/systemd/system/'],
#                 check=True,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE
#             )
#             logger.debug("Service file moved to systemd directory")

#             # Set permissions
#             subprocess.run(
#                 ['sudo', 'chmod', '644', f'/etc/systemd/system/hotspot_{hotspot.id}.service'],
#                 check=True
#             )
#             logger.debug("Service file permissions set")

#             # Reload systemd
#             subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
#             logger.info("Systemd daemon reloaded")

#             return f'/etc/systemd/system/hotspot_{hotspot.id}.service'

#         except subprocess.CalledProcessError as e:
#             logger.error(f"Command failed: {e.stderr.decode().strip()}")
#             if os.path.exists(temp_path):
#                 os.remove(temp_path)
#                 logger.debug("Cleaned up temporary service file")
#             raise Exception(f"Service installation failed: {e.stderr.decode().strip()}")
#         except Exception as e:
#             logger.error(f"Service generation failed: {str(e)}", exc_info=True)
#             raise Exception(f"Service generation failed: {str(e)}")

#     @classmethod
#     def execute_hotspot_command(cls, action, hotspot_id=None):
#         """Enhanced command execution with pre/post verification"""
#         try:
#             cls._verify_script()
            
#             if action in ['start', 'stop', 'restart'] and hotspot_id:
#                 service_name = f"hotspot_{hotspot_id}.service"
                
#                 # Verify service exists before trying to control it
#                 if action == 'start' and not os.path.exists(f'/etc/systemd/system/{service_name}'):
#                     raise Exception(f"Service file {service_name} does not exist")
                
#                 cmd = ['sudo', 'systemctl', action, service_name]
#             else:
#                 cmd = ['sudo', cls.HOTSPOT_SCRIPT_PATH, action]
#                 if hotspot_id:
#                     cmd.append(str(hotspot_id))

#             # Execute with timeout
#             result = subprocess.run(
#                 cmd,
#                 check=False,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True,
#                 timeout=30
#             )
            
#             # For start commands, wait a moment then verify
#             if action == 'start' and hotspot_id:
#                 import time
#                 time.sleep(5)  # Give service time to start
#                 is_running = cls.is_hotspot_running(hotspot_id)
#                 if not is_running:
#                     result.returncode = 1
#                     result.stderr += "\nPost-start verification failed - service not running"
            
#             return {
#                 'success': result.returncode == 0,
#                 'returncode': result.returncode,
#                 'stdout': result.stdout,
#                 'stderr': result.stderr,
#                 'command': ' '.join(cmd),
#                 'verified': action == 'start' and hotspot_id and result.returncode == 0
#             }

#         except subprocess.TimeoutExpired:
#             return {
#                 'success': False,
#                 'error': "Command timed out",
#                 'returncode': -1
#             }
#         except Exception as e:
#             return {
#                 'success': False,
#                 'error': str(e),
#                 'returncode': -2
#             }

    @classmethod
    def is_hotspot_running(cls, hotspot_id):
        """More thorough check of hotspot status"""
        try:
            # 1. Check systemd status
            service_name = f"hotspot_{hotspot_id}.service"
            status_result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', service_name],
                capture_output=True,
                text=True
            )
            
            # 2. Check process list
            process_running = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if 'hostapd' in proc.info['name'].lower():
                        if any(f'hotspot_{hotspot_id}' in cmd for cmd in proc.info['cmdline']):
                            process_running = True
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 3. Verify network interface
            interface_up = False
            if hotspot := Hotspot.objects.filter(id=hotspot_id).first():
                ifconfig = subprocess.run(
                    ['sudo', 'ifconfig', hotspot.interface],
                    capture_output=True,
                    text=True
                )
                interface_up = "UP" in ifconfig.stdout
                
            return (
                status_result.returncode == 0 and 
                process_running and 
                interface_up
            )
            
        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
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