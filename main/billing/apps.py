from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    # Registering signals
    def ready(self):
        import billing.signals  # noqa