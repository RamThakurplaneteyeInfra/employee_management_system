"""
Set PostgreSQL search_path on every new database connection.
Required when using Neon pooler (or other poolers that disallow startup parameter "search_path").
Uses Django's connection_created signal so the path is applied globally for all connections.
"""
from django.db.backends.signals import connection_created


def _set_search_path(sender, connection, **kwargs):
    from django.conf import settings

    path = getattr(settings, "DB_SEARCH_PATH", "public")
    schemas = [s.strip() for s in path.split(",") if s.strip()]
    if not schemas:
        return
    quoted = ", ".join(connection.ops.quote_name(s) for s in schemas)
    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {quoted}")


connection_created.connect(_set_search_path)
