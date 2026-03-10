"""
QuaterlyReports signals: notifications for actionable entries.

All notifications use the same consumer and WebSocket endpoint as the notifications app
(NotificationConsumer, ws://host/ws/notifications/). Each event creates a Notification
record and sends a channel_layer group_send to "user_{username}" with type="send_notification".

Notification flows:
  1. Entry created → notify MD (username 2000) and the selected co_author.
  2. Entry approved (co_author sets approved_by_coauthor=True) → notify creator and all shared_with users.
  3. Creator updates the entry → notify co_author, all shared_with, and MD (triggered from view).
  4. Share chain completed (last user sets status to COMPLETED) → notify creator.
"""
from asgiref.sync import async_to_sync
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from .models import FunctionsEntries, FunctionsEntriesShare
from notifications.models import Notification, notification_type
from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str

User = get_user_model()
# Username of the MD user who receives notifications for new entries, approvals, and creator updates.
MD_USERNAME = "2000"

# Cache: previous individual_status (status_name) per FunctionsEntriesShare pk, used in post_save to detect PENDING → COMPLETED.
_pre_save_share_status = {}
# Cache: previous approved_by_coauthor per FunctionsEntries pk, used in post_save to detect approval (False → True).
_pre_save_entry_approved = {}


def _send_notification_and_ws(from_user, recipient, msg, category, title, extra=None):
    """
    Create a Notification row and send a real-time WebSocket event to the recipient.
    Uses the same consumer (NotificationConsumer) and endpoint as the notifications app:
    channel_layer.group_send("user_{username}", type="send_notification", ...).
    Message is trimmed to 100 chars to match Notification.message max_length.
    """
    if not recipient or not from_user:
        return
    msg_trim = (msg[:97] + "...") if len(msg) > 100 else msg
    try:
        nt, _ = notification_type.objects.get_or_create(type_name=category, defaults={"type_name": category})
    except Exception:
        return
    # Persist in DB for notification list / API
    notification_obj = Notification.objects.create(
        from_user=from_user,
        receipient=recipient,
        message=msg_trim,
        type_of_notification=nt,
    )
    # Push to WebSocket so the recipient sees it in real time (time in IST)
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            from_name = _get_users_Name_sync(from_user) or getattr(from_user, "username", "")
            ws_extra = dict(extra or {})
            ws_extra["time"] = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
            async_to_sync(channel_layer.group_send)(
                f"user_{recipient.username}",
                {
                    "type": "send_notification",
                    "category": category,
                    "title": title or category,
                    "from": from_name,
                    "message": msg_trim,
                    "extra": ws_extra,
                },
            )
        except Exception:
            pass


def _notify_creator_share_chain_completed(entry, completed_by_user):
    """
    Notify the entry creator when the last user in the share chain sets their
    individual_status from PENDING to COMPLETED. Called from post_save on FunctionsEntriesShare.
    """
    creator = getattr(entry, "Creator", None)
    if not creator:
        return
    completer_name = _get_users_Name_sync(completed_by_user) or getattr(completed_by_user, "username", "")
    message = f"Share chain completed by {completer_name} for entry #{entry.pk}."
    _send_notification_and_ws(
        completed_by_user, creator, message,
        "Share_Chain_Completed", "Share chain completed",
    )


# =============================================================================
# Signal: Actionable entry created → notify MD and co_author
# =============================================================================

@receiver(post_save, sender=FunctionsEntries)
def notify_md_and_coauthor_on_entry_created(sender, instance, created, **kwargs):
    """
    When a new actionable entry is created (POST to ActionableEntries/ or equivalent),
    notify:
      - MD: user with username MD_USERNAME ("2000"), if that user exists.
      - Co-author: the selected co_author on the entry, if set and different from creator.
    From_user is the creator; message includes entry id and creator name.
    """
    if not created:
        return
    creator = getattr(instance, "Creator", None)
    if not creator:
        return
    creator_name = _get_users_Name_sync(creator) or getattr(creator, "username", "")
    msg = f"New actionable entry #{instance.pk} from {creator_name}."
    recipients = []
    # Add MD (username 2000) if they exist
    try:
        md = User.objects.get(username=MD_USERNAME)
        recipients.append(md)
    except User.DoesNotExist:
        pass
    # Add co_author if present and not same as creator
    co_author = getattr(instance, "co_author", None)
    if co_author and co_author != creator:
        recipients.append(co_author)
    for rec in recipients:
        _send_notification_and_ws(
            creator, rec, msg,
            "Actionable_Entry_Created", "Actionable entry created",
            extra={"entry_id": instance.pk},
        )


# =============================================================================
# Signal: Entry approved by co_author → notify creator and all shared_with
# =============================================================================

@receiver(pre_save, sender=FunctionsEntries)
def _store_entry_approved_before_save(sender, instance, **kwargs):
    """
    Before an entry is saved, store its current approved_by_coauthor value keyed by pk.
    The post_save handler uses this to detect the transition False → True (co_author just approved).
    """
    if instance.pk:
        try:
            old = FunctionsEntries.objects.get(pk=instance.pk)
            _pre_save_entry_approved[instance.pk] = getattr(old, "approved_by_coauthor", False)
        except FunctionsEntries.DoesNotExist:
            _pre_save_entry_approved[instance.pk] = False


@receiver(post_save, sender=FunctionsEntries)
def notify_creator_and_shared_when_approved(sender, instance, created, **kwargs):
    """
    When the co_author approves the entry (approved_by_coauthor changes from False to True),
    notify:
      - The creator (so they know the entry is now in progress).
      - Every user in the share chain (shared_with), so they know the entry is visible to them.
    From_user is the co_author; we skip notifying the co_author themselves.
    """
    if created:
        return
    was_approved = _pre_save_entry_approved.pop(instance.pk, False)
    if not instance.approved_by_coauthor or was_approved:
        return
    co_author = getattr(instance, "co_author", None)
    if not co_author:
        return
    co_name = _get_users_Name_sync(co_author) or getattr(co_author, "username", "")
    msg = f"Actionable entry #{instance.pk} approved by {co_name}."
    # Notify creator (unless creator is the co_author, e.g. edge case)
    creator = getattr(instance, "Creator", None)
    if creator and creator != co_author:
        _send_notification_and_ws(
            co_author, creator, msg,
            "Actionable_Entry_Approved", "Entry approved",
            extra={"entry_id": instance.pk},
        )
    # Notify each user in the share chain (shared_with)
    for share in instance.share_chain.all():
        sw = getattr(share, "shared_with", None)
        if sw and sw != co_author and sw != creator:
            _send_notification_and_ws(
                co_author, sw, msg,
                "Actionable_Entry_Approved", "Entry approved",
                extra={"entry_id": instance.pk},
            )


# =============================================================================
# Creator-update notification (called from view, not a model signal)
# =============================================================================

def notify_associates_and_md_on_creator_update(entry):
    """
    Notify all associated users and MD when the creator edits the actionable entry.
    Called from QuaterlyReports.views._entry_detail_ops after a successful PATCH/PUT
    when the current user is the creator.

    Recipients:
      - MD: user with username MD_USERNAME ("2000"), if they exist and are not the creator.
      - Co-author: the entry's co_author, if set and not the creator.
      - Every user in the share chain (shared_with), excluding the creator.
    From_user is the creator; message includes entry id and creator name.
    """
    creator = getattr(entry, "Creator", None)
    if not creator:
        return
    creator_name = _get_users_Name_sync(creator) or getattr(creator, "username", "")
    msg = f"Actionable entry #{entry.pk} updated by creator {creator_name}."
    recipients = []
    try:
        md = User.objects.get(username=MD_USERNAME)
        if md != creator:
            recipients.append(md)
    except User.DoesNotExist:
        pass
    co_author = getattr(entry, "co_author", None)
    if co_author and co_author != creator:
        recipients.append(co_author)
    for share in entry.share_chain.all():
        sw = getattr(share, "shared_with", None)
        if sw and sw != creator and sw not in recipients:
            recipients.append(sw)
    for rec in recipients:
        _send_notification_and_ws(
            creator, rec, msg,
            "Actionable_Entry_Updated_By_Creator", "Entry updated by creator",
            extra={"entry_id": entry.pk},
        )


# =============================================================================
# Signal: Share chain completed (last user sets status to COMPLETED) → notify creator
# =============================================================================

@receiver(pre_save, sender=FunctionsEntriesShare)
def _store_share_status_before_save(sender, instance, **kwargs):
    """
    Before a share row is saved, store its current individual_status status_name (e.g. PENDING/INPROCESS).
    The post_save handler uses this to detect the transition to COMPLETED by the last user in the chain.
    """
    if instance.pk:
        try:
            old = FunctionsEntriesShare.objects.select_related("individual_status").get(pk=instance.pk)
            _pre_save_share_status[instance.pk] = (
                getattr(old.individual_status, "status_name", None) or ""
            ).upper()
        except FunctionsEntriesShare.DoesNotExist:
            _pre_save_share_status[instance.pk] = None


@receiver(post_save, sender=FunctionsEntriesShare)
def notify_creator_when_share_chain_completed(sender, instance, created, **kwargs):
    """
    When a share row's individual_status changes to COMPLETED, check if this row is the *last*
    in the chain (by shared_time). Only the last user is allowed to set COMPLETED. If so,
    notify the entry creator that the share chain is complete.
    Calls _notify_creator_share_chain_completed(entry, completed_by_user).
    """
    if created:
        return
    old_status_name = _pre_save_share_status.pop(instance.pk, None)
    new_status_name = (getattr(instance.individual_status, "status_name", None) or "").upper()
    if new_status_name != "COMPLETED" or old_status_name == "COMPLETED":
        return
    entry = instance.actionable_entry
    # Only the last share in the chain (by shared_time) can set COMPLETED; only then do we notify
    last_share = (
        FunctionsEntriesShare.objects.filter(actionable_entry=entry)
        .order_by("-shared_time")
        .first()
    )
    if not last_share or last_share.pk != instance.pk:
        return
    _notify_creator_share_chain_completed(entry, instance.shared_with)
