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
CACHE_KEY_PREFIX_MESSAGING_SCOPE = "get:msg"
DEFAULT_TIMEOUT = getattr(settings, "CACHE_GET_TIMEOUT", 300)

# Messaging GET paths that are scoped by chat_id or group_id (segment after the path prefix).
_MESSAGING_SCOPE_PATH_PREFIXES = ("/messaging/getMessages/", "/messaging/showGroupMembers/")


def _get_messaging_scope_from_path(path):
    """
    If path is a messaging GET that includes chat_id or group_id (e.g. /messaging/getMessages/G-123/),
    return that scope id (chat_id or group_id). Otherwise return None.
    """
    if not path or not path.startswith("/messaging/"):
        return None
    path_stripped = path.rstrip("/")
    for prefix in _MESSAGING_SCOPE_PATH_PREFIXES:
        if path_stripped.startswith(prefix):
            rest = path_stripped[len(prefix):].strip("/")
            if rest:
                return rest
    return None


def _build_get_cache_key(request):
    """
    Build a cache key for this GET request.
    - Messaging GET with chat_id/group_id in path: get:msg:<scope_id>:<path_safe>:<hash>
    - All other GET: get:<user_id>:<path_safe>:<hash>
    """
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


# Path prefix for GET accounts/employees/ (user-free: invalidate for all users when anyone logs in).
GET_ALL_EMPLOYEES_PATH_PREFIX = "accounts:employees"

# GET path prefixes that are invalidated for all users (and anon) when any mutation hits them (e.g. alerts GET is open to all).
GLOBAL_INVALIDATE_GET_PREFIXES = frozenset({"alertsapi:alerts"})


def invalidate_get_cache_for_prefix_all_users(path_prefix):
    """
    Invalidate GET cache for path_prefix for every user (and anon).
    Use when the GET endpoint is open to all so any mutation should clear all cached responses.
    """
    if not path_prefix:
        return
    try:
        backend = getattr(cache, "_cache", None) or cache
        if not hasattr(backend, "delete_pattern"):
            return
        prefix_safe = path_prefix.replace("/", ":").strip(":")
        pattern = f"*{CACHE_KEY_PREFIX}:*:{prefix_safe}*"
        backend.delete_pattern(pattern)
    except Exception:
        pass


def invalidate_get_all_employees_cache():
    """
    Invalidate GET cache for accounts/employees/ for all users (user-free).
    Call on login so the next GET {{baseurl}}/accounts/employees/ returns fresh data for every user.
    """
    if not GET_ALL_EMPLOYEES_PATH_PREFIX:
        return
    try:
        backend = getattr(cache, "_cache", None) or cache
        if not hasattr(backend, "delete_pattern"):
            return
        prefix_safe = GET_ALL_EMPLOYEES_PATH_PREFIX.replace("/", ":").strip(":")
        # Match get:<any_user_id>:accounts:employees:* so all users' cache for this endpoint is cleared
        pattern = f"*{CACHE_KEY_PREFIX}:*:{prefix_safe}*"
        backend.delete_pattern(pattern)
    except Exception:
        pass


def invalidate_get_cache_for_messaging_scope(scope_id):
    """
    Invalidate all GET cache entries for messaging endpoints tied to this chat_id or group_id.
    Key format for messaging-scoped GET: get:msg:<scope_id>:<path_safe>:<hash>
    Clears getMessages/<scope_id>/ and showGroupMembers/<scope_id>/ and any other GET under that scope.
    """
    if not scope_id:
        return
    try:
        backend = getattr(cache, "_cache", None) or cache
        if not hasattr(backend, "delete_pattern"):
            return
        pattern = f"*{CACHE_KEY_PREFIX_MESSAGING_SCOPE}:{scope_id}:*"
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
    # Alerts: POST/PUT/PATCH/DELETE on alerts invalidate GET alerts list/detail
    ("alertsapi:alerts", ["alertsapi:alerts"]),
    # Announcements: POST/PUT/PATCH/DELETE on announcements invalidate GET announcements list/detail
    ("alertsapi:announcements", ["alertsapi:announcements"]),
    # Attention: POST/PUT/PATCH/DELETE on attention invalidate GET attention list/detail
    ("alertsapi:attention", ["alertsapi:attention"]),
    # events (birthday counter)
    ("eventsapi:events:birthdaycounter", ["eventsapi:events:birthdaycounter"]),
    # QuaterlyReports (root-mounted: addDayEntries, changeStatus, deleteEntry, ActionableEntries, etc.)
    ("addDayEntries", ["getUserEntries"]),
    ("changeStatus", ["getUserEntries"]),
    ("deleteEntry", ["getUserEntries"]),
    ("ActionableEntries", ["ActionableEntries"]),
    ("addMeetingHeadSubhead", ["getMonthlySchedule"]),
]
