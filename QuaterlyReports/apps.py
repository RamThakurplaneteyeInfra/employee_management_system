from django.apps import AppConfig


class QuaterlyreportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'QuaterlyReports'

    def ready(self):
        import QuaterlyReports.signals  # noqa: F401
