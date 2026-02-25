from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    def ready(self):
        import accounts.signals
        from ems.cache_invalidation import connect_cache_invalidation
        connect_cache_invalidation()