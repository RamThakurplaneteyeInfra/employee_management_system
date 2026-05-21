
from functools import wraps
from asgiref.sync import iscoroutinefunction, sync_to_async
from django.http import HttpRequest, HttpResponseForbidden
# from django.views.decorators.csrf import csrf_exempt as _csrf_exempt


def _check_admin_sync(request):
    """Sync helper: returns 'ok' | 'login' | 'admin' for auth/admin checks."""
    if not request.user.is_authenticated:
        return "login"
    if not request.user.is_superuser:
        return "admin"
    return "ok"


def _check_auth_sync(request):
    """Sync helper: access request.user without triggering SynchronousOnlyOperation in async context."""
    return request.user.is_authenticated


def _check_admin_or_hr_sync(request):
    """Sync helper: returns 'ok' | 'login' | 'forbidden' for create-employee access."""
    if not request.user.is_authenticated:
        return "login"
    if request.user.is_superuser:
        return "ok"
    from accounts.filters import _get_user_role_sync

    role = _get_user_role_sync(request.user)
    if role in ("Admin", "MD", "HR", "Hr"):
        return "ok"
    return "forbidden"


def admin_required(view_func):
    """Supports both sync and async views."""
    if iscoroutinefunction(view_func):
        @wraps(view_func)
        async def async_wrapper(request: HttpRequest, *args, **kwargs):
            status = await sync_to_async(_check_admin_sync)(request)
            if status == "login":
                return HttpResponseForbidden("Login required")
            if status == "admin":
                return HttpResponseForbidden("Admin access only")
            return await view_func(request, *args, **kwargs)
        return async_wrapper

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        """
        This function is a wrapper that takes an HttpRequest object as input along with additional
        arguments and keyword arguments.
        
        :param request: HttpRequest object that represents the incoming HTTP request from the client. It
        contains information such as headers, method, body, and other request details
        :type request: HttpRequest
        """
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Login required")
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Admin access only")
    return wrapper


def admin_or_hr_required(view_func):
    """Superuser or Profile role Admin/MD/HR. Used only for create-employee; other admin views stay admin_required."""
    if iscoroutinefunction(view_func):
        @wraps(view_func)
        async def async_wrapper(request: HttpRequest, *args, **kwargs):
            access = await sync_to_async(_check_admin_or_hr_sync)(request)
            if access == "login":
                return HttpResponseForbidden("Login required")
            if access == "forbidden":
                return HttpResponseForbidden("Admin or HR access required")
            return await view_func(request, *args, **kwargs)
        return async_wrapper

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        access = _check_admin_or_hr_sync(request)
        if access == "login":
            return HttpResponseForbidden("Login required")
        if access == "forbidden":
            return HttpResponseForbidden("Admin or HR access required")
        return view_func(request, *args, **kwargs)

    return wrapper


def login_required(view_func):
    """Async-safe login required. Redirects unauthenticated users or returns 401."""
    if iscoroutinefunction(view_func):
        @wraps(view_func)
        async def async_wrapper(request: HttpRequest, *args, **kwargs):
            is_auth = await sync_to_async(_check_auth_sync)(request)
            if not is_auth:
                return HttpResponseForbidden("Login required")
            return await view_func(request, *args, **kwargs)
        return async_wrapper

    @wraps(view_func)
    def sync_wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Login required")
        return view_func(request, *args, **kwargs)
    return sync_wrapper

def csrf_exempt(view_func):
    """Async-safe csrf_exempt. Properly awaits async views to avoid unawaited coroutine errors."""
    if iscoroutinefunction(view_func):
        @wraps(view_func)
        async def async_wrapper(request: HttpRequest, *args, **kwargs):
            return await view_func(request, *args, **kwargs)
        async_wrapper.csrf_exempt = True
        return async_wrapper

    @wraps(view_func)
    def sync_wrapper(request: HttpRequest, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    sync_wrapper.csrf_exempt = True
    return sync_wrapper