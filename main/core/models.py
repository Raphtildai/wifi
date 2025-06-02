# core/models.py
from django.db import models

class SystemConfiguration(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'core'  # Add this line
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configurations"
    
    def __str__(self):
        return self.key


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('ACCESS', 'Access'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        app_label = 'core'  # Add this line
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_action_display()} on {self.model} by {self.user}"