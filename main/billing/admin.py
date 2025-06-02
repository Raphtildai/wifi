# billing/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Plan, Subscription, Transaction

User = get_user_model()

class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'data_limit', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    list_editable = ('is_active',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.user_type == 2:  # Reseller
            return qs.filter(is_active=True)  # Only show active plans to resellers
        return qs  # Admins see all plans

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active', 'auto_renew')
    list_filter = ('is_active', 'plan', 'start_date')
    search_fields = ('user__username', 'plan__name')
    readonly_fields = ('start_date',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:  # Admin
            return qs
        elif request.user.user_type == 2:  # Reseller
            return qs.filter(user__parent_reseller=request.user)
        return qs.none()  # Customers see nothing
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            if request.user.user_type == 2:  # Reseller
                kwargs["queryset"] = User.objects.filter(parent_reseller=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'timestamp', 'is_successful')
    list_filter = ('transaction_type', 'is_successful', 'timestamp')
    search_fields = ('user__username', 'reference', 'description')
    readonly_fields = ('timestamp', 'reference')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 1:  # Admin
            return qs
        elif request.user.user_type == 2:  # Reseller
            # Resellers see their own transactions and their customers' transactions
            return qs.filter(
                models.Q(user=request.user) | 
                models.Q(user__parent_reseller=request.user)
            )
        return qs.filter(user=request.user)  # Customers only see their own
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            if request.user.user_type == 2:  # Reseller
                kwargs["queryset"] = User.objects.filter(
                    models.Q(pk=request.user.pk) | 
                    models.Q(parent_reseller=request.user)
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Plan, PlanAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Transaction, TransactionAdmin)