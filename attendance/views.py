import requests as http_requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.filters import _get_user_role_sync

_FULL_ACCESS_ROLES = frozenset({"MD", "Admin", "HR", "Hr"})

_EXT_BASE = getattr(settings, "ATTENDANCE_API_URL", "").rstrip("/")
_EXT_KEY = getattr(settings, "ATTENDANCE_API_KEY", "")


def _ext_headers():
    return {
        "ngrok-skip-browser-warning": "1",
        "X-API-Key": _EXT_KEY,
    }


def _has_full_access(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _get_user_role_sync(user) in _FULL_ACCESS_ROLES


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def monthly_attendance(request):
    """
    GET /attendanceapi/monthly/?year=2026&month=4&employee_code=2066

    MD / Admin / HR  -> can query any employee_code
    Regular employee -> forced to their own username (employee_code param ignored)
    """
    year = request.query_params.get("year")
    month = request.query_params.get("month")
    employee_code = request.query_params.get("employee_code", "")

    if not year or not month:
        return Response(
            {"detail": "Both 'year' and 'month' query params are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if _has_full_access(request.user):
        if not employee_code:
            return Response(
                {"detail": "'employee_code' query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        employee_code = str(request.user.username)

    try:
        resp = http_requests.get(
            f"{_EXT_BASE}/api/v1/attendance/monthly",
            headers=_ext_headers(),
            params={
                "year": year,
                "month": month,
                "employee_code": employee_code,
            },
            timeout=15,
        )
        return Response(resp.json(), status=resp.status_code)
    except http_requests.ConnectionError:
        return Response(
            {"detail": "Attendance service is unreachable."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except http_requests.Timeout:
        return Response(
            {"detail": "Attendance service timed out."},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except Exception as exc:
        return Response(
            {"detail": f"Attendance service error: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_attendance(request):
    """
    GET /attendanceapi/me/?year=2026&month=4

    Always returns the logged-in user's own attendance — no employee_code param needed.
    """
    year = request.query_params.get("year")
    month = request.query_params.get("month")

    if not year or not month:
        return Response(
            {"detail": "Both 'year' and 'month' query params are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        resp = http_requests.get(
            f"{_EXT_BASE}/api/v1/attendance/monthly",
            headers=_ext_headers(),
            params={
                "year": year,
                "month": month,
                "employee_code": str(request.user.username),
            },
            timeout=15,
        )
        return Response(resp.json(), status=resp.status_code)
    except http_requests.ConnectionError:
        return Response(
            {"detail": "Attendance service is unreachable."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except http_requests.Timeout:
        return Response(
            {"detail": "Attendance service timed out."},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except Exception as exc:
        return Response(
            {"detail": f"Attendance service error: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def health_check(request):
    """Proxy the external attendance service health endpoint."""
    try:
        resp = http_requests.get(
            f"{_EXT_BASE}/health",
            headers=_ext_headers(),
            timeout=5,
        )
        return Response(resp.json(), status=resp.status_code)
    except Exception:
        return Response(
            {"status": "unavailable"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
