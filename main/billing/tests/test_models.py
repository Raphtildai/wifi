import pytest
from decimal import Decimal
from django.utils.timezone import now, timedelta
from billing.models import Plan, Subscription, Transaction
from tests.conftest_base import api_client, admin_user, reseller_user, customer_user

pytestmark = pytest.mark.django_db


def test_plan_creation():
    plan = Plan.objects.create(
        name="Basic Plan",
        price=Decimal("9.99"),
        duration_days=30,
        description="Simple data plan",
        data_limit=1024,
    )
    assert plan.name == "Basic Plan"
    assert plan.price == Decimal("9.99")
    assert plan.duration_days == 30
    assert plan.data_limit == 1024
    assert plan.is_active is True
    assert str(plan) == "Basic Plan"


def test_subscription_creation(customer_user):
    plan = Plan.objects.create(name="Monthly", price=10, duration_days=30)
    end = now() + timedelta(days=30)
    sub = Subscription.objects.create(
        user=customer_user,
        plan=plan,
        end_date=end,
        auto_renew=True,
    )
    assert sub.user == customer_user
    assert sub.plan == plan
    assert sub.end_date.date() == end.date()
    assert sub.auto_renew is True
    assert sub.is_active is True
    assert str(sub) == f"{customer_user.first_name} {customer_user.last_name}'s {plan.name} subscription"


def test_transaction_creation(reseller_user, customer_user):
    tx = Transaction.objects.create(
        user=reseller_user,
        amount=Decimal("100.00"),
        transaction_type=Transaction.TransactionType.DEPOSIT,
        reference="REF001",
        description="Initial deposit",
        related_user=customer_user,
    )
    assert tx.user == reseller_user
    assert tx.related_user == customer_user
    assert tx.amount == Decimal("100.00")
    assert tx.transaction_type == "DEP"
    assert tx.is_successful is True
    assert str(tx) == f"Deposit of 100.00 for {reseller_user.username}"
