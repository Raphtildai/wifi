from django.contrib import admin
from .models import Plan, Subscription, Transaction

# Register your models here.
admin.site.register([Plan, Subscription, Transaction])
