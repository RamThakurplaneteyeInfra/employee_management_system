"""
GET response caching and invalidation.
- Cache key from path + query + user so GET responses are cached per user.
- Invalidate by path prefix when data is created/updated.
"""
import hashlib
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings

CACHE_KEY_PREFIX = "get"
DEFAULT_TIMEOUT = getattr(settings, "CACHE_GET_TIMEOUT", 300)


def _build_get_cache_key(request):
    """Build a cache key for this GET request (path + query + user). Path included for prefix invalidation."""
    path = request.path
    # print("building the cache key")
    query = sorted(request.GET.items()) if request.GET else []
    query_str = "&".join(f"{k}={v}" for k, v in query)
    user_id = request.user.pk if request.user.is_authenticated else "none"
    raw = f"{query_str}:{user_id}"
    path_safe = path.replace("/", ":").strip(":") or "root"
    return f"{CACHE_KEY_PREFIX}:{path_safe}:{hashlib.md5(raw.encode()).hexdigest()}"


def get_cached_response(request):
    """Return cached HttpResponse for this GET request, or None if miss."""
    if request.method != "GET":
        return None
    key = _build_get_cache_key(request)
    data = cache.get(key)
    if data is None:
        return None
    # print("returning the cached response")
    return HttpResponse(
        content=data.get("content", b""),
        content_type=data.get("content_type", "application/json"),
    )


def set_cached_response(request, response, timeout=DEFAULT_TIMEOUT):
    """Cache the response for this GET request."""
    if request.method != "GET" or response.status_code != 200:
        return
    if getattr(response, "streaming", False):
        return
    key = _build_get_cache_key(request)
    # print("setting the cached response")
    data = {
        "content": response.content,
        "content_type": response.get("Content-Type", "application/json"),
    }
    cache.set(key, data, timeout=timeout)


def get_cache_key_for_request(request):
    """Expose cache key for attaching to request (used by middleware)."""
    return _build_get_cache_key(request)


def invalidate_get_cache_for_prefix(path_prefix):
    """
    Invalidate all GET cache entries whose path contains path_prefix.
    path_prefix: e.g. "accounts", "messaging", "tasks", "eventsapi", "notifications", "ActionableEntries"
    """
    if not path_prefix:
        return
    try:
        backend = getattr(cache, "_cache", None) or cache
        if hasattr(backend, "delete_pattern"):
            prefix_safe = path_prefix.replace("/", ":").strip(":")
            # Key format is get:path_safe:hash; path_safe uses : instead of /
            pattern = f"*{CACHE_KEY_PREFIX}:*{prefix_safe}*"
            backend.delete_pattern(pattern)
    except Exception:
        pass


def get_path_prefixes_from_request(request):
    """
    Return specific GET path prefixes to invalidate for this mutation request.
    Uses _MUTATION_PATH_TO_GET_PREFIXES for granular invalidation; falls back to first segment.
    """
    path = (request.path or "").strip("/")
    if not path:
        return []
    path_safe = path.replace("/", ":").strip(":")
    path_with_slash = "/" + path
    # Check for specific mutation → affected GET prefixes (more specific than whole app)
    for mutation_prefix, get_prefixes in _MUTATION_PATH_TO_GET_PREFIXES:
        match_prefix = mutation_prefix.replace(":", "/")
        if path_safe.startswith(mutation_prefix) or path_with_slash.startswith("/" + match_prefix):
            return list(get_prefixes)
    # Fallback: first URL segment (e.g. "tasks", "accounts")
    first = path.split("/")[0]
    return [first] if first else []


# Mutation path prefix (path_safe format) → list of GET path_safe prefixes to invalidate.
# Order matters: more specific (e.g. tasks:changeStatus) before generic (e.g. changeStatus).
_MUTATION_PATH_TO_GET_PREFIXES = [
    # task_management: create/update/delete/change status → only task list and count
    ("tasks:createTask", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:updateTask", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:deleteTask", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:changeStatus", ["tasks:viewTasks", "tasks:viewAssignedTasks", "tasks:Taskcount"]),
    ("tasks:sendMessage", ["tasks:getMessage"]),
    # accounts
    ("accounts:admin:createEmployeeLogin", ["accounts:employees", "accounts:employee", "accounts:admin"]),
    ("accounts:admin:updateProfile", ["accounts:employees", "accounts:employee", "accounts:admin"]),
    ("accounts:admin:deleteEmployee", ["accounts:employees", "accounts:employee", "accounts:admin"]),
    ("accounts:admin:changePhoto", ["accounts:admin"]),
    ("accounts:updateUsername", ["accounts:employees", "accounts:employee"]),
    # events (birthday counter)
    ("eventsapi:events:birthdaycounter", ["eventsapi:events:birthdaycounter"]),
    # QuaterlyReports (root-mounted: addDayEntries, changeStatus, deleteEntry, ActionableEntries, etc.)
    ("addDayEntries", ["getUserEntries"]),
    ("changeStatus", ["getUserEntries"]),
    ("deleteEntry", ["getUserEntries"]),
    ("ActionableEntries", ["ActionableEntries"]),
    ("addMeetingHeadSubhead", ["getMonthlySchedule"]),
]
