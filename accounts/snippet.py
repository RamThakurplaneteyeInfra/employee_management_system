

from functools import wraps

from django.http import HttpRequest, HttpResponseForbidden, JsonResponse


def admin_required(view_func):
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
            return view_func(request,*args,**kwargs)

        
        return HttpResponseForbidden("Admin access only")
    return wrapper