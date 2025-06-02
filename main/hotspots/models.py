# hotspots/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from accounts.enums import UserType

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Hotspot"
        verbose_name_plural = "Hotspots"
        unique_together = ('owner', 'ssid')
    
    def __str__(self):
        return f"{self.ssid} at {self.location.name}"


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