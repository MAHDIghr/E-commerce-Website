from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
    verbose_name = "Administration My Line Collection"

    def ready(self):
        from . import signals  # noqa: F401
