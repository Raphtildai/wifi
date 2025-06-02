# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .enums import UserType

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