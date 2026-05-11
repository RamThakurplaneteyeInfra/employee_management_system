"""
GET response caching and invalidation.
- Cache key from path + query + user so GET responses are cached per user.
- Invalidate by path prefix tag (Redis Set) — avoids O(N) SCAN on every mutation.
"""
import hashlib
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings

CACHE_KEY_PREFIX = "get"
CACHE_KEY_PREFIX_MESSAGING_SCOPE = "get:msg"
DEFAULT_TIMEOUT = getattr(settings, "CACHE_GET_TIMEOUT", 300)
TAG_TIMEOUT = DEFAULT_TIMEOUT + 300  # tag set lives slightly longer than cached values

_MESSAGING_SCOPE_PATH_PREFIXES = ("/messaging/getMessages/", "/messaging/showGroupMembers/")


def _get_messaging_scope_from_path(path):
    if not path or not path.startswith("/messaging/"):
        return None
    path_stripped = path.rstrip("/")
    for prefix in _MESSAGING_SCOPE_PATH_PREFIXES:
        if path_stripped.startswith(prefix):
            rest = path_stripped[len(prefix):].strip("/")
            if rest:
                return rest
    return None


def _tag_key(prefix_safe, uid):
    """Redis key for the Set that tracks all cache keys under this prefix+user."""
    return f"tag:{prefix_safe}:{uid}"


def _build_get_cache_key(request):
    path = request.path
    query = sorted(request.GET.items()) if request.GET else []
    query_str = "&".join(f"{k}={v}" for k, v in query)
    path_safe = path.replace("/", ":").strip(":") or "root"
    raw = query_str or ""
    key_hash = hashlib.md5(raw.encode()).hexdigest()

    scope_id = _get_messaging_scope_from_path(path)
    if scope_id is not None:
        return f"{CACHE_KEY_PREFIX_MESSAGING_SCOPE}:{scope_id}:{path_safe}:{key_hash}"
    user_id = request.user.pk if request.user.is_authenticated else "anon"
    return f"{CACHE_KEY_PREFIX}:{user_id}:{path_safe}:{key_hash}"


def _register_key_in_tags(cache_key, path, user_id):
    """Register cache_key in tag Sets so invalidation can delete directly without SCAN."""
    try:
        client = cache.client.get_client()
        path_safe = path.replace("/", ":").strip(":")
        first = path_safe.split(":")[0] if path_safe else ""
        if first:
            client.sadd(_tag_key(first, user_id), cache_key)
            client.expire(_tag_key(first, user_id), TAG_TIMEOUT)
        client.sadd(_tag_key(path_safe, user_id), cache_key)
        client.expire(_tag_key(path_safe, user_id), TAG_TIMEOUT)
    except Exception:
        pass


def get_cached_response(request):
    if request.method != "GET":
        return None
    key = _build_get_cache_key(request)
    data = cache.get(key)
    if data is None:
        return None
    return HttpResponse(
        content=data.get("content", b""),
        content_type=data.get("content_type", "application/json"),
    )


def set_cached_response(request, response, timeout=DEFAULT_TIMEOUT):
    if request.method != "GET" or response.status_code != 200:
        return
    if getattr(response, "streaming", False):
        return
    key = _build_get_cache_key(request)
    data = {
        "content": response.content,
        "content_type": response.get("Content-Type", "application/json"),
    }
    cache.set(key, data, timeout=timeout)
    user_id = request.user.pk if getattr(request.user, "is_authenticated", False) else "anon"
    _register_key_in_tags(key, request.path, user_id)


def get_cache_key_for_request(request):
    return _build_get_cache_key(request)


def invalidate_get_cache_for_prefix(path_prefix, user_id=None, user_ids=None):
    """
    Invalidate GET cache for path_prefix using tag Sets (O(1)) instead of SCAN (O(N)).
    """
    if not path_prefix:
        return
    ids_to_invalidate = []
    if user_id is not None:
        ids_to_invalidate.append(user_id)
    if user_ids:
        ids_to_invalidate.extend(user_ids)
    if not ids_to_invalidate:
        return
    try:
        client = cache.client.get_client()
        prefix_safe = path_prefix.replace("/", ":").strip(":")
        for uid in set(ids_to_invalidate):
            tag = _tag_key(prefix_safe, uid)
            keys = client.smembers(tag)
            if keys:
                client.delete(*keys)
            client.delete(tag)
    except Exception:
        # Fallback to delete_pattern
        try:
            backend = getattr(cache, "_cache", None) or cache
            if hasattr(backend, "delete_pattern"):
                prefix_safe = path_prefix.replace("/", ":").strip(":")
                for uid in set(ids_to_invalidate):
                    backend.delete_pattern(f"*{CACHE_KEY_PREFIX}:{uid}:*{prefix_safe}*")
        except Exception:
            pass


def invalidate_birthday_counter_cache(user_id=None, user_ids=None):
    invalidate_get_cache_for_prefix("eventsapi:events:birthdaycounter", user_id=user_id, user_ids=user_ids)


def invalidate_missed_calls_count_cache(user_id=None, user_ids=None):
    invalidate_get_cache_for_prefix("messaging:missedCallsCount", user_id=user_id, user_ids=user_ids)


GET_ALL_EMPLOYEES_PATH_PREFIX = "accounts:employees"
GLOBAL_INVALIDATE_GET_PREFIXES = frozenset({"alertsapi:alerts"})


def invalidate_get_cache_for_prefix_all_users(path_prefix):
    """Invalidate GET cache for path_prefix for all users. Scans only tag keys (small set)."""
    if not path_prefix:
        return
    try:
        client = cache.client.get_client()
        prefix_safe = path_prefix.replace("/", ":").strip(":")
        tag_pattern = f"tag:{prefix_safe}:*"
        cursor = 0
        while True:
            cursor, tag_keys = client.scan(cursor, match=tag_pattern, count=100)
            for tag in tag_keys:
                keys = client.smembers(tag)
                if keys:
                    client.delete(*keys)
                client.delete(tag)
            if cursor == 0:
                break
    except Exception:
        try:
            backend = getattr(cache, "_cache", None) or cache
            if hasattr(backend, "delete_pattern"):
                prefix_safe = path_prefix.replace("/", ":").strip(":")
                backend.delete_pattern(f"*{CACHE_KEY_PREFIX}:*:{prefix_safe}*")
        except Exception:
            pass


def invalidate_get_all_employees_cache():
    invalidate_get_cache_for_prefix_all_users(GET_ALL_EMPLOYEES_PATH_PREFIX)


def invalidate_get_cache_for_messaging_scope(scope_id):
    if not scope_id:
        return
    try:
        backend = getattr(cache, "_cache", None) or cache
        if hasattr(backend, "delete_pattern"):
            backend.delete_pattern(f"*{CACHE_KEY_PREFIX_MESSAGING_SCOPE}:{scope_id}:*")
    except Exception:
        pass


def get_path_prefixes_from_request(request):
    path = (request.path or "").strip("/")
    if not path:
        return []
    path_safe = path.replace("/", ":").strip(":")
    path_with_slash = "/" + path
    for mutation_prefix, get_prefixes in _MUTATION_PATH_TO_GET_PREFIXES:
        match_prefix = mutation_prefix.replace(":", "/")
        if path_safe.startswith(mutation_prefix) or path_with_slash.startswith("/" + match_prefix):
            return list(get_prefixes)
    first = path.split("/")[0]
    return [first] if first else []


_MUTATION_PATH_TO_GET_PREFIXES = [
    ("tasks:createTask", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:updateTask", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:deleteTask", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:changeStatus", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:sendMessage", ["tasks:getMessage"]),
    ("accounts:admin:createEmployeeLogin", ["accounts:employees", "accounts:employee", "accounts:admin"]),
    ("accounts:admin:updateProfile", ["accounts:employees", "accounts:employee", "accounts:admin"]),
    ("accounts:admin:deleteEmployee", ["accounts:employees", "accounts:employee", "accounts:admin"]),
    ("accounts:admin:changePhoto", ["accounts:admin"]),
    ("accounts:updateUsername", ["accounts:employees", "accounts:employee"]),
    ("alertsapi:alerts", ["alertsapi:alerts"]),
    ("alertsapi:announcements", ["alertsapi:announcements"]),
    ("alertsapi:attention", ["alertsapi:attention"]),
    ("eventsapi:events:birthdaycounter", ["eventsapi:events:birthdaycounter"]),
    ("addDayEntries", ["getUserEntries"]),
    ("changeStatus", ["getUserEntries"]),
    ("deleteEntry", ["getUserEntries"]),
    ("ActionableEntries", ["ActionableEntries"]),
    ("addMeetingHeadSubhead", ["getMonthlySchedule"]),
]
