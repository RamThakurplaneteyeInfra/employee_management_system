"""
WebSocket presence for /ws/notifications/ — Redis-backed, optional, fail-safe.

- Uses a per-username connection counter (multi-tab safe).
- Keys are separate from django-redis cache key hashing (raw Redis keys).
- Any Redis error is swallowed (logged); callers never crash on presence.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings

logger = logging.getLogger(__name__)

# Raw Redis keys (not passed through django-redis cache make_key).
_KEY_PREFIX = "ems:ws_presence:v1:cnt:"


def _ttl_seconds() -> int:
    return max(30, int(getattr(settings, "WS_PRESENCE_TTL_SECONDS", 120)))


def presence_enabled() -> bool:
    if not getattr(settings, "WS_PRESENCE_ENABLED", True):
        return False
    return bool(getattr(settings, "REDIS_URL", None))


def _counter_key(username: str) -> str | None:
    u = (username or "").strip()
    if not u:
        return None
    return f"{_KEY_PREFIX}{u}"


def _client():
    from django_redis import get_redis_connection

    return get_redis_connection("default")


def connect_presence(username: str) -> bool:
    """Increment active notification-WS count for user; refresh TTL. Returns False if skipped/failed."""
    if not presence_enabled():
        return False
    key = _counter_key(username)
    if not key:
        return False
    try:
        conn = _client()
        pipe = conn.pipeline()
        pipe.incr(key)
        pipe.expire(key, _ttl_seconds())
        pipe.execute()
        return True
    except Exception as exc:
        logger.warning("ws_presence connect failed user=%s: %s", username, exc)
        return False


def refresh_presence_ttl(username: str) -> None:
    """Refresh TTL (client ping)."""
    if not presence_enabled():
        return
    key = _counter_key(username)
    if not key:
        return
    try:
        conn = _client()
        if conn.exists(key):
            conn.expire(key, _ttl_seconds())
    except Exception as exc:
        logger.warning("ws_presence refresh failed user=%s: %s", username, exc)


def disconnect_presence(username: str) -> None:
    """Decrement on WS disconnect; remove key when count hits zero."""
    if not presence_enabled():
        return
    key = _counter_key(username)
    if not key:
        return
    try:
        conn = _client()
        if not conn.exists(key):
            return
        v = conn.decr(key)
        if v is not None and v <= 0:
            conn.delete(key)
    except Exception as exc:
        logger.warning("ws_presence disconnect failed user=%s: %s", username, exc)


def force_presence_offline(username: str) -> None:
    """Clear presence immediately (e.g. explicit logout)."""
    if not presence_enabled():
        return
    key = _counter_key(username)
    if not key:
        return
    try:
        _client().delete(key)
    except Exception as exc:
        logger.warning("ws_presence force_offline failed user=%s: %s", username, exc)


def ws_online_map(usernames: Iterable[str]) -> dict[str, bool]:
    """
    Return {username: bool} for active notification WS (count > 0 and key exists).
    Unknown users omitted. Fail-soft: on error returns all False for requested names.
    """
    names = [str(u).strip() for u in usernames if u and str(u).strip()]
    if not names or not presence_enabled():
        return {n: False for n in names}
    keys = [(n, _counter_key(n)) for n in names]
    keys = [(n, k) for n, k in keys if k]
    if not keys:
        return {n: False for n in names}
    try:
        conn = _client()
        raw_keys = [k for _, k in keys]
        values = conn.mget(raw_keys)
        out: dict[str, bool] = {n: False for n in names}
        for (username, _k), val in zip(keys, values):
            try:
                n = int(val) if val is not None else 0
            except (TypeError, ValueError):
                n = 0
            out[username] = n > 0
        return out
    except Exception as exc:
        logger.warning("ws_presence mget failed: %s", exc)
        return {n: False for n in names}
