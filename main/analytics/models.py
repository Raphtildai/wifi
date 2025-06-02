# analytics/models.py
from django.db import models
from django.contrib.auth import get_user_model
from hotspots.models import Hotspot
from accounts.enums import UserType

User = get_user_model()

class DailyUsage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_usage'
    )
    hotspot = models.ForeignKey(
        Hotspot,
        on_delete=models.CASCADE,
        related_name='daily_usage'
    )
    date = models.DateField()
    data_used = models.PositiveIntegerField(
        default=0,
        help_text="Data used in MB"
    )
    session_count = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Daily Usage"
        verbose_name_plural = "Daily Usage"
        unique_together = ('user', 'hotspot', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} usage on {self.date}"


class RevenueRecord(models.Model):
    reseller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='revenue_records',
        limit_choices_to={'user_type__in': [UserType.ADMIN, UserType.RESELLER]}
    )
    date = models.DateField()
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    commissions_earned = models.DecimalField(max_digits=10, decimal_places=2)
    new_customers = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Revenue Record"
        verbose_name_plural = "Revenue Records"
        unique_together = ('reseller', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"Revenue for {self.reseller.username} on {self.date}"