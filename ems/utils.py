from datetime import date, datetime, timezone, timedelta

from django.contrib.auth import get_user_model
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

# Indian Standard Time (UTC+5:30) – for API responses across apps
IST = timezone(timedelta(hours=5, minutes=30))


def gmt_to_ist_str(dt, fmt="%d/%m/%y %H:%M:%S"):
    """Convert UTC/GMT datetime to IST and return formatted string. Handles date-only (DateField). Returns None if dt is None."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime("%d/%m/%y")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime(fmt)


def gmt_to_ist_date_str(dt):
    """IST date only: %d/%m/%y."""
    return gmt_to_ist_str(dt, "%d/%m/%y") if dt else None


def get_user_from_member(m):
    """
    Resolve API member payloads (client lead / customer panel) to a User instance.
    Accepts dict with id and/or username, bare user id (int or numeric string), or username string.
    """
    User = get_user_model()
    uid = m.get("id") if isinstance(m, dict) else m
    uname = m.get("username") if isinstance(m, dict) else (m if isinstance(m, str) else None)
    u = None
    if uid is not None and uid != "":
        try:
            pid = int(uid) if (isinstance(uid, str) and str(uid).replace("-", "").isdigit()) else uid
            u = User.objects.get(id=pid)
        except (User.DoesNotExist, TypeError, ValueError):
            try:
                u = User.objects.get(username=str(uid))
            except User.DoesNotExist:
                pass
    if u is None and uname:
        try:
            u = User.objects.get(username=str(uname))
        except User.DoesNotExist:
            pass
    return u


def gmt_to_ist_time_str(dt):
    """IST time only: %H:%M:%S."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%H:%M:%S")


def custom_exception_handler(exc, context):
    """
    Custom exception handler that standardizes the error response format.
    Format:
    {
        "success": False,
        "message": "Error message",
        "code": "error_code",
        "errors": { ... } (optional details)
    }
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If response is None, it means it's an exception DRF doesn't handle natively
    # (like a raw Python KeyError or ValueError). 
    # We can choose to handle them here or let Django's 500 handler take over.
    if response is not None:
        custom_data = {
            "success": False,
            "message": "An error occurred",
            "code": "error"
        }

        # Handle specific error codes if available
        if hasattr(exc, 'default_code'):
            custom_data["code"] = exc.default_code
        
        # Improve message based on the exception type
        if hasattr(exc, 'detail'):
            # If detail is a string, use it as the message
            if isinstance(exc.detail, str):
                custom_data["message"] = exc.detail
            # If detail is a list or dict (validation errors), put it in 'errors'
            else:
                custom_data["message"] = "Validation error"
                custom_data["errors"] = exc.detail
                custom_data["code"] = "validation_error"

        response.data = custom_data

    return response
