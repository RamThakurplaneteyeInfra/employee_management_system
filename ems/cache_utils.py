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
    """Build a cache key for this GET request: get:<user_id>:<path_safe>:<hash>. User_id in key so invalidation can target one user."""
    path = request.path
    query = sorted(request.GET.items()) if request.GET else []
    query_str = "&".join(f"{k}={v}" for k, v in query)
    user_id = request.user.pk if request.user.is_authenticated else "anon"
    path_safe = path.replace("/", ":").strip(":") or "root"
    raw = query_str or ""
    key_hash = hashlib.md5(raw.encode()).hexdigest()
    return f"{CACHE_KEY_PREFIX}:{user_id}:{path_safe}:{key_hash}"


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


def invalidate_get_cache_for_prefix(path_prefix, user_id=None, user_ids=None):
    """
    Invalidate GET cache entries whose path contains path_prefix, optionally limited to specific user(s).
    Key format: get:<user_id>:<path_safe>:<hash>
    - path_prefix: e.g. "accounts", "tasks", "eventsapi:events:birthdaycounter"
    - user_id: single user pk; only that user's cache for this prefix is invalidated.
    - user_ids: list of user pks; only those users' caches are invalidated. If both user_id and user_ids are None, no keys are deleted (caller must pass affected users to avoid clearing other users' cache).
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
        backend = getattr(cache, "_cache", None) or cache
        if not hasattr(backend, "delete_pattern"):
            return
        prefix_safe = path_prefix.replace("/", ":").strip(":")
        for uid in set(ids_to_invalidate):
            pattern = f"*{CACHE_KEY_PREFIX}:{uid}:*{prefix_safe}*"
            backend.delete_pattern(pattern)
    except Exception:
        pass


def invalidate_birthday_counter_cache(user_id=None, user_ids=None):
    """
    Invalidate GET cache entries for the birthday counter API, optionally limited to specific user(s).
    Call after bulk or single birthday_counter updates. Pass user_ids of users whose counter changed
    so only their cache is invalidated.
    """
    prefix = "eventsapi:events:birthdaycounter"
    invalidate_get_cache_for_prefix(prefix, user_id=user_id, user_ids=user_ids)


def invalidate_missed_calls_count_cache(user_id=None, user_ids=None):
    """
    Invalidate GET cache entries for the missed calls count API, optionally limited to specific user(s).
    Call after resetMissedCallsCount so the next GET missedCallsCount returns fresh data.
    """
    prefix = "messaging:missedCallsCount"
    invalidate_get_cache_for_prefix(prefix, user_id=user_id, user_ids=user_ids)


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
