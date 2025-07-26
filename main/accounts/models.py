# accounts/models.py
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .enums import UserType

@property
def is_admin(self):
    return self.is_authenticated and (self.is_superuser or self.user_type == 1)

@property
def is_reseller(self):
    return self.is_authenticated and self.user_type == 2

@property
def is_customer(self):
    return self.is_authenticated and self.user_type == 3

class User(AbstractUser):
    user_type = models.PositiveSmallIntegerField(
        choices=UserType.choices,
        default=UserType.CUSTOMER
    )
    credit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Account balance in currency"
    )
    parent_reseller = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sub_accounts',
        limit_choices_to={'user_type': UserType.RESELLER}
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_user_type_display()})"

    # Checking Subscription
    def has_active_subscription(self):
        """
        Check if user has an active subscription based on:
        1. Active subscription record
        2. Subscription end date
        3. Account credit (for pay-as-you-go)
        """
        # Check for active time-based subscription
        active_subscription = self.subscriptions.filter(
            is_active=True,
            end_date__gte=timezone.now()
        ).exists()
        
        if active_subscription:
            return True
            
        # For customers, check if they have positive credit (pay-as-you-go)
        if self.user_type == UserType.CUSTOMER and self.credit > 0:
            return True
            
        return False

    def get_active_subscription(self):
        """Get the user's current active subscription if it exists"""
        return self.subscriptions.filter(
            is_active=True,
            end_date__gte=timezone.now()
        ).first()

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    company_name = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Commission percentage for resellers"
    )
    
    def __str__(self):
        return f"Profile of {self.user.username}"