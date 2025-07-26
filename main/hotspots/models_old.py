# hotspots/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from accounts.enums import UserType
import subprocess
import os

User = get_user_model()

class HotspotLocation(models.Model):
    """Physical location of WiFi access point without GIS"""
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90)
        ]
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180)
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Hotspot Location"
        verbose_name_plural = "Hotspot Locations"
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return self.name

    @property
    def coordinates(self):
        """Return as tuple for convenience"""
        return (float(self.latitude), float(self.longitude))


class Hotspot(models.Model):
    class HotspotType(models.TextChoices):
        PUBLIC = 'PUB', _('Public')
        PRIVATE = 'PRI', _('Private')
        COMMERCIAL = 'COM', _('Commercial')
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hotspots',
        limit_choices_to={'user_type__in': [UserType.ADMIN, UserType.RESELLER]}
    )
    location = models.ForeignKey(
        HotspotLocation,
        on_delete=models.PROTECT,
        related_name='hotspots'
    )
    ssid = models.CharField(max_length=32)
    password = models.CharField(max_length=64, blank=True)
    hotspot_type = models.CharField(
        max_length=3,
        choices=HotspotType.choices,
        default=HotspotType.PUBLIC
    )
    max_users = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)]
    )
    bandwidth_limit = models.PositiveIntegerField(
        default=10,
        help_text="Mbps per user"
    )
    is_active = models.BooleanField(default=True)
    allowed_users = models.ManyToManyField(User, related_name="allowed_hotspots", blank=True)
    current_task_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Hotspot"
        verbose_name_plural = "Hotspots"
        unique_together = ('owner', 'ssid')
    
    def __str__(self):
        return f"{self.ssid} at {self.location.name}"
    
    def start(self):
        """Enhanced hotspot starter with detailed error reporting"""
        try:
            # Verify system capabilities
            if not self._verify_ap_support():
                raise Exception("Wireless interface doesn't support AP mode")
            
            if not self._verify_packages():
                raise Exception("Missing required packages (hostapd, dnsmasq, iw)")
            
            # Verify interface is available
            interface = self.interface
            if not interface:
                raise Exception("No wireless interface found")
            
            # Execute the start command with timeout
            try:
                from django.core.management import call_command
                result = call_command(
                    'hotspot_control', 
                    'start', 
                    f'--hotspot-id={self.id}',
                    '--debug'
                )
                
                # Verify it actually started
                time.sleep(3)  # Give it time to initialize
                if not self.get_status():
                    raise Exception("Hotspot started but verification failed")
                    
                return True
                
            except subprocess.TimeoutExpired:
                raise Exception("Hotspot startup timed out")
                
        except Exception as e:
            error_msg = f"Failed to start hotspot: {str(e)}"
            print(error_msg)
            # Log detailed error to database or file
            self._log_error(error_msg)
            raise Exception(error_msg)

    def _log_error(self, message):
        """Log errors to a dedicated file"""
        log_file = "/var/log/hotspot_errors.log"
        with open(log_file, "a") as f:
            f.write(f"[{time.ctime()}] Hotspot {self.ssid} error: {message}\n")

    def _verify_ap_support(self):
        """Check if wireless interface supports AP mode"""
        try:
            interface = self.interface
            result = subprocess.run(
                ['iw', 'list'],
                capture_output=True,
                text=True
            )
            return '* AP' in result.stdout
        except Exception:
            return False

    def _verify_packages(self):
        """Verify required packages are installed"""
        required = ['hostapd', 'dnsmasq', 'iw']
        try:
            for pkg in required:
                subprocess.run(
                    ['dpkg', '-s', pkg],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            return True
        except subprocess.CalledProcessError:
            return False

    def stop(self):
        """Stop this hotspot"""
        from django.core.management import call_command
        call_command('hotspot_control', 'stop', f'--hotspot-id={self.id}')

    def restart(self):
        """Restart this hotspot"""
        from django.core.management import call_command
        call_command('hotspot_control', 'restart', f'--hotspot-id={self.id}')

    # def get_status(self):
    #     """Check if hotspot is running"""
    #     try:
    #         result = subprocess.run(
    #             ['sudo', 'hostapd_cli', '-i', self.interface, 'status'],
    #             capture_output=True,
    #             text=True
    #         )
    #         print(f"Result of status: {result}")
    #         return 'state: RUNNING' in result.stdout
    #     except:
    #         return False

    # def get_status(self):
    #     """Check if hotspot is actually running on the system"""
    #     try:
    #         # Method 1: Check for hostapd process
    #         result = subprocess.run(
    #             ['pgrep', '-f', f'hostapd.*{self.ssid}'],
    #             capture_output=True
    #         )
    #         if result.returncode == 0:
    #             return True
            
    #         # Method 2: Check interface mode
    #         interface = self.interface or 'wlo1'  # default interface
    #         result = subprocess.run(
    #             ['iwconfig', interface],
    #             capture_output=True,
    #             text=True
    #         )
    #         return 'Mode:Master' in result.stdout
    #     except Exception as e:
    #         print(f"Status check error: {str(e)}")
    #         return False

    # @property
    # def interface(self):
    #     """Get the wireless interface being used"""
    #     # You might want to make this a model field or detect dynamically
    #     result = subprocess.run(
    #         ['iw', 'dev'],
    #         capture_output=True,
    #         text=True
    #     )
    #     return result.stdout.split('\n')[0].split()[-1]
    def get_status(self):
        """Comprehensive status check with PID verification"""
        def check_pid_file(service):
            pid_file = f"/var/run/hostapd_prod/{service}.pid"
            try:
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                    os.kill(pid, 0)  # Check if process exists
                    return True
            except (FileNotFoundError, ProcessLookupError, ValueError):
                return False

        status = {
            'hostapd': check_pid_file('hostapd'),
            'dnsmasq': check_pid_file('dnsmasq'),
            'interface': self._check_interface_mode()
        }

        print(f"Hotspot status for {self.ssid}:")
        print(f"  hostapd: {'Running' if status['hostapd'] else 'Not running'}")
        print(f"  dnsmasq: {'Running' if status['dnsmasq'] else 'Not running'}")
        print(f"  interface: {'Master mode' if status['interface'] else 'Not in master mode'}")

        return all(status.values())

    def _check_interface_mode(self):
        try:
            result = subprocess.run(
                ['iwconfig', self.interface],
                capture_output=True,
                text=True
            )
            return 'Mode:Master' in result.stdout
        except Exception:
            return False

    @property
    def interface(self):
        """Get the wireless interface being used"""
        try:
            result = subprocess.run(
                ['iw', 'dev'],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    return line.split()[1]
        except Exception:
            pass
        return 'wlan0'  # fallback

class Session(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    hotspot = models.ForeignKey(
        Hotspot,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    data_used = models.PositiveIntegerField(
        default=0,
        help_text="Data used in MB"
    )
    ip_address = models.GenericIPAddressField()
    mac_address = models.CharField(max_length=17, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Session #{self.id} by {self.user.username}"