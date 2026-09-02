from django.apps import AppConfig


class ManagedBackendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "managed_backend"
    verbose_name = "A+ Managed Backend"
