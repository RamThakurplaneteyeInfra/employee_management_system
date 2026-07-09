"""
DM work entries API (create by DM employee; approve/reject by MD).
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.filters import _get_user_role_sync
from accounts.models import DmWorkEntry, Profile

from .dm_scoring_targets import is_dm_profile
from .dm_work_scoring import build_dm_work_points, parse_leave_points_period, resolve_leave_points_user


def _is_md(user) -> bool:
    return ( _get_user_role_sync(user=user) or "" ).strip() == "MD"


def _forbidden(detail: str = "You do not have permission to access DM work entries."):
    return Response({"detail": detail}, status=status.HTTP_403_FORBIDDEN)


def _get_profile(user):
    return (
        Profile.objects.filter(Employee_id=user)
        .select_related("Role")
        .prefetch_related("functions")
        .first()
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def dm_work_entries(request):
    """
    GET  /accounts/dm-work-entries/?year=2026&month=7
      - DM user: list own entries (optionally filter by year/month on created_at)
      - MD: list all entries; optional ?employee=<username>
    POST /accounts/dm-work-entries/
      - DM user only: create new pending work entry.
    """
    if request.method == "POST":
        profile = _get_profile(request.user)
        if not is_dm_profile(profile):
            return _forbidden("Only DM employees can submit DM work entries.")
        data = request.data if isinstance(request.data, dict) else {}
        title = (data.get("title") or "").strip()
        if not title:
            return Response({"detail": "title is required."}, status=status.HTTP_400_BAD_REQUEST)
        content_type = (data.get("content_type") or "").strip()
        if content_type not in (
            DmWorkEntry.ContentType.DIGITAL_MEDIA,
            DmWorkEntry.ContentType.DIGITAL_CONTENT,
        ):
            return Response(
                {"detail": "content_type must be 'digital_media' or 'digital_content'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        description = (data.get("description") or "").strip()
        entry = DmWorkEntry.objects.create(
            created_by=request.user,
            title=title,
            description=description,
            content_type=content_type,
            status=DmWorkEntry.ApprovalStatus.PENDING,
        )
        return Response(
            {
                "id": entry.id,
                "ok": True,
                "status": entry.status,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            },
            status=status.HTTP_201_CREATED,
        )

    # GET
    qs = DmWorkEntry.objects.all().select_related("created_by", "approved_by").order_by("-created_at")
    employee = (request.query_params.get("employee") or "").strip()
    if _is_md(request.user):
        if employee:
            qs = qs.filter(created_by__username=employee)
    else:
        qs = qs.filter(created_by=request.user)

    raw_year = request.query_params.get("year")
    raw_month = request.query_params.get("month")
    if raw_year and raw_month:
        try:
            year = int(raw_year)
            month = int(raw_month)
            qs = qs.filter(created_at__year=year, created_at__month=month)
        except Exception:
            return Response({"detail": "year and month must be integers."}, status=status.HTTP_400_BAD_REQUEST)

    out = []
    for e in qs[:500]:
        out.append(
            {
                "id": e.id,
                "employee_id": e.created_by_id,
                "title": e.title,
                "description": e.description,
                "content_type": e.content_type,
                "status": e.status,
                "approved_by": e.approved_by_id,
                "approved_at": e.approved_at.isoformat() if e.approved_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return Response({"count": len(out), "items": out})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def dm_work_entry_approve(request, entry_id: int):
    """
    PATCH /accounts/dm-work-entries/<id>/approve/
    MD only. Body: {"status": "approved"|"rejected"}.
    """
    if not _is_md(request.user):
        return _forbidden("Only MD can approve or reject DM work entries.")

    try:
        entry = DmWorkEntry.objects.get(pk=entry_id)
    except DmWorkEntry.DoesNotExist:
        return Response({"detail": "Entry not found."}, status=status.HTTP_404_NOT_FOUND)

    data = request.data if isinstance(request.data, dict) else {}
    new_status = (data.get("status") or "").strip().lower()
    if new_status not in (DmWorkEntry.ApprovalStatus.APPROVED, DmWorkEntry.ApprovalStatus.REJECTED):
        return Response({"detail": "status must be 'approved' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST)

    entry.status = new_status
    entry.approved_by = request.user
    entry.approved_at = timezone.now()
    entry.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    return Response(
        {
            "id": entry.id,
            "ok": True,
            "status": entry.status,
            "approved_by": entry.approved_by_id,
            "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dm_work_points(request):
    """
    GET /accounts/dm-work-entries/points/?year=2026&month=7
    Optional: ?employee=<username> (HR/MD; mirrors other points endpoints pattern).
    """
    year, month, quarter, period_err = parse_leave_points_period(request)
    if period_err is not None:
        return Response(period_err, status=status.HTTP_400_BAD_REQUEST)

    # Reuse leave permissions: HR/MD can view; others only self.
    from accounts.leave_views import _user_can_view_on_leave

    target_user, user_err = resolve_leave_points_user(request, _user_can_view_on_leave, _get_user_role_sync)
    if user_err is not None:
        err_status = status.HTTP_403_FORBIDDEN
        return Response(user_err, status=err_status)

    data = build_dm_work_points(target_user, year, month=month, quarter=quarter)
    return Response(data)

