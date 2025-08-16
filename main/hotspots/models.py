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
    channel = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(1)]
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
        """Start hotspot using service layer"""
        from hotspots.services import HotspotControlService
        service = HotspotControlService()
        
        try:
            service.generate_env_file(self)
            result = service.execute_command('start', self.id)
            
            if not result['success']:
                raise Exception(result['error'])
                
            if not self.get_status():
                raise Exception("Hotspot started but verification failed")
            
            return True
        except Exception as e:
            self._log_error(f"Failed to start hotspot: {str(e)}")
            raise

    def stop(self):
        """Stop this hotspot"""
        from django.core.management import call_command
        call_command('hotspot_control', 'stop', f'--hotspot-id={self.id}')

    def restart(self):
        """Restart this hotspot"""
        from django.core.management import call_command
        call_command('hotspot_control', 'restart', f'--hotspot-id={self.id}')

    def get_status(self):
        """Check if hotspot is running by verifying hostapd process and SSID"""
        try:
            # Check if hostapd is running (any instance)
            hostapd_running = subprocess.run(
                ['pgrep', 'hostapd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ).returncode == 0

            if not hostapd_running:
                return False

            # Check for our specific hotspot by verifying config file
            config_path = f'/etc/hostapd-prod/hostapd.conf'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_content = f.read()
                    return f'ssid={self.ssid}' in config_content

            return False

        except subprocess.SubprocessError as e:
            self._log_error(f"Subprocess error in status check: {str(e)}")
            return False
        except Exception as e:
            self._log_error(f"Unexpected error in status check: {str(e)}")
            return False

    def get_hostapd_pid(self):
        """Get PID of the hostapd process for this hotspot"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', f'hostapd.*{self.ssid}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
            return None
        except Exception:
            return None
    
    def get_connected_clients(self):
        """Get number of connected clients by parsing hostapd status"""
        try:
            pid = self.get_hostapd_pid()
            if not pid:
                return 0
                
            # Use hostapd_cli to get connected stations
            result = subprocess.run(
                ['hostapd_cli', '-p', '/var/run/hostapd', 'list_sta'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                return len([line for line in result.stdout.split('\n') 
                        if line.strip()])
            return 0
        except Exception:
            return 0

    def _log_error(self, message):
        """Helper method for consistent error logging"""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Hotspot {self.id} ({self.ssid}): {message}")
            
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