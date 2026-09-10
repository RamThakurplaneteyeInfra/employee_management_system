"""
Failed-login rate limiting for POST /accounts/login/.

Limits by client IP and by username (whichever hits the cap first).
Uses Django's default cache (Redis when REDIS_URL is set) plus a process-local
fallback so limits still apply if Redis is down / IGNORE_EXCEPTIONS swallows errors.
Successful login clears both counters. Failed auth increments them.
"""
import threading
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest

_lock = threading.Lock()
# key -> (count, expires_at_epoch)
_local_counts = {}


def login_rate_limit_attempts():
    return max(1, int(getattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 5)))


def login_rate_limit_window_seconds():
    return max(60, int(getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300)))


def get_client_ip(request: HttpRequest) -> str:
    """Best-effort client IP (first X-Forwarded-For hop, else REMOTE_ADDR)."""
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    return (request.META.get("REMOTE_ADDR") or "").strip() or "unknown"


def _cache_keys(ip, username):
    keys = ["login_fail:ip:%s" % ip]
    u = (username or "").strip().lower()
    if u:
        keys.append("login_fail:user:%s" % u)
    return keys


def _local_get(key):
    now = time.time()
    with _lock:
        item = _local_counts.get(key)
        if not item:
            return 0
        count, exp = item
        if now > exp:
            _local_counts.pop(key, None)
            return 0
        return int(count)


def _local_incr(key, window):
    now = time.time()
    with _lock:
        item = _local_counts.get(key)
        if not item or now > item[1]:
            _local_counts[key] = (1, now + window)
            return 1
        count, exp = item
        count = int(count) + 1
        _local_counts[key] = (count, exp)
        return count


def _local_delete(key):
    with _lock:
        _local_counts.pop(key, None)


def _local_ttl(key):
    """Seconds remaining on the local counter, or 0 if missing/expired."""
    now = time.time()
    with _lock:
        item = _local_counts.get(key)
        if not item:
            return 0
        _count, exp = item
        if now > exp:
            return 0
        return max(0, int(exp - now))


def _remote_get(key):
    try:
        return int(cache.get(key) or 0)
    except Exception:
        return 0


def _remote_ttl(key):
    """Seconds remaining on the Redis/cache key (django-redis ttl), or 0."""
    try:
        ttl = cache.ttl(key)
        if ttl is None or int(ttl) < 0:
            return 0
        return int(ttl)
    except Exception:
        return 0


def _get_count(key):
    return max(_remote_get(key), _local_get(key))


def is_login_rate_limited(ip, username):
    limit = login_rate_limit_attempts()
    for key in _cache_keys(ip, username):
        if _get_count(key) >= limit:
            return True
    return False


def remaining_retry_seconds(ip, username):
    """
    Seconds until the active lockout expires.
    Uses the longest remaining TTL among IP/username keys that are over the limit.
    """
    limit = login_rate_limit_attempts()
    remaining = 0
    for key in _cache_keys(ip, username):
        if _get_count(key) >= limit:
            remaining = max(remaining, _local_ttl(key), _remote_ttl(key))
    if remaining <= 0:
        return login_rate_limit_window_seconds()
    return remaining


def record_failed_login(ip, username):
    window = login_rate_limit_window_seconds()
    for key in _cache_keys(ip, username):
        local_count = _local_incr(key, window)
        try:
            if cache.add(key, 1, window):
                continue
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, local_count, window)
        except Exception:
            # Redis may be down; local counter already updated.
            pass


def clear_failed_login(ip, username):
    for key in _cache_keys(ip, username):
        _local_delete(key)
        try:
            cache.delete(key)
        except Exception:
            pass


def rate_limit_response_payload(ip, username):
    """Build 429 body with actual remaining wait time for this IP/username."""
    seconds = remaining_retry_seconds(ip, username)
    # Ceil minutes for display (90s -> 2 minutes); keep 1 when any wait remains.
    minutes = max(1, (seconds + 59) // 60) if seconds > 0 else 0
    return {
        "messege": (
            "Too many failed login attempts. "
            "Try again in %s minutes." % minutes
        ),
        "retry_after_seconds": seconds,
        "retry_after_minutes": minutes,
    }
