import os
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

from .models import (
    Profile,
    User,
    management_Profile,
    LeaveSummary,
    LeaveApplicationData,
    LeaveStatus,
)
from .filters import _get_role_object_sync


def _seed_menstrual_leave_for_female_sync(sender, instance: Profile, **kwargs):
    """Ensure female employees start with menstrual_leaves=1 (idempotent)."""
    gender = (getattr(instance, "gender", "") or "").strip().lower()
    if gender != "female":
        return
    user = instance.Employee_id
    if not user:
        return
    summary, _ = LeaveSummary.objects.get_or_create(
        user=user,
        defaults={"total_leaves": 0, "used_leaves": 0},
    )
    if summary.menstrual_leaves != 1:
        summary.menstrual_leaves = 1
        summary.save(update_fields=["menstrual_leaves"])


@receiver(post_save, sender=Profile)
def seed_menstrual_leave_for_female(sender, instance: Profile, **kwargs):
    _seed_menstrual_leave_for_female_sync(sender, instance, **kwargs)


def _delete_profile_photo_sync(sender, instance: Profile, **kwargs):
    if not instance.Photo_link:
        return
    from django.core.files.storage import default_storage
    name = instance.Photo_link.name
    if not name:
        return
    try:
        if default_storage.exists(name):
            default_storage.delete(name)
    except Exception:
        if hasattr(instance.Photo_link, "path") and os.path.isfile(instance.Photo_link.path):
            os.remove(instance.Photo_link.path)


@receiver(post_delete, sender=Profile)
def delete_profile_photo(sender, instance: Profile, **kwargs):
    _delete_profile_photo_sync(sender, instance, **kwargs)


def _create_emp_profile_sync(sender, instance: Profile, created, **kwargs):
    if created and instance.Role.role_name == "MD":
        instance.Employee_id.is_superuser = True
        instance.Employee_id.save()
        management_Profile.objects.create(
            Employee=instance.Employee_id, Role=instance.Role, Email_id=instance.Email_id,
            Photo_link=instance.Photo_link, Date_of_join=instance.Date_of_join,
            Date_of_birth=instance.Date_of_birth, Name=instance.Name
        )
    role_object = instance.Role
    role_object.total_count += 1
    role_object.save()


@receiver(post_save, sender=Profile)
def create_emp_profile(sender, instance: Profile, created, **kwargs):
    _create_emp_profile_sync(sender, instance, created, **kwargs)


def _create_profile_from_user_sync(sender, instance: User, created, **kwargs):
    try:
        if created and instance.is_superuser:
            role_object = _get_role_object_sync(role="Admin")
            if role_object:
                role_object.total_count += 1
                management_Profile.objects.create(
                    Employee=instance, Role=role_object, Email_id=instance.email
                )
                role_object.save()
    except Exception as e:
        print(e)


@receiver(post_save, sender=User)
def create_profile_from_user(sender, instance: User, created, **kwargs):
    _create_profile_from_user_sync(sender, instance, created, **kwargs)


# ---------------------------------------------------------------------------
# Leave-approval safety net: debit casual -> earn -> unpaid whenever MD_approval
# transitions to Approved (non-Short-Leave paths). Short Leave debits monthly
# quota separately. Admin-financed Short Leave sequential path also debited here.
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=LeaveApplicationData)
def _capture_old_md_status(sender, instance: LeaveApplicationData, **kwargs):
    """Stash previous MD/admin approval ids so post_save detects transitions."""
    if instance.pk:
        old = (
            sender.objects
            .filter(pk=instance.pk)
            .only("MD_approval_id", "admin_approval_id")
            .first()
        )
        instance._old_md_approval_id = old.MD_approval_id if old else None
        instance._old_admin_approval_id = getattr(old, "admin_approval_id", None) if old else None
    else:
        instance._old_md_approval_id = None
        instance._old_admin_approval_id = None


@receiver(post_save, sender=LeaveApplicationData)
def _debit_on_admin_short_leave_approval(sender, instance: LeaveApplicationData, created, **kwargs):
    """Sequential short leave finalized by Admin: consume one monthly short-leave slot."""
    new_ad = instance.admin_approval
    new_name = getattr(new_ad, "name", None) if new_ad else None
    if new_name != "Approved":
        return

    lt = getattr(getattr(instance, "leave_type", None), "name", "") or ""
    if lt != "Short Leave":
        return

    from .leave_views import _short_leave_use_sequential_chain, finalize_short_leave_monthly_debit

    if not _short_leave_use_sequential_chain(instance.applicant):
        return

    if getattr(instance, "short_leave_slot_consumed", False):
        return

    old_id = getattr(instance, "_old_admin_approval_id", None)
    if old_id:
        old_name = (
            LeaveStatus.objects
            .filter(pk=old_id)
            .values_list("name", flat=True)
            .first()
        )
        if old_name == "Approved":
            return

    if instance.is_emergency:
        return

    finalize_short_leave_monthly_debit(instance)


@receiver(post_save, sender=LeaveApplicationData)
def _debit_on_md_approval(sender, instance: LeaveApplicationData, created, **kwargs):
    """Run casual->earn unpaid on MD approval except Short Leave (monthly slot) / Menstrual."""
    new_md = instance.MD_approval
    new_name = getattr(new_md, "name", None) if new_md else None
    if new_name != "Approved":
        return

    if instance.is_emergency:
        return

    leave_type_name = getattr(getattr(instance, "leave_type", None), "name", "") or ""

    if leave_type_name == "Short Leave":
        if getattr(instance, "short_leave_slot_consumed", False):
            return
        old_id = getattr(instance, "_old_md_approval_id", None)
        if old_id:
            old_name = (
                LeaveStatus.objects
                .filter(pk=old_id)
                .values_list("name", flat=True)
                .first()
            )
            if old_name == "Approved":
                return
        from .leave_views import finalize_short_leave_monthly_debit

        finalize_short_leave_monthly_debit(instance)
        return

    already_debited = (
        (instance.casual_used or 0) > 0
        or (instance.earn_used or 0) > 0
        or (instance.unpaid_used or 0) > 0
    )
    if already_debited:
        return

    old_id = getattr(instance, "_old_md_approval_id", None)
    if old_id:
        old_name = (
            LeaveStatus.objects
            .filter(pk=old_id)
            .values_list("name", flat=True)
            .first()
        )
        if old_name == "Approved":
            return

    from .leave_views import (
        _consume_casual_earn_unpaid,
        _consume_menstrual_leave,
        _debit_amount_for,
    )

    with transaction.atomic():
        if leave_type_name == "Menstrual":
            _consume_menstrual_leave(instance.applicant)
            return
        debit = _debit_amount_for(instance)
        if debit <= 0:
            return
        split = _consume_casual_earn_unpaid(instance.applicant, debit)
        LeaveApplicationData.objects.filter(pk=instance.pk).update(
            casual_used=split["casual"],
            earn_used=split["earn"],
            unpaid_used=split["unpaid"],
        )
