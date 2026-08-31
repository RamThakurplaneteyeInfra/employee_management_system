"""
Shared PostgreSQL search_path helpers for schema-based EMS databases.

auth_user / django_session live outside public (typically login_details).
Empty DB_SEARCH_PATH env must not wipe the default — Neon/Railway often set
blank vars which would otherwise skip SET search_path and cause:
  ProgrammingError: relation "auth_user" does not exist
"""

from __future__ import annotations

DEFAULT_DB_SEARCH_PATH = (
    "login_details,emp_assessment,alerts,clients,events,task_management,"
    "notifications,project,quatery_reports,messaging,team_farm,team_infra,"
    "team_interns,team_management,customer_panel"
)


def resolve_db_search_path(raw: str | None = None) -> str:
    """
    Resolve search_path string.

    - None → use settings.DB_SEARCH_PATH when Django is configured, else default
    - blank / whitespace → default (never return empty)
    """
    if raw is None:
        try:
            from django.conf import settings

            if settings.configured:
                raw = getattr(settings, "DB_SEARCH_PATH", None)
        except Exception:
            raw = None
    path = (raw or "").strip()
    return path or DEFAULT_DB_SEARCH_PATH


def search_path_schemas(raw: str | None = None) -> list[str]:
    resolved = resolve_db_search_path(raw)
    return [s.strip() for s in resolved.split(",") if s.strip()]


def format_search_path_sql(ops, raw: str | None = None) -> str | None:
    schemas = search_path_schemas(raw)
    if not schemas:
        return None
    quoted = ", ".join(ops.quote_name(s) for s in schemas)
    return f"SET search_path TO {quoted}"
