"""
Middleware for GET response caching.
Caches 200 GET responses per (path, query, user). Invalidation via cache_utils.invalidate_get_cache_for_prefix.
"""
from django.utils.deprecation import MiddlewareMixin
from .cache_utils import get_cached_response, set_cached_response, get_cache_key_for_request

# Do not cache these path prefixes (admin, static, etc.)
CACHE_SKIP_PREFIXES = ("/admin/", "/static/", "/media/")


class CacheGetMiddleware(MiddlewareMixin):
    """
    Cache GET responses and serve from cache when available.
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
        if request.method != "GET" or request.path.startswith(CACHE_SKIP_PREFIXES):
            return response
        if getattr(request, "_cache_key", None) is not None and response.status_code == 200:
            set_cached_response(request, response)
        return response
