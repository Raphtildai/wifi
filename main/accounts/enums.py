# accounts/enums.py
from django.utils.translation import gettext_lazy as _
from django.db import models

class UserType(models.IntegerChoices):
    ADMIN = 1, _('Admin')
    RESELLER = 2, _('Reseller')
    CUSTOMER = 3, _('Customer')