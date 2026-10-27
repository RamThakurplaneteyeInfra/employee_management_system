"""
PostgreSQL backend that sets search_path on every cursor.

Neon’s pooler can reset session state between transactions, so search_path must
be applied on each cursor. DB_SEARCH_PATH should list the schema containing
auth_user first, then the other app schemas.
"""
from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper

from ems.db_search_path import format_search_path_sql


class DatabaseWrapper(PostgresDatabaseWrapper):
    """Django PostgreSQL backend that sets search_path whenever a cursor is used."""

    def create_cursor(self, name=None):
        cursor = super().create_cursor(name=name)
        sql = format_search_path_sql(self.ops)
        if sql:
            cursor.execute(sql)
        return cursor
