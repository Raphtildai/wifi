# billing/services.py
from django.utils import timezone
from .models import Subscription

def create_subscription(user, plan):
    """Handle subscription creation with business logic"""
    end_date = timezone.now() + timezone.timedelta(days=plan.duration_days)
    return Subscription.objects.create(
        user=user,
        plan=plan,
        end_date=end_date,
        is_active=True
    )