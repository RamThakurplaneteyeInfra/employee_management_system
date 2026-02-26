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
    get_path_prefixes_from_request,
)

# Do not cache these path prefixes (admin, static, etc.)
CACHE_SKIP_PREFIXES = ("/admin/", "/static/", "/media/")
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
        # Invalidate GET cache immediately after any mutation so next GET sees updated data
        if request.method in MUTATION_METHODS and 200 <= response.status_code < 300:
            for prefix in get_path_prefixes_from_request(request):
                invalidate_get_cache_for_prefix(prefix)
        if request.method == "GET" and getattr(request, "_cache_key", None) is not None and response.status_code == 200:
            set_cached_response(request, response)
        return response
