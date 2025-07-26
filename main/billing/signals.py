from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Subscription

@receiver(pre_save, sender=Subscription)
def check_subscription_expiry(sender, instance, **kwargs):
    """Automatically deactivate expired subscriptions"""
    if instance.end_date < timezone.now():
        instance.is_active = False