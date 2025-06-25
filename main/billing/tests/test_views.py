# billing/tests/test_views.py
import pytest
from django.urls import reverse
from rest_framework import status
from datetime import datetime, timedelta
from django.utils.timezone import make_aware, now
from billing.models import Plan, Subscription, Transaction
from accounts.enums import UserType
from tests.conftest_base import api_client, admin_user, reseller_user, customer_user

pytestmark = pytest.mark.django_db

# Helpers
def create_plan():
    return Plan.objects.create(name='Test Plan', price=9.99, duration_days=30)

# PLAN TESTS
def test_plan_list_view(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    create_plan()
    response = api_client.get(reverse('plans-list'))
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) > 0

def test_plan_create(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    data = {'name': 'Premium Plan', 'price': 19.99, 'duration_days': 60}
    response = api_client.post(reverse('plans-list'), data)
    assert response.status_code == status.HTTP_201_CREATED

def test_plan_create_restricted_for_non_admin(api_client, reseller_user):
    api_client.force_authenticate(user=reseller_user)
    data = {'name': 'Invalid Plan', 'price': 10.0, 'duration_days': 30}
    response = api_client.post(reverse('plans-list'), data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_plan_create_missing_fields(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(reverse('plans-list'), {'name': 'Incomplete'})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'price' in response.data
    assert 'duration_days' in response.data

def test_plan_detail(api_client, admin_user):
    plan = create_plan()
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(reverse('plans-detail', args=[plan.id]))
    assert response.status_code == status.HTTP_200_OK

def test_plan_update(api_client, admin_user):
    plan = create_plan()
    api_client.force_authenticate(user=admin_user)
    data = {'name': 'Updated Plan', 'price': 15.99, 'duration_days': 45}
    response = api_client.put(reverse('plans-detail', args=[plan.id]), data)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Updated Plan'

def test_plan_update_restricted_for_non_admin(api_client, reseller_user):
    plan = create_plan()
    api_client.force_authenticate(user=reseller_user)
    response = api_client.put(reverse('plans-detail', args=[plan.id]), {'name': 'Hack'})
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_plan_delete(api_client, admin_user):
    plan = create_plan()
    api_client.force_authenticate(user=admin_user)
    response = api_client.delete(reverse('plans-detail', args=[plan.id]))
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Plan.objects.filter(id=plan.id).exists()

def test_plan_delete_restricted_for_non_admin(api_client, customer_user):
    plan = create_plan()
    api_client.force_authenticate(user=customer_user)
    response = api_client.delete(reverse('plans-detail', args=[plan.id]))
    assert response.status_code == status.HTTP_403_FORBIDDEN

# SUBSCRIPTION TESTS
def test_subscription_list_view(api_client, customer_user):
    plan = create_plan()
    sub = Subscription.objects.create(user=customer_user, plan=plan, end_date=now() + timedelta(days=30))
    api_client.force_authenticate(user=customer_user)
    response = api_client.get(reverse('subscriptions-list'))
    assert response.status_code == status.HTTP_200_OK
    assert sub.id in [s['id'] for s in response.data]

def test_subscription_create(api_client, reseller_user, customer_user):
    api_client.force_authenticate(user=reseller_user)
    plan = create_plan()
    data = {
        "user": customer_user.id,
        "plan_id": plan.id,
        "end_date": (now() + timedelta(days=30)).isoformat(),
        "auto_renew": True
    }
    response = api_client.post(reverse('subscriptions-list'), data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

def test_subscription_create_invalid_user(api_client, customer_user):
    plan = create_plan()
    api_client.force_authenticate(user=customer_user)
    data = {
        "user": customer_user.id,
        "plan_id": plan.id,
        "end_date": (now() + timedelta(days=30)).isoformat(),
        "auto_renew": True
    }
    response = api_client.post(reverse('subscriptions-list'), data)
    assert response.status_code in [status.HTTP_403_FORBIDDEN, 400]  

def test_subscription_detail(api_client, customer_user):
    plan = create_plan()
    sub = Subscription.objects.create(user=customer_user, plan=plan, end_date='2099-12-31')
    api_client.force_authenticate(user=customer_user)
    response = api_client.get(reverse('subscriptions-detail', args=[sub.id]))
    assert response.status_code == status.HTTP_200_OK
    assert response.data['plan']['id'] == plan.id

def test_subscription_access_allowed_to_owner(api_client, reseller_user, customer_user):
    plan = create_plan()
    sub = Subscription.objects.create(user=customer_user, plan=plan, end_date='2099-12-31')
    api_client.force_authenticate(user=reseller_user)
    response = api_client.get(reverse('subscriptions-detail', args=[sub.id]))
    assert response.status_code == status.HTTP_200_OK
    
def test_subscription_access_denied_to_others(api_client, reseller_user, customer_user, django_user_model):
    plan = create_plan()
    sub = Subscription.objects.create(user=customer_user, plan=plan, end_date='2099-12-31')
    random_user = django_user_model.objects.create_user(username='random', password='pass1234')
    api_client.force_authenticate(user=random_user)
    response = api_client.get(reverse('subscriptions-detail', args=[sub.id]))
    assert response.status_code == status.HTTP_403_FORBIDDEN 

def test_subscription_delete(api_client, customer_user):
    plan = create_plan()
    sub = Subscription.objects.create(user=customer_user, plan=plan, end_date='2099-12-31')
    api_client.force_authenticate(user=customer_user)
    response = api_client.delete(reverse('subscriptions-detail', args=[sub.id]))
    assert response.status_code == status.HTTP_204_NO_CONTENT

# TRANSACTION TESTS
def test_transaction_list_view(api_client, reseller_user):
    tx = Transaction.objects.create(user=reseller_user, amount=100, transaction_type='DEP', reference='TX123')
    api_client.force_authenticate(user=reseller_user)
    response = api_client.get(reverse('transactions-list'))
    assert response.status_code == status.HTTP_200_OK
    assert tx.id in [t['id'] for t in response.data]

def test_transaction_filter_by_type(api_client, reseller_user):
    Transaction.objects.create(user=reseller_user, amount=100, transaction_type='DEP', reference='DEP001')
    Transaction.objects.create(user=reseller_user, amount=50, transaction_type='REF', reference='REF001')
    api_client.force_authenticate(user=reseller_user)
    response = api_client.get(reverse('transactions-list') + '?transaction_type=DEP')
    assert all(tx['transaction_type'] == 'DEP' for tx in response.data)
    assert len(response.data) == 1

def test_transaction_create(api_client, reseller_user):
    api_client.force_authenticate(user=reseller_user)
    data = {
        "user": reseller_user.id,
        "amount": 50.00,
        "transaction_type": "DEP",
        "reference": "TEST-REF-123",
        "description": "Initial deposit"
    }
    response = api_client.post(reverse('transactions-list'), data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

def test_transaction_create_missing_fields(api_client, reseller_user):
    api_client.force_authenticate(user=reseller_user)
    response = api_client.post(reverse('transactions-list'), {"amount": 100}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "transaction_type" in response.data
    assert "reference" in response.data

def test_transaction_detail(api_client, reseller_user):
    tx = Transaction.objects.create(user=reseller_user, amount=300, transaction_type='DEP', reference='TX300')
    api_client.force_authenticate(user=reseller_user)
    response = api_client.get(reverse('transactions-detail', args=[tx.id]))
    assert response.status_code == status.HTTP_200_OK
    assert float(response.data['amount']) == 300.0

def test_transaction_access_denied_to_others(api_client, reseller_user, customer_user):
    tx = Transaction.objects.create(user=reseller_user, amount=100, transaction_type='DEP', reference='SHARED123')
    api_client.force_authenticate(user=customer_user)
    response = api_client.get(reverse('transactions-detail', args=[tx.id]))
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

def test_transaction_delete(api_client, reseller_user):
    tx = Transaction.objects.create(user=reseller_user, amount=300, transaction_type='DEP', reference='TX300')
    api_client.force_authenticate(user=reseller_user)
    response = api_client.delete(reverse('transactions-detail', args=[tx.id]))
    assert response.status_code == status.HTTP_204_NO_CONTENT

# # billing/tests/test_views.py
# import pytest
# from django.urls import reverse
# from rest_framework import status
# from datetime import date, datetime, timedelta
# from django.utils.timezone import make_aware
# from billing.models import Plan, Subscription, Transaction
# from accounts.enums import UserType
# from tests.conftest_base import api_client, admin_user, reseller_user, customer_user

# aware_end_date = make_aware(datetime.now() + timedelta(days=2))

# pytestmark = pytest.mark.django_db

# # Plan tests
# def create_plan():
#     return Plan.objects.create(name='Test Plan', price=9.99, duration_days=30)

# def test_plan_list_view(api_client, admin_user):
#     api_client.force_authenticate(user=admin_user)
#     create_plan()
#     response = api_client.get(reverse('plans-list'))
#     assert response.status_code == status.HTTP_200_OK
#     assert len(response.data) > 0
    
# def test_plan_create(api_client, admin_user):
#     api_client.force_authenticate(user=admin_user)
#     data = {'name': 'Premium Plan', 'price': 19.99, 'duration_days': 60}
#     response = api_client.post(reverse('plans-list'), data)
#     assert response.status_code == status.HTTP_201_CREATED

# def test_plan_detail(api_client, admin_user):
#     plan = create_plan()
#     api_client.force_authenticate(user=admin_user)
#     response = api_client.get(reverse('plans-detail', args=[plan.id]))
#     assert response.status_code == status.HTTP_200_OK
#     assert response.data['name'] == plan.name

# def test_plan_update(api_client, admin_user):
#     plan = create_plan()
#     api_client.force_authenticate(user=admin_user)
#     data = {'name': 'Updated Plan', 'price': 15.99, 'duration_days': 45}
#     response = api_client.put(reverse('plans-detail', args=[plan.id]), data)
#     assert response.status_code == status.HTTP_200_OK
#     assert response.data['name'] == 'Updated Plan'

# def test_plan_delete(api_client, admin_user):
#     plan = create_plan()
#     api_client.force_authenticate(user=admin_user)
#     response = api_client.delete(reverse('plans-detail', args=[plan.id]))
#     assert response.status_code == status.HTTP_204_NO_CONTENT
#     assert not Plan.objects.filter(id=plan.id).exists()

# # Subscription tests
# def test_subscription_list_view(api_client, customer_user):
#     plan = create_plan()
#     sub = Subscription.objects.create(user=customer_user, plan=plan, end_date=aware_end_date)
#     api_client.force_authenticate(user=customer_user)
#     response = api_client.get(reverse('subscriptions-list'))
#     assert response.status_code == status.HTTP_200_OK
#     assert sub.id in [s['id'] for s in response.data]

# def test_subscription_create(api_client, reseller_user, customer_user):
#     api_client.force_authenticate(user=reseller_user)

#     plan = Plan.objects.create(name="Test Plan", duration_days=30, price=100.0)

#     data = {
#         "user": customer_user.id,
#         "plan_id": plan.id,  
#         "end_date": (datetime.now() + timedelta(days=30)).isoformat(),  
#         "auto_renew": True
#     }

#     response = api_client.post("/api/billing/subscriptions/", data, format="json")
#     print("Subscription Create Response:", response.status_code, response.json())
#     assert response.status_code == status.HTTP_201_CREATED

# def test_subscription_detail(api_client, customer_user):
#     plan = create_plan()
#     sub = Subscription.objects.create(user=customer_user, plan=plan, end_date='2099-12-31')
#     api_client.force_authenticate(user=customer_user)
#     response = api_client.get(reverse('subscriptions-detail', args=[sub.id]))
#     assert response.status_code == status.HTTP_200_OK
#     assert response.data['plan']['id'] == plan.id

# def test_subscription_delete(api_client, customer_user):
#     plan = create_plan()
#     sub = Subscription.objects.create(user=customer_user, plan=plan, end_date='2099-12-31')
#     api_client.force_authenticate(user=customer_user)
#     response = api_client.delete(reverse('subscriptions-detail', args=[sub.id]))
#     assert response.status_code == status.HTTP_204_NO_CONTENT

# # Transactions Tests
# def test_transaction_list_view(api_client, reseller_user):
#     tx = Transaction.objects.create(
#         user=reseller_user,
#         amount=100,
#         transaction_type='DEP',
#         reference='TX123',
#     )
#     api_client.force_authenticate(user=reseller_user)
#     response = api_client.get(reverse('transactions-list'))
#     assert response.status_code == status.HTTP_200_OK
#     assert tx.id in [t['id'] for t in response.data]

# def test_transaction_filter_by_type(api_client, reseller_user):
#     Transaction.objects.create(
#         user=reseller_user, amount=100, transaction_type='DEP', reference='DEP001'
#     )
#     Transaction.objects.create(
#         user=reseller_user, amount=50, transaction_type='REF', reference='REF001'
#     )
#     api_client.force_authenticate(user=reseller_user)
#     response = api_client.get(reverse('transactions-list') + '?transaction_type=DEP')
#     assert all(tx['transaction_type'] == 'DEP' for tx in response.data)
    
# def test_transaction_create(api_client, reseller_user):
#     api_client.force_authenticate(user=reseller_user)

#     data = {
#         "user": reseller_user.id,
#         "amount": 50.00,
#         "transaction_type": "DEP",  
#         "reference": "TEST-REF-123",  
#         "description": "Initial deposit"
#     }

#     response = api_client.post("/api/billing/transactions/", data, format="json")
#     print("Transaction Create Response:", response.status_code, response.json())
#     assert response.status_code == status.HTTP_201_CREATED

# def test_transaction_detail(api_client, reseller_user):
#     tx = Transaction.objects.create(
#         user=reseller_user, amount=300, transaction_type='DEP', reference='TX300'
#     )
#     api_client.force_authenticate(user=reseller_user)
#     response = api_client.get(reverse('transactions-detail', args=[tx.id]))
#     assert response.status_code == status.HTTP_200_OK
#     assert float(response.data['amount']) == 300.0

# def test_transaction_delete(api_client, reseller_user):
#     tx = Transaction.objects.create(
#         user=reseller_user, amount=300, transaction_type='DEP', reference='TX300'
#     )
#     api_client.force_authenticate(user=reseller_user)
#     response = api_client.delete(reverse('transactions-detail', args=[tx.id]))
#     assert response.status_code == status.HTTP_204_NO_CONTENT