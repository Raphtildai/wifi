import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from analytics.models import DailyUsage, RevenueRecord

@pytest.mark.django_db
class TestDailyUsageModel:
    def test_daily_usage_creation(self, daily_usage):
        assert daily_usage.pk is not None
        assert daily_usage.data_used == 500
        assert daily_usage.duration_seconds == 3600
        assert str(daily_usage) == f"{daily_usage.user.username} usage on {daily_usage.date}"

    def test_unique_together_constraint(self, reseller_user):
        RevenueRecord.objects.create(
            reseller=reseller_user,
            date=date.today(),
            total_sales=100.00,
            commissions_earned=10.00  # Add this
        )
        with pytest.raises(IntegrityError):
            RevenueRecord.objects.create(
                reseller=reseller_user,
                date=date.today(),
                total_sales=200.00,
                commissions_earned=20.00  # Add this
            )

    def test_ordering(self, customer_user, hotspot):
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        DailyUsage.objects.create(
            user=customer_user,
            hotspot=hotspot,
            date=yesterday,
            data_used=100
        )
        DailyUsage.objects.create(
            user=customer_user,
            hotspot=hotspot,
            date=today,
            data_used=200
        )
        
        usages = DailyUsage.objects.all()
        assert usages[0].date == today
        assert usages[1].date == yesterday

@pytest.mark.django_db
class TestRevenueRecordModel:
    def test_revenue_record_creation(self, revenue_record):
        assert revenue_record.pk is not None
        assert revenue_record.total_sales == 1000.00
        assert revenue_record.commissions_earned == 100.00
        assert str(revenue_record) == f"Revenue for {revenue_record.reseller.username} on {revenue_record.date}"

    def test_reseller_validation(self, customer_user):
        with pytest.raises(ValidationError):
            record = RevenueRecord(
                reseller=customer_user,  # Customer can't be reseller
                date=date.today(),
                total_sales=100.00
            )
            record.full_clean()

    def test_unique_together_constraint(self, reseller_user):
        RevenueRecord.objects.create(
            reseller=reseller_user,
            date=date.today(),
            total_sales=100.00,
            commissions_earned=10.00  
        )
        with pytest.raises(IntegrityError):
            RevenueRecord.objects.create(
                reseller=reseller_user,
                date=date.today(),
                total_sales=200.00,
                commissions_earned=20.00  
            )