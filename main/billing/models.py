# billing/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Plan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    duration_days = models.PositiveIntegerField(
        help_text="Plan duration in days"
    )
    data_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Data limit in MB (empty for unlimited)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Plans"
        ordering = ['price']
    
    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}'s {self.plan.name} subscription"

    # Helper methods to subscription models
    def is_currently_active(self):
        """Check if this specific subscription is currently active"""
        return self.is_active and self.end_date >= timezone.now()
    
    def renew(self, duration_days=None):
        """Renew the subscription"""
        duration = duration_days or self.plan.duration_days
        self.end_date = timezone.now() + timezone.timedelta(days=duration)
        self.is_active = True
        self.save()
    
    def cancel(self):
        """Cancel the subscription (set to inactive)"""
        self.is_active = False
        self.save()


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEP', _('Deposit')
        PURCHASE = 'PUR', _('Purchase')
        COMMISSION = 'COM', _('Commission')
        REFUND = 'REF', _('Refund')
    
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    transaction_type = models.CharField(
        max_length=3,
        choices=TransactionType.choices
    )
    reference = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    related_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='related_transactions'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount} for {self.user.username}"