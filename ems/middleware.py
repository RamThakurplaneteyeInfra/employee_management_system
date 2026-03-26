"""
Middleware for GET response caching.
Caches 200 GET responses per (path, query, user).
Invalidates cache immediately on POST/PUT/PATCH/DELETE (2xx) so next GET returns fresh data.
"""
from django.utils.deprecation import MiddlewareMixin
from .cache_utils import (
    get_cached_response,
    set_cached_response,
    get_cache_key_for_request,
    invalidate_get_cache_for_prefix,
    invalidate_get_cache_for_prefix_all_users,
    get_path_prefixes_from_request,
    GLOBAL_INVALIDATE_GET_PREFIXES,
)

# Do not cache these path prefixes (admin, static, notifications GETs, logout, etc.)
CACHE_SKIP_PREFIXES = ("/admin/", "/static/", "/media/", "/notifications/", "/accounts/logout/")
MUTATION_METHODS = ("POST", "PUT", "PATCH", "DELETE")


class CacheGetMiddleware(MiddlewareMixin):
    """
    Cache GET responses and serve from cache when available.
    On POST/PUT/PATCH/DELETE success (2xx), invalidate GET cache for that path so next GET is fresh.
    Add after AuthenticationMiddleware so request.user is set.
    """

    def process_request(self, request):
        if request.method != "GET":
            return None
        if request.path.startswith(CACHE_SKIP_PREFIXES):
            return None
        cached = get_cached_response(request)
        if cached is not None:
            return cached
        request._cache_key = get_cache_key_for_request(request)
        return None

    def process_response(self, request, response):
        if request.path.startswith(CACHE_SKIP_PREFIXES):
            return response
        # Invalidate GET cache on mutation: per-user for most endpoints; all users for GLOBAL_INVALIDATE_GET_PREFIXES (e.g. alerts GET open to all)
        if request.method in MUTATION_METHODS and 200 <= response.status_code < 300:
            user_id = getattr(request.user, "pk", None) if getattr(request.user, "is_authenticated", False) else None
            for prefix in get_path_prefixes_from_request(request):
                if prefix in GLOBAL_INVALIDATE_GET_PREFIXES:
                    invalidate_get_cache_for_prefix_all_users(prefix)
                else:
                    invalidate_get_cache_for_prefix(prefix, user_id=user_id)
        if request.method == "GET" and getattr(request, "_cache_key", None) is not None and response.status_code == 200:
            set_cached_response(request, response)
        return response

# =============================================================================
# Prometheus Metrics
# Covers: HTTP, DB, cache, errors, GC, process, Python info, business metrics
# =============================================================================
import time
import os
from django.db.backends.signals import connection_created
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR,
)

# -- GC, process, python info are auto-collected by importing these collectors --
# GC_COLLECTOR      → python_gc_*
# PROCESS_COLLECTOR → process_virtual_memory_bytes, process_resident_memory_bytes,
#                     process_cpu_seconds_total, process_open_fds
# PLATFORM_COLLECTOR→ python_info

# ---------------------------------------------------------------------------
# HTTP metrics
# ---------------------------------------------------------------------------
_HTTP_TOTAL = Counter(
    "django_http_requests_total",
    "Total HTTP requests by method, endpoint, status",
    ["method", "endpoint", "status"],
)
_HTTP_DURATION = Histogram(
    "django_http_request_duration_seconds_ems",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
_HTTP_IN_PROGRESS = Gauge(
    "django_http_requests_in_progress",
    "Currently in-flight HTTP requests",
    ["method"],
)
_HTTP_ERRORS = Counter(
    "django_http_errors_total",
    "HTTP error responses (4xx and 5xx)",
    ["method", "endpoint", "status"],
)
_HTTP_RESPONSE_SIZE = Histogram(
    "django_http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1_000, 10_000, 100_000, 1_000_000],
)


# ---------------------------------------------------------------------------
# Cache metrics
# ---------------------------------------------------------------------------
_CACHE_HITS = Counter("django_cache_hits_total", "Cache hits")
_CACHE_MISSES = Counter("django_cache_misses_total", "Cache misses")

# ---------------------------------------------------------------------------
# Business / app-level metrics
# ---------------------------------------------------------------------------
_USER_LOGINS = Counter("app_user_logins_total", "Successful user logins")
_USER_REGISTRATIONS = Counter("app_user_registrations_total", "New user registrations")
_TASK_CREATED = Counter("app_tasks_created_total", "Tasks created")
_MSG_SENT = Counter("app_messages_sent_total", "Messages sent", ["type"])  # type: individual|group
_WS_ACTIVE = Gauge("app_ws_connections_active", "Active WebSocket connections", ["consumer"])
_WS_CONNECT = Counter("app_ws_connects_total", "WebSocket connect events", ["consumer"])
_WS_DISCONNECT = Counter("app_ws_disconnects_total", "WebSocket disconnect events", ["consumer"])


# ---------------------------------------------------------------------------
# HTTP middleware
# ---------------------------------------------------------------------------
def _norm(path: str) -> str:
    """Collapse numeric path segments to <id> to limit cardinality."""
    return "/".join("<id>" if p.isdigit() else p for p in path.split("/"))


class PrometheusMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path == "/metrics":
            return None
        request._prom_t = time.perf_counter()
        _HTTP_IN_PROGRESS.labels(method=request.method).inc()

    def process_response(self, request, response):
        if request.path == "/metrics":
            return response
        t = getattr(request, "_prom_t", None)
        if t is None:
            return response
        duration = time.perf_counter() - t
        endpoint = _norm(request.path)
        method = request.method
        status = str(response.status_code)

        _HTTP_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
        _HTTP_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        _HTTP_IN_PROGRESS.labels(method=method).dec()

        if response.status_code >= 400:
            _HTTP_ERRORS.labels(method=method, endpoint=endpoint, status=status).inc()

        if hasattr(response, "content") and response.content:
            _HTTP_RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(len(response.content))

        return response

    def process_exception(self, request, exception):
        endpoint = _norm(request.path)
        _HTTP_ERRORS.labels(method=request.method, endpoint=endpoint, status="500").inc()
        return None
