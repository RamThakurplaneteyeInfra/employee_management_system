"""
Leave workflow notification helpers.

Isolated side-effect layer for leave notifications so leave approval logic stays
unchanged and notification failures never block API responses.
"""
from __future__ import annotations

import logging
from typing import Iterable

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.db import transaction

from accounts.filters import _get_users_Name_sync
from accounts.models import LeaveApplicationData, Profile
from ems.channel_groups import user_group_name
from ems.utils import gmt_to_ist_str
from notifications.models import Notification, notification_type

logger = logging.getLogger(__name__)

SHORT_LEAVE_TYPE_NAME = "Short Leave"

TYPE_SUBMITTED_ALT = "Leave_Submitted_Alternative"
TYPE_ALT_APPROVED = "Leave_Alternative_Approved"
TYPE_TL_APPROVED = "Leave_TeamLead_Approved"
TYPE_HR_APPROVED = "Leave_HR_Approved"
TYPE_FINAL_APPROVED = "Leave_Final_Approved"


def _is_regular_leave(instance: LeaveApplicationData | None) -> bool:
    if not instance:
        return False
    if bool(getattr(instance, "is_emergency", False)):
        return False
    leave_type_name = getattr(getattr(instance, "leave_type", None), "name", "") or ""
    if leave_type_name == SHORT_LEAVE_TYPE_NAME:
        return False
    return True


def _get_or_create_notification_type(type_name: str) -> notification_type | None:
    if not type_name:
        return None
    try:
        with transaction.atomic():
            nt, _ = notification_type.objects.get_or_create(type_name=type_name)
            return nt
    except Exception as exc:
        logger.warning("Leave notification type resolve failed (%s): %s", type_name, exc)
        return None


def _send_ws_notification(to_user: User, payload: dict) -> None:
    if not to_user:
        return
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(user_group_name(to_user.username), payload)
    except Exception as exc:
        logger.warning("Leave websocket notify failed for %s: %s", to_user.username, exc)


def _display_name(user: User | None) -> str | None:
    if not user:
        return None
    return _get_users_Name_sync(user) or user.username


def send_leave_notification(
    *,
    to_user: User | None,
    from_user: User | None,
    type_name: str,
    title: str,
    message: str,
    category: str = "Leave",
) -> Notification | None:
    """
    Persist in-app notification and push websocket notification.
    Never raises to callers.
    """
    if not to_user:
        return None
    nt = _get_or_create_notification_type(type_name)
    if not nt:
        return None

    try:
        notification_obj = Notification.objects.create(
            from_user=from_user,
            receipient=to_user,
            message=message[:100],
            type_of_notification=nt,
        )
    except Exception as exc:
        logger.warning("Leave Notification.objects.create failed: %s", exc)
        return None

    payload = {
        "type": "send_notification",
        "title": title,
        "category": category,
        "from": _display_name(from_user),
        "message": message[:100],
        "extra": {"time": gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")},
    }
    _send_ws_notification(to_user, payload)
    return notification_obj


def _users_by_role_names(role_names: Iterable[str]) -> list[User]:
    """
    Resolve users from Profile.Role.role_name.
    Keeps legacy role spellings compatible.
    """
    names = [name for name in role_names if name]
    if not names:
        return []
    profiles = (
        Profile.objects.select_related("Employee_id", "Role")
        .filter(Role__role_name__in=names, Employee_id__isnull=False)
    )
    users = []
    seen_ids: set[int] = set()
    for profile in profiles:
        user = profile.Employee_id
        if user and user.id not in seen_ids:
            users.append(user)
            seen_ids.add(user.id)
    return users


def notify_alternative_on_submission(instance: LeaveApplicationData) -> None:
    """Applicant submits leave; notify designated alternative if present."""
    if not _is_regular_leave(instance):
        return
    if not instance.alternative_id:
        return
    applicant_name = _display_name(instance.applicant) or "An employee"
    msg = f"{applicant_name} requested leave and selected you as alternative."
    send_leave_notification(
        to_user=instance.alternative,
        from_user=instance.applicant,
        type_name=TYPE_SUBMITTED_ALT,
        title="Leave cover request",
        message=msg,
    )


def notify_after_alternative_approved(instance: LeaveApplicationData, acting_user: User) -> None:
    """Alternative approved; notify team lead, fallback to HR, then MD."""
    if not _is_regular_leave(instance):
        return
    applicant_name = _display_name(instance.applicant) or "Employee"
    actor_name = _display_name(acting_user) or "Alternative"
    if instance.team_lead_id:
        msg = f"{actor_name} approved cover for {applicant_name}'s leave. Please review."
        send_leave_notification(
            to_user=instance.team_lead,
            from_user=acting_user,
            type_name=TYPE_ALT_APPROVED,
            title="Leave needs team lead approval",
            message=msg,
        )
        return
    notify_hr_after_team_lead_approved(instance, acting_user)


def notify_hr_after_team_lead_approved(instance: LeaveApplicationData, acting_user: User) -> None:
    """Team lead approved; notify all HR users, fallback to MD if no HR exists."""
    if not _is_regular_leave(instance):
        return
    recipients = _users_by_role_names(["HR", "Hr"])
    applicant_name = _display_name(instance.applicant) or "Employee"
    actor_name = _display_name(acting_user) or "Team lead"
    msg = f"{actor_name} approved {applicant_name}'s leave. HR review is required."
    if recipients:
        for recipient in recipients:
            send_leave_notification(
                to_user=recipient,
                from_user=acting_user,
                type_name=TYPE_TL_APPROVED,
                title="Leave needs HR approval",
                message=msg,
            )
        return
    notify_md_after_hr_approved(instance, acting_user)


def notify_md_after_hr_approved(instance: LeaveApplicationData, acting_user: User) -> None:
    """HR approved; notify all MD users."""
    if not _is_regular_leave(instance):
        return
    recipients = _users_by_role_names(["MD"])
    applicant_name = _display_name(instance.applicant) or "Employee"
    actor_name = _display_name(acting_user) or "HR"
    msg = f"{actor_name} approved {applicant_name}'s leave. MD review is required."
    for recipient in recipients:
        send_leave_notification(
            to_user=recipient,
            from_user=acting_user,
            type_name=TYPE_HR_APPROVED,
            title="Leave needs MD approval",
            message=msg,
        )


def notify_applicant_final_approval(instance: LeaveApplicationData, acting_user: User) -> None:
    """MD approved; notify applicant as final decision."""
    if not _is_regular_leave(instance):
        return
    actor_name = _display_name(acting_user) or "MD"
    msg = f"Your leave request has been approved by {actor_name}."
    send_leave_notification(
        to_user=instance.applicant,
        from_user=acting_user,
        type_name=TYPE_FINAL_APPROVED,
        title="Leave approved",
        message=msg,
    )
