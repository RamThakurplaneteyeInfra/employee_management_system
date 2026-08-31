"""
Set PostgreSQL search_path on every new database connection.
Required when using Neon pooler (or other poolers that disallow startup parameter "search_path").
Uses Django's connection_created signal so the path is applied globally for all connections.

Also optionally verifies auth_user is visible (warn by default; raise if DB_SEARCH_PATH_STRICT=1).
"""
from __future__ import annotations

import logging
import os

from django.db.backends.signals import connection_created

from ems.db_search_path import format_search_path_sql

logger = logging.getLogger(__name__)


def _set_search_path(sender, connection, **kwargs):
    if connection.vendor != "postgresql":
        return
    sql = format_search_path_sql(connection.ops)
    if not sql:
        return
    with connection.cursor() as cursor:
        cursor.execute(sql)
        _maybe_verify_auth_user(cursor)


def _maybe_verify_auth_user(cursor) -> None:
    """Confirm auth_user resolves after search_path (pool / env misconfig guard)."""
    try:
        cursor.execute("SELECT to_regclass('auth_user')")
        row = cursor.fetchone()
        found = row[0] if row else None
    except Exception as exc:
        logger.warning("DB search_path auth_user check failed: %s", exc)
        return

    if found:
        return

    msg = (
        "relation auth_user is not visible after SET search_path. "
        "Check DB_SEARCH_PATH (must list the schema that owns auth_user first, "
        "e.g. login_details). Empty env values are ignored and fall back to default."
    )
    strict = (os.getenv("DB_SEARCH_PATH_STRICT") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if strict:
        raise RuntimeError(msg)
    logger.error(msg)


connection_created.connect(_set_search_path)
