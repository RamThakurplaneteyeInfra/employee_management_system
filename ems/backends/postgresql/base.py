"""
PostgreSQL backend that sets search_path on every cursor.
Use this when using connection pooling (e.g. Neon, dj_db_conn_pool) so that
auth_user and other app schema tables are visible even when a connection is
reused from the pool and the session was reset. DB_SEARCH_PATH should list
the schema containing auth_user first, then other app schemas (no public).
"""
from django.conf import settings

from dj_db_conn_pool.backends.postgresql.base import DatabaseWrapper as PoolDatabaseWrapper


class DatabaseWrapper(PoolDatabaseWrapper):
    """Pool backend that ensures search_path is set whenever a cursor is used."""

    def create_cursor(self, name=None):
        cursor = super().create_cursor(name=name)
        path = getattr(settings, "DB_SEARCH_PATH", "public")
        schemas = [s.strip() for s in path.split(",") if s.strip()]
        if schemas:
            quoted = ", ".join(self.ops.quote_name(s) for s in schemas)
            cursor.execute(f"SET search_path TO {quoted}")
        return cursor
