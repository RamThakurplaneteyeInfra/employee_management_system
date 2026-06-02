"""
Leave application APIs: POST (regular + emergency), GET, PATCH, PUT, DELETE.
Approval hierarchy by applicant role; remaining-leaves validation; HR-only emergency leave.
"""
from decimal import Decimal

from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from ems.RequiredImports import get_object_or_404
from ems.auth_utils import CsrfExemptSessionAuthentication

from .models import (
    LeaveApplicationData,
    LeaveTypes,
    LeaveStatus,
    LeaveSummary,
    Profile,
)
from .serializers import (
    LeaveApplicationResponseSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationEmergencyCreateSerializer,
    LeaveApplicationUpdateSerializer,
    MenstrualLeaveCreateSerializer,
    AlternativeRespondSerializer,
    ShortLeaveCreateSerializer,
)
from .filters import _get_user_role_sync
from .leave_notifications import (
    notify_alternative_on_submission,
    notify_after_alternative_approved,
    notify_hr_after_team_lead_approved,
    notify_md_after_hr_approved,
    notify_applicant_final_approval,
)

INTERN_ROLE_NAME = "Intern"


def _parse_pagination_params(request):
    """
    Optional limit/offset pagination (backward-compatible).
    Enabled when either query param is present. Same contract as Messaging getMessages / callHistory.
    """
    raw_limit = request.query_params.get("limit")
    raw_offset = request.query_params.get("offset")
    paginate_enabled = raw_limit is not None or raw_offset is not None

    if not paginate_enabled:
        return 0, 0, False

    default_limit = 30
    max_limit = 100

    try:
        limit = int(raw_limit) if raw_limit is not None else default_limit
    except (TypeError, ValueError):
        limit = default_limit

    try:
        offset = int(raw_offset) if raw_offset is not None else 0
    except (TypeError, ValueError):
        offset = 0

    if limit < 1:
        limit = default_limit
    if limit > max_limit:
        limit = max_limit
    if offset < 0:
        offset = 0

    return limit, offset, True


def _paginated_response(queryset, serializer_data, limit, offset):
    total = queryset.count()
    next_offset = offset + limit if (offset + limit) < total else None
    prev_offset = offset - limit if offset - limit >= 0 else None
    return Response(
        {
            "items": serializer_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "next_offset": next_offset,
                "prev_offset": prev_offset,
                "has_next": next_offset is not None,
                "has_prev": offset > 0,
                "total": total,
            },
        }
    )


# ---------- Role-based permissions for approval tabs ----------
class IsHR(BasePermission):
    """Allow only users with role HR (or superuser)."""

    def has_permission(self, request, view):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = _get_user_role_sync(request.user)
        return role == "HR"


class IsAdmin(BasePermission):
    """Allow only users with role Admin (or superuser)."""

    def has_permission(self, request, view):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = _get_user_role_sync(request.user)
        return role == "Admin"


class IsMD(BasePermission):
    """Allow only users with role MD (or superuser)."""

    def has_permission(self, request, view):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = _get_user_role_sync(request.user)
        return role == "MD"


# ---------- Helpers: LeaveStatus by name (single query) ----------
def _get_leave_status_map():
    """Return dict name -> LeaveStatus instance; use in views to avoid repeated queries."""
    qs = LeaveStatus.objects.all()
    return {obj.name: obj for obj in qs}


def _validate_remaining_leaves(applicant, duration_of_days):
    """
    Raise serializers.ValidationError if applicant's remaining leaves < duration_of_days.
    """
    from rest_framework import serializers

    try:
        summary = LeaveSummary.objects.get(user=applicant)
    except LeaveSummary.DoesNotExist:
        raise serializers.ValidationError(
            {"non_field_errors": ["Leave summary not found for this user. Run populate_leave_data."]}
        )
    remaining = max(0, summary.total_leaves - summary.used_leaves)
    if remaining < duration_of_days:
        raise serializers.ValidationError(
            {"non_field_errors": [f"Insufficient leave balance. Remaining: {remaining}, requested: {duration_of_days}."]}
        )


def _get_applicant_role_and_teamlead(applicant):
    """
    Return (role_name or None, teamlead_user or None).
    Uses Profile; if no profile, role is None (treat as non-MD and set team_lead from Profile if any).
    """
    try:
        profile = Profile.objects.select_related("Role", "Teamlead").get(Employee_id=applicant)
        role_name = profile.Role.role_name if profile.Role else None
        teamlead = profile.Teamlead
        return role_name, teamlead
    except Profile.DoesNotExist:
        return None, None


def _is_intern_applicant(applicant):
    role_name, _ = _get_applicant_role_and_teamlead(applicant)
    return role_name == INTERN_ROLE_NAME


def _set_team_lead_from_profile(application, applicant):
    """Set application.team_lead from applicant's Profile.Teamlead (if any)."""
    _, teamlead = _get_applicant_role_and_teamlead(applicant)
    application.team_lead = teamlead


def _increment_used_leaves(applicant, duration_of_days):
    """
    When MD approves a (non-emergency) leave, add duration to applicant's LeaveSummary.used_leaves.
    Emergency leave already updates used_leaves in emergency_leave().
    """
    if not applicant or (duration_of_days or 0) <= 0:
        return
    summary, _ = LeaveSummary.objects.get_or_create(
        user=applicant,
        defaults={"total_leaves": 0, "used_leaves": 0},
    )
    summary.used_leaves = (summary.used_leaves or 0) + duration_of_days
    summary.save(update_fields=["used_leaves"])


def _consume_menstrual_leave(applicant):
    """Set the applicant's monthly menstrual_leaves bucket to 0 (idempotent)."""
    if not applicant:
        return
    summary, _ = LeaveSummary.objects.get_or_create(
        user=applicant,
        defaults={"total_leaves": 0, "used_leaves": 0},
    )
    if summary.menstrual_leaves and summary.menstrual_leaves > 0:
        summary.menstrual_leaves = 0
        summary.save(update_fields=["menstrual_leaves"])


def _consume_casual_earn_unpaid(applicant, duration_days):
    """
    Debit `duration_days` from the applicant's leave buckets in waterfall order:
        casual_leaves -> earn_leaves -> unpaid_leaves.

    `duration_days` accepts int / Decimal (e.g. Decimal('0.5') for half-day).
    Also increments `used_leaves` by the integer paid portion (casual + earn) so
    legacy reporting that reads used_leaves keeps working for paid days only.

    Returns: dict {"casual": Decimal, "earn": Decimal, "unpaid": Decimal}.
    """
    zero = Decimal("0")
    if not applicant:
        return {"casual": zero, "earn": zero, "unpaid": zero}
    needed = Decimal(duration_days or 0)
    if needed <= 0:
        return {"casual": zero, "earn": zero, "unpaid": zero}

    summary, _ = LeaveSummary.objects.get_or_create(
        user=applicant,
        defaults={"total_leaves": 0, "used_leaves": 0},
    )
    if _is_intern_applicant(applicant):
        take_unpaid = needed
        summary.unpaid_leaves = (summary.unpaid_leaves or zero) + take_unpaid
        summary.save(update_fields=["unpaid_leaves"])
        return {"casual": zero, "earn": zero, "unpaid": take_unpaid}

    casual_balance = summary.casual_leaves or zero
    earn_balance = summary.earn_leaves or zero

    take_casual = min(casual_balance, needed)
    needed -= take_casual

    take_earn = min(earn_balance, needed)
    needed -= take_earn

    take_unpaid = needed  # whatever is left becomes unpaid

    summary.casual_leaves = casual_balance - take_casual
    summary.earn_leaves = earn_balance - take_earn
    summary.unpaid_leaves = (summary.unpaid_leaves or zero) + take_unpaid
    # Keep legacy `used_leaves` coherent for the paid portion only.
    paid_taken = take_casual + take_earn
    summary.used_leaves = (summary.used_leaves or 0) + int(paid_taken)
    summary.save(update_fields=[
        "casual_leaves", "earn_leaves", "unpaid_leaves", "used_leaves",
    ])
    return {"casual": take_casual, "earn": take_earn, "unpaid": take_unpaid}


def _debit_amount_for(application):
    """Return the Decimal amount to debit for casual/earn/unpaid (not Short Leave / Menstrual)."""
    leave_type_name = getattr(getattr(application, "leave_type", None), "name", "") or ""
    if leave_type_name == "Half_day":
        return Decimal("0.5")
    if leave_type_name == "Short Leave":
        return Decimal("0")
    return Decimal(application.duration_of_days or 0)


def short_leave_monthly_quota() -> int:
    return max(0, int(getattr(settings, "SHORT_LEAVE_MONTHLY_QUOTA", 2)))


def _current_month_first():
    return timezone.localdate().replace(day=1)


def sync_short_leave_monthly_calendar(user):
    """If the calendar month changed, reset monthly short leave to the configured quota."""
    quota = short_leave_monthly_quota()
    ms = _current_month_first()
    LeaveSummary.objects.filter(user=user).exclude(short_leave_credit_month_first=ms).update(
        short_leaves_remaining=quota,
        short_leave_credit_month_first=ms,
    )


SHORT_LEAVE_TYPE_NAME = "Short Leave"


def _leave_type_name_on(instance):
    if instance is None:
        return ""
    return getattr(getattr(instance, "leave_type", None), "name", "") or ""


def _is_short_leave_instance(instance):
    return _leave_type_name_on(instance) == SHORT_LEAVE_TYPE_NAME


def validate_short_leave_monthly_quota(applicant):
    """Raise ValidationError if applicant has no monthly short-leave slots left."""
    from rest_framework import serializers as ser
    from django.db.models import Q

    quota = short_leave_monthly_quota()
    LeaveSummary.objects.get_or_create(
        user=applicant,
        defaults={
            "total_leaves": 0,
            "used_leaves": 0,
            "short_leaves_remaining": quota,
            "short_leave_credit_month_first": _current_month_first(),
        },
    )
    sync_short_leave_monthly_calendar(applicant)
    summary = LeaveSummary.objects.get(user=applicant)

    awaiting = LeaveApplicationData.objects.filter(
        applicant=applicant,
        leave_type__name=SHORT_LEAVE_TYPE_NAME,
        short_leave_slot_consumed=False,
    ).exclude(
        Q(team_lead_approval__name="Rejected")
        | Q(HR_approval__name="Rejected")
        | Q(MD_approval__name="Rejected")
        | Q(admin_approval__name="Rejected"),
    ).count()

    if summary.short_leaves_remaining <= 0:
        raise ser.ValidationError(
            {
                "non_field_errors": [
                    f"No short leave slots remaining this month (monthly quota is {quota})."
                ]
            }
        )

    slots_left = summary.short_leaves_remaining
    if awaiting >= slots_left:
        raise ser.ValidationError(
            {
                "non_field_errors": [
                    (
                        "Monthly short-leave quota is already tied up by pending requests. "
                        "Wait until they resolve before applying again."
                    )
                ]
            }
        )


def finalize_short_leave_monthly_debit(application: LeaveApplicationData) -> None:
    """
    Consume one monthly short-leave slot after final approval. Does not touch casual/earn.
    Idempotent via `short_leave_slot_consumed`.
    """
    if not application or not application.pk:
        return
    if not _is_short_leave_instance(application):
        return
    quota = short_leave_monthly_quota()
    applicant = application.applicant
    pk = application.pk

    with transaction.atomic():
        locked = (
            LeaveApplicationData.objects.select_for_update()
            .filter(pk=pk, short_leave_slot_consumed=False)
            .first()
        )
        if not locked:
            return
        summary, _ = LeaveSummary.objects.select_for_update().get_or_create(
            user=applicant,
            defaults={
                "total_leaves": 0,
                "used_leaves": 0,
                "short_leaves_remaining": quota,
                "short_leave_credit_month_first": _current_month_first(),
            },
        )
        ms = _current_month_first()
        if summary.short_leave_credit_month_first != ms:
            summary.short_leaves_remaining = quota
            summary.short_leave_credit_month_first = ms
        if summary.short_leaves_remaining < 1:
            summary.save(update_fields=["short_leaves_remaining", "short_leave_credit_month_first"])
            return
        summary.short_leaves_remaining -= 1
        summary.save(update_fields=["short_leaves_remaining", "short_leave_credit_month_first"])
        LeaveApplicationData.objects.filter(pk=pk).update(short_leave_slot_consumed=True)


def _role_is_hr(role_name):
    return role_name in ("HR", "Hr")


def _short_leave_use_sequential_chain(applicant):
    """True when short leave runs TL → HR → MD (HR and MD applicants use other rails)."""
    role_name, _ = _get_applicant_role_and_teamlead(applicant)
    if _role_is_hr(role_name):
        return False
    if role_name == "MD":
        return False
    return True


def _short_leave_skip_team_lead_step(applicant):
    role_name, _ = _get_applicant_role_and_teamlead(applicant)
    return role_name in ("TeamLead", "Teamlead")


def _set_short_leave_approvals(application, applicant, status_map):
    """
    Short leave rails:
      - HR applicant: MD only (Pending), same as full-day HR leave.
      - MD applicant: auto-approved on MD rail.
      - Team-lead applicant: HR first, then MD after HR approves.
      - Others: sequential TL → HR → MD. Employee without team lead starts at HR;
        Intern must have a team lead (enforced in the view).
    """
    pending = status_map.get("Pending")
    approved = status_map.get("Approved")
    role_name, teamlead = _get_applicant_role_and_teamlead(applicant)

    application.team_lead_approval_id = None
    application.HR_approval_id = None
    application.admin_approval_id = None
    application.MD_approval_id = None
    application.approved_by_MD_at = None

    if role_name == "MD":
        application.MD_approval_id = approved.id if approved else None
        application.approved_by_MD_at = timezone.now()
        return
    if _role_is_hr(role_name):
        application.MD_approval_id = pending.id if pending else None
        return
    if _short_leave_skip_team_lead_step(applicant):
        application.HR_approval_id = pending.id if pending else None
        return
    if teamlead:
        application.team_lead_approval_id = pending.id if pending else None
        return
    application.HR_approval_id = pending.id if pending else None


def _short_leave_requires_tl_approved_before_hr(instance):
    if not _short_leave_use_sequential_chain(instance.applicant):
        return False
    if _short_leave_skip_team_lead_step(instance.applicant):
        return False
    return bool(instance.team_lead_id)


def _short_leave_requires_hr_approved_before_md(instance):
    if not _short_leave_use_sequential_chain(instance.applicant):
        return False
    return True


def _short_leave_on_legacy_admin_rail(instance):
    """In-flight short leave created before TL→HR→MD routing (Admin final step)."""
    return _is_short_leave_instance(instance) and instance.admin_approval_id is not None


def _set_approvals_by_role(application, applicant, status_map, is_md_approval_by_default=False):
    """
    Set team_lead_approval, HR_approval, admin_approval, MD_approval on application
    based on applicant's role.
    - MD applicant: all None except MD=Approved.
    - Admin applicant: team_lead=None, HR=Pending, admin=None, MD=Pending.
    - HR applicant: team_lead=None, HR=None, admin=None, MD=Pending. (MD-only approval.)
    - TeamLead applicant: team_lead=None, HR=Pending, admin=None, MD=Pending.
    - Employee/Intern: team_lead=Pending (if a team lead is assigned), HR=Pending, admin=None, MD=Pending
      (Team Lead, HR, and MD see the request in parallel; MD's approval confirms it).
    """
    pending = status_map.get("Pending")
    approved = status_map.get("Approved")

    role_name, teamlead = _get_applicant_role_and_teamlead(applicant)

    if role_name == "MD" or is_md_approval_by_default:
        application.team_lead_approval_id = None
        application.HR_approval_id = None
        application.admin_approval_id = None
        application.MD_approval_id = approved.id if approved else None
        application.approved_by_MD_at = timezone.now()
        return
    if role_name == "Admin":
        application.team_lead_approval_id = None
        application.HR_approval_id = pending.id if pending else None
        application.admin_approval_id = None
        application.MD_approval_id = pending.id if pending else None
        return
    if role_name == "HR":
        # HR's own leave goes to MD ONLY (no Admin step). Admin tab will not
        # show this row because admin_approval is left NULL.
        application.team_lead_approval_id = None
        application.HR_approval_id = None
        application.admin_approval_id = None
        application.MD_approval_id = pending.id if pending else None
        return
    if role_name in ("TeamLead", "Teamlead"):
        # Applicant is team lead: no team lead step; goes to HR
        application.team_lead_approval_id = None
        application.HR_approval_id = pending.id if pending else None
        application.admin_approval_id = None
        application.MD_approval_id = pending.id if pending else None
        return
    # Employee or Intern: parallel approval. Team Lead (if assigned), HR, and MD
    # all receive the request immediately. Only MD's approval confirms the leave
    # and triggers balance debit (handled in _apply_update_by_role).
    if teamlead:
        application.team_lead_approval_id = pending.id if pending else None
    else:
        application.team_lead_approval_id = None
    application.HR_approval_id = pending.id if pending else None
    application.admin_approval_id = None
    application.MD_approval_id = pending.id if pending else None


def _set_initial_alternative_approval(application, status_map):
    """When an alternative cover person is set, they start as Pending; clears when unset."""
    pending = status_map.get("Pending")
    if application.alternative_id:
        application.alternative_approval_id = pending.id if pending else None
        application.alternative_responded_at = None
    else:
        application.alternative_approval_id = None
        application.alternative_responded_at = None


def _resync_alternative_approval_if_alternative_changed(instance, status_map, old_alternative_id):
    """Reset alternative response when the applicant changes or clears the cover person."""
    pending = status_map.get("Pending")
    if not instance.alternative_id:
        instance.alternative_approval_id = None
        instance.alternative_responded_at = None
        return
    if instance.alternative_id != old_alternative_id:
        instance.alternative_approval_id = pending.id if pending else None
        instance.alternative_responded_at = None


# ---------- ViewSet ----------
class LeaveApplicationViewSet(ModelViewSet):
    """
    Leave applications: list, retrieve, create (regular), emergency (HR), update, delete.
    Queryset optimized with select_related for FKs.
    """
    queryset = (
        LeaveApplicationData.objects.all()
        .select_related(
            "applicant",
            "applicant__accounts_profile",
            "team_lead",
            "team_lead__accounts_profile",
            "alternative",
            "alternative__accounts_profile",
            "leave_type",
            "team_lead_approval",
            "HR_approval",
            "MD_approval",
            "admin_approval",
            "alternative_approval",
        )
        .order_by("-application_date", "-id")
    )
    serializer_class = LeaveApplicationResponseSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}

    def get_serializer_class(self):
        if self.action == "create":
            return LeaveApplicationCreateSerializer
        if self.action == "short_leave":
            return ShortLeaveCreateSerializer
        if self.action == "emergency_leave":
            return LeaveApplicationEmergencyCreateSerializer
        if self.action == "menstrual_leave":
            return MenstrualLeaveCreateSerializer
        if self.action in ("update", "partial_update"):
            return LeaveApplicationUpdateSerializer
        return LeaveApplicationResponseSerializer

    def create(self, request, *args, **kwargs):
        """POST: apply for leave (self). leave_type as string; Full_day: validate remaining leaves, no half_day_slots validation; Half_day: validate half_day_slots, no duration validation. Returns name/status fields only (no FK ids)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applicant = request.user
        validated = serializer.validated_data
        leave_type = validated.get("leave_type")
        leave_type_name = getattr(leave_type, "name", None) or ""
        duration = validated.get("duration_of_days") or 0
        # Full_day / Half_day no longer reject on insufficient balance; the new
        # waterfall (casual -> earn -> unpaid) absorbs any overflow at approval time.
        # Menstrual leave uses a separate monthly bucket (0 or 1).
        if leave_type_name == "Menstrual":
            from rest_framework import serializers as _s
            summary = LeaveSummary.objects.filter(user=applicant).first()
            if not summary or (summary.menstrual_leaves or 0) < 1:
                raise _s.ValidationError(
                    {"non_field_errors": ["No menstrual leave available this month."]}
                )

        status_map = _get_leave_status_map()
        is_md_applicant = _get_user_role_sync(applicant) == "MD"
        with transaction.atomic():
            application = serializer.save()
            _set_team_lead_from_profile(application, applicant)
            _set_approvals_by_role(application, applicant, status_map, is_md_approval_by_default=is_md_applicant)
            _set_initial_alternative_approval(application, status_map)
            application.save(update_fields=[
                "team_lead", "team_lead_approval", "HR_approval", "MD_approval", "admin_approval",
                "approved_by_MD_at", "alternative_approval", "alternative_responded_at",
            ])
            # When applicant is MD, leave is auto-approved; deduct from the right bucket.
            if is_md_applicant and not application.is_emergency:
                if leave_type_name == "Menstrual":
                    _consume_menstrual_leave(applicant)
                else:
                    debit = _debit_amount_for(application)
                    if debit > 0:
                        split = _consume_casual_earn_unpaid(applicant, debit)
                        application.casual_used = split["casual"]
                        application.earn_used = split["earn"]
                        application.unpaid_used = split["unpaid"]
                        application.save(update_fields=[
                            "casual_used", "earn_used", "unpaid_used",
                        ])
            # Regular leave submission -> notify designated alternative once.
            notify_alternative_on_submission(application)
        application.refresh_from_db()
        return Response(
            LeaveApplicationResponseSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="emergency", permission_classes=[IsAuthenticated, IsHR])
    def emergency_leave(self, request):
        """
        HR only: create emergency leave on behalf of any user.
        Emergency leaves are limited to 10%% of user's total_leaves (LeaveSummary.emergency_leaves tracks used emergency days).
        team_lead_approval, HR_approval, MD_approval are all set to Approved by default for emergency requests.
        """
        from rest_framework import serializers as s

        serializer = LeaveApplicationEmergencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_map = _get_leave_status_map()
        approved = status_map.get("Approved")

        applicant = serializer.validated_data.get("applicant")
        duration = serializer.validated_data.get("duration_of_days") or 0
        if duration < 1:
            raise s.ValidationError({"duration_of_days": ["duration_of_days must be at least 1."]})

        leave_type_obj = serializer.validated_data.get("leave_type")
        leave_type_name = getattr(leave_type_obj, "name", "") or ""
        is_menstrual = leave_type_name == "Menstrual"

        summary, _ = LeaveSummary.objects.get_or_create(
            user=applicant,
            defaults={"total_leaves": 0, "used_leaves": 0},
        )
        if is_menstrual:
            # Menstrual emergency: female-only, draws from monthly menstrual bucket.
            profile = Profile.objects.filter(Employee_id=applicant).first()
            gender = (getattr(profile, "gender", "") or "").strip().lower()
            if gender != "female":
                raise s.ValidationError(
                    {"leave_type": ["Menstrual leave is available to female employees only."]}
                )
            if (summary.menstrual_leaves or 0) < 1:
                raise s.ValidationError(
                    {"non_field_errors": ["No menstrual leave available this month."]}
                )
        else:
            # Enforce emergency leave quota: emergency_leaves is filled from total_leaves (10%) on create and decremented on use
            if duration > summary.emergency_leaves:
                raise s.ValidationError(
                    {
                        "non_field_errors": [
                            f"Insufficient emergency leave balance. Remaining emergency: {summary.emergency_leaves}, requested: {duration}."
                        ]
                    }
                )

        with transaction.atomic():
            application = serializer.save()
            application.is_emergency = True
            _set_team_lead_from_profile(application, application.applicant)
            # For emergency: all approvers default to Approved
            application.team_lead_approval = approved
            application.HR_approval = approved
            application.MD_approval = approved
            application.admin_approval = None
            application.approved_by_MD_at = timezone.now()
            _set_initial_alternative_approval(application, status_map)
            application.save(update_fields=[
                "is_emergency",
                "team_lead",
                "team_lead_approval",
                "HR_approval",
                "MD_approval",
                "admin_approval",
                "approved_by_MD_at",
                "alternative_approval",
                "alternative_responded_at",
            ])

            if is_menstrual:
                # Menstrual emergency draws from monthly menstrual bucket only.
                summary.menstrual_leaves = 0
                summary.save(update_fields=["menstrual_leaves"])
            else:
                # Decrement emergency quota and add to used_leaves
                summary.emergency_leaves = summary.emergency_leaves - duration
                summary.used_leaves = summary.used_leaves + duration
                summary.save(update_fields=["emergency_leaves", "used_leaves"])
        application.refresh_from_db()
        return Response(
            LeaveApplicationResponseSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="menstrual", permission_classes=[IsAuthenticated])
    def menstrual_leave(self, request):
        """
        Dedicated endpoint for menstrual leave.
        POST /accounts/leave-applications/menstrual/

        Body (exactly 3 fields):
            {
                "date": "YYYY-MM-DD",
                "leave_subject": "...",
                "reason": "..."
            }

        Behaviour:
            - Female applicants only (Profile.gender == "Female"); else 400.
            - Requires LeaveSummary.menstrual_leaves >= 1; else 400.
            - Auto-fills leave_type=Menstrual, duration_of_days=1,
              half_day_slots=None, is_emergency=False.
            - Auto-approves team_lead/HR/MD rails (admin left null);
              applicant does NOT need any approver to act.
            - Decrements LeaveSummary.menstrual_leaves to 0 immediately
              (idempotent — the post_save signal will not double-decrement).
            - Does NOT touch used_leaves, casual_leaves, earn_leaves,
              unpaid_leaves, emergency_leaves, or any other user's data.
            - The created row appears in /view_history/ (applicant) and
              /approval/ (HR/MD/TeamLead) endpoints unchanged, marked
              Approved.
        """
        from rest_framework import serializers as s

        serializer = MenstrualLeaveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        applicant = request.user

        profile = Profile.objects.filter(Employee_id=applicant).first()
        gender = (getattr(profile, "gender", "") or "").strip().lower()
        if gender != "female":
            raise s.ValidationError(
                {"leave_type": ["Menstrual leave is available to female employees only."]}
            )

        summary, _ = LeaveSummary.objects.get_or_create(
            user=applicant,
            defaults={"total_leaves": 0, "used_leaves": 0},
        )
        if (summary.menstrual_leaves or 0) < 1:
            raise s.ValidationError(
                {"non_field_errors": ["No menstrual leave available this month."]}
            )

        try:
            menstrual_type = LeaveTypes.objects.get(name="Menstrual")
        except LeaveTypes.DoesNotExist:
            raise s.ValidationError(
                {"non_field_errors": ["Menstrual leave type is not configured."]}
            )

        status_map = _get_leave_status_map()
        approved = status_map.get("Approved")

        with transaction.atomic():
            application = LeaveApplicationData.objects.create(
                applicant=applicant,
                start_date=serializer.validated_data["date"],
                duration_of_days=Decimal("1"),
                leave_subject=serializer.validated_data["leave_subject"],
                reason=serializer.validated_data["reason"],
                leave_type=menstrual_type,
                half_day_slots=None,
                is_emergency=False,
            )
            _set_team_lead_from_profile(application, applicant)
            application.team_lead_approval = approved
            application.HR_approval = approved
            application.MD_approval = approved
            application.admin_approval = None
            application.approved_by_MD_at = timezone.now()
            application.save(update_fields=[
                "team_lead",
                "team_lead_approval",
                "HR_approval",
                "MD_approval",
                "admin_approval",
                "approved_by_MD_at",
            ])
            # Decrement the monthly bucket. Idempotent: helper no-ops if
            # menstrual_leaves is already 0, so the post_save signal that
            # fires on the application above (which also calls this helper
            # for Menstrual + MD-Approved rows) cannot double-decrement.
            _consume_menstrual_leave(applicant)

        application.refresh_from_db()
        return Response(
            LeaveApplicationResponseSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="short", permission_classes=[IsAuthenticated])
    def short_leave(self, request):
        """
        Two-hour short leave inside configured office hours.
        Sequential approval: Team lead → HR → MD (team-lead applicant: HR → MD;
        HR applicant: MD only). Interns must have a profile team lead.
        Short-leave rows cannot be deleted.
        POST body: ``date``, ``short_leave_start_time``, ``leave_subject``, ``reason``.
        """
        from rest_framework import serializers as ser

        serializer = ShortLeaveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applicant = request.user
        role_app, tl_from_profile = _get_applicant_role_and_teamlead(applicant)
        if role_app == "Intern" and not tl_from_profile:
            raise ser.ValidationError(
                {"non_field_errors": ["Interns must have an assigned team lead to request short leave."]}
            )
        try:
            short_type = LeaveTypes.objects.get(name=SHORT_LEAVE_TYPE_NAME)
        except LeaveTypes.DoesNotExist:
            raise ser.ValidationError(
                {"non_field_errors": ["Short Leave leave type is not configured. Contact admin to run migrations."]}
            )
        vd = serializer.validated_data
        dur = ShortLeaveCreateSerializer.duration_of_days_decimal()
        status_map = _get_leave_status_map()
        validate_short_leave_monthly_quota(applicant)

        with transaction.atomic():
            application = LeaveApplicationData.objects.create(
                applicant=applicant,
                start_date=vd["date"],
                duration_of_days=dur,
                leave_subject=vd["leave_subject"],
                reason=vd["reason"],
                leave_type=short_type,
                half_day_slots=None,
                is_emergency=False,
                MD_approval=None,
                short_leave_start_time=vd["short_leave_start_time"],
            )
            _set_team_lead_from_profile(application, applicant)
            _set_short_leave_approvals(application, applicant, status_map)
            _set_initial_alternative_approval(application, status_map)
            application.save(update_fields=[
                "team_lead",
                "team_lead_approval",
                "HR_approval",
                "MD_approval",
                "admin_approval",
                "approved_by_MD_at",
                "alternative_approval",
                "alternative_responded_at",
            ])

        application.refresh_from_db()
        return Response(
            LeaveApplicationResponseSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """PUT: full update; delegate to partial_update logic for allowed fields."""
        partial = kwargs.get("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self._apply_update_by_role(instance, serializer.validated_data, request.user)
        return Response(LeaveApplicationResponseSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        """PATCH: update allowed fields by role (approval fields or applicant's draft fields)."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self._apply_update_by_role(instance, serializer.validated_data, request.user)
        return Response(LeaveApplicationResponseSerializer(instance).data)

    def _apply_update_by_role(self, instance, validated_data, user):
        """Apply validated_data according to role: approvers set their approval; applicant can edit draft."""
        from rest_framework import serializers as s

        role = _get_user_role_sync(user)
        _, teamlead = _get_applicant_role_and_teamlead(instance.applicant)
        is_applicant = user == instance.applicant
        is_teamlead = teamlead == user
        # Superusers may act as MD even if they don't have a Profile row whose
        # Role.role_name == "MD" (mirrors the IsMD permission). Without this,
        # an MD payload from a superuser was silently dropped, leaving the
        # leave Pending and skipping the casual->earn->unpaid waterfall.
        is_md = (role == "MD") or bool(getattr(user, "is_superuser", False))

        old_tl_ap = instance.team_lead_approval
        old_hr_ap = instance.HR_approval
        old_admin_ap = instance.admin_approval
        old_alt_ap = instance.alternative_approval

        # Capture MD approval state before we change it (for leave_summary update)
        old_md_approved = (
            instance.MD_approval
            and getattr(instance.MD_approval, "name", None) == "Approved"
        )
        old_admin_approved = (
            old_admin_ap
            and getattr(old_admin_ap, "name", None) == "Approved"
        )

        approval_updates = {}
        if "team_lead_approval" in validated_data and is_teamlead:
            approval_updates["team_lead_approval"] = validated_data.pop("team_lead_approval")
        if "HR_approval" in validated_data and role == "HR":
            if _is_short_leave_instance(instance) and _short_leave_use_sequential_chain(instance.applicant):
                if _short_leave_requires_tl_approved_before_hr(instance):
                    cur_tl = instance.team_lead_approval
                    if not (cur_tl and cur_tl.name == "Approved"):
                        raise s.ValidationError(
                            {"HR_approval": ["Team lead must approve this short leave before HR."]}
                        )
            approval_updates["HR_approval"] = validated_data.pop("HR_approval")
        if "admin_approval" in validated_data and role == "Admin":
            if _short_leave_on_legacy_admin_rail(instance):
                cur_hr = instance.HR_approval
                if not (cur_hr and cur_hr.name == "Approved"):
                    raise s.ValidationError(
                        {"admin_approval": ["HR must approve this short leave before Admin."]}
                    )
            approval_updates["admin_approval"] = validated_data.pop("admin_approval")
        if "MD_approval" in validated_data and is_md:
            if _is_short_leave_instance(instance) and _short_leave_requires_hr_approved_before_md(instance):
                cur_hr = instance.HR_approval
                if not (cur_hr and cur_hr.name == "Approved"):
                    raise s.ValidationError(
                        {"MD_approval": ["HR must approve this short leave before MD."]}
                    )
            md_status = validated_data.pop("MD_approval")
            approval_updates["MD_approval"] = md_status
            if md_status and md_status.name == "Approved":
                approval_updates["approved_by_MD_at"] = timezone.now()

        is_alternative = bool(instance.alternative_id and user.id == instance.alternative_id)
        if "alternative_approval" in validated_data:
            if not is_alternative:
                raise s.ValidationError(
                    {"alternative_approval": ["Only the designated alternative may update this field."]}
                )
            alt_status = validated_data.pop("alternative_approval")
            cur = getattr(getattr(instance, "alternative_approval", None), "name", None)
            if cur in ("Approved", "Rejected"):
                raise s.ValidationError(
                    {"alternative_approval": ["You have already responded to this request."]}
                )
            if alt_status.name not in ("Approved", "Rejected"):
                raise s.ValidationError(
                    {"alternative_approval": ["Cover response must be Approved or Rejected."]}
                )
            approval_updates["alternative_approval"] = alt_status
            approval_updates["alternative_responded_at"] = timezone.now()

        for key, value in approval_updates.items():
            setattr(instance, key, value)

        draft_fields = (
            "start_date",
            "short_leave_start_time",
            "duration_of_days",
            "leave_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "alternative",
        )
        updated_fields = list(approval_updates.keys())

        status_pending = (_get_leave_status_map().get("Pending"))

        # Short leave sequential: advance HR / MD Pending after prior approver Accepted.
        if _is_short_leave_instance(instance) and _short_leave_use_sequential_chain(instance.applicant):
            tl_upd = approval_updates.get("team_lead_approval")
            tl_was_approved = old_tl_ap and old_tl_ap.name == "Approved"
            if tl_upd and tl_upd.name == "Approved" and not tl_was_approved and status_pending:
                if instance.HR_approval_id is None:
                    instance.HR_approval = status_pending
                    updated_fields.append("HR_approval")
            hr_upd = approval_updates.get("HR_approval")
            hr_was_approved = old_hr_ap and old_hr_ap.name == "Approved"
            if hr_upd and hr_upd.name == "Approved" and not hr_was_approved and status_pending:
                if _short_leave_on_legacy_admin_rail(instance):
                    pass
                elif instance.MD_approval_id is None:
                    instance.MD_approval = status_pending
                    updated_fields.append("MD_approval")

        # When MD just approved (was not already Approved), deduct from the right bucket
        # (non-emergency only; emergency already updated at create).
        if (
            approval_updates.get("MD_approval")
            and getattr(approval_updates["MD_approval"], "name", None) == "Approved"
            and not old_md_approved
            and not instance.is_emergency
        ):
            leave_type_name = getattr(getattr(instance, "leave_type", None), "name", "") or ""
            if leave_type_name == "Menstrual":
                _consume_menstrual_leave(instance.applicant)
            elif leave_type_name != "Short Leave":
                debit = _debit_amount_for(instance)
                if debit > 0:
                    split = _consume_casual_earn_unpaid(instance.applicant, debit)
                    instance.casual_used = split["casual"]
                    instance.earn_used = split["earn"]
                    instance.unpaid_used = split["unpaid"]
                    updated_fields.extend(["casual_used", "earn_used", "unpaid_used"])

        # Applicant can update content fields only if no approval is yet Approved (draft)
        if is_applicant:
            has_approval = any([
                (instance.team_lead_approval and instance.team_lead_approval.name == "Approved"),
                (instance.HR_approval and instance.HR_approval.name == "Approved"),
                (instance.MD_approval and instance.MD_approval.name == "Approved"),
                (instance.admin_approval and instance.admin_approval.name == "Approved"),
            ])
            if has_approval and any(k in validated_data for k in draft_fields):
                raise s.ValidationError({"non_field_errors": ["Cannot edit application after an approval has been granted."]})
            if not has_approval:
                old_alternative_id = instance.alternative_id
                for field in draft_fields:
                    if field in validated_data:
                        setattr(instance, field, validated_data[field])
                        updated_fields.append(field)
                if "alternative" in validated_data:
                    status_map_sl = _get_leave_status_map()
                    _resync_alternative_approval_if_alternative_changed(
                        instance, status_map_sl, old_alternative_id
                    )
                    for extra in ("alternative_approval", "alternative_responded_at"):
                        if extra not in updated_fields:
                            updated_fields.append(extra)
                if "duration_of_days" in validated_data and not _is_short_leave_instance(instance):
                    _validate_remaining_leaves(instance.applicant, validated_data["duration_of_days"])

        if updated_fields:
            instance.save(update_fields=list(dict.fromkeys(updated_fields)))

        # ---- transition-based leave notifications (idempotent) ----
        # Notify only when rail transitions from non-Approved -> Approved.
        # Keep short/emergency flow untouched via helpers' internal guards.
        new_alt_name = getattr(getattr(instance, "alternative_approval", None), "name", None)
        old_alt_name = getattr(old_alt_ap, "name", None) if old_alt_ap else None
        if new_alt_name == "Approved" and old_alt_name != "Approved":
            notify_after_alternative_approved(instance, user)

        new_tl_name = getattr(getattr(instance, "team_lead_approval", None), "name", None)
        old_tl_name = getattr(old_tl_ap, "name", None) if old_tl_ap else None
        if new_tl_name == "Approved" and old_tl_name != "Approved":
            notify_hr_after_team_lead_approved(instance, user)

        new_hr_name = getattr(getattr(instance, "HR_approval", None), "name", None)
        old_hr_name = getattr(old_hr_ap, "name", None) if old_hr_ap else None
        if new_hr_name == "Approved" and old_hr_name != "Approved":
            notify_md_after_hr_approved(instance, user)

        new_md_name = getattr(getattr(instance, "MD_approval", None), "name", None)
        if new_md_name == "Approved" and not old_md_approved:
            notify_applicant_final_approval(instance, user)

    def destroy(self, request, *args, **kwargs):
        """DELETE: applicant can delete own application if MD has not yet approved."""
        instance = self.get_object()
        if _is_short_leave_instance(instance):
            return Response(
                {"detail": "Short leave requests cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.user != instance.applicant:
            return Response(
                {"detail": "You may only delete your own leave application."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if instance.MD_approval and instance.MD_approval.name == "Approved":
            return Response(
                {"detail": "Cannot delete an application that has been approved by MD."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------- GET: my leave summary (total / used / remaining + per-category balances) ----------
    @action(detail=False, methods=["get"], url_path="summary")
    def leave_summary(self, request):
        """
        Logged-in user's leave balance.
        GET /accounts/leave-applications/summary/

        Backwards-compatible: every key returned by the previous version is preserved
        (`total_leaves`, `used_leaves`, `remaining_leaves`, `remaining_emergency_leave`).
        Extra keys added without breaking existing clients:
        `username`, `name`, `gender`, `is_female`, `role`, `leave_policy`,
        `emergency_leaves`, `casual_leaves`, `earn_leaves`, `menstrual_leaves`.
        Interns receive `leave_policy` = `intern` and `casual_leaves` / `earn_leaves`
        as `0` in the response; approved full/half-day debits accrue `unpaid_leaves`.
        `menstrual_leaves` is always `0` for non-female employees.
        `short_leaves_remaining` counts approved short leaves left this month.
        """
        summary, _ = LeaveSummary.objects.get_or_create(
            user=request.user,
            defaults={
                "total_leaves": 0,
                "used_leaves": 0,
                "short_leaves_remaining": short_leave_monthly_quota(),
                "short_leave_credit_month_first": _current_month_first(),
            },
        )
        sync_short_leave_monthly_calendar(request.user)
        summary.refresh_from_db()

        profile = Profile.objects.filter(Employee_id=request.user).select_related("Role").first()
        display_name = (getattr(profile, "Name", None) or request.user.username) if profile else request.user.username
        gender_raw = (getattr(profile, "gender", None) or "") if profile else ""
        is_female = gender_raw.strip().lower() == "female"
        role_name = getattr(getattr(profile, "Role", None), "role_name", None)
        is_intern = role_name == INTERN_ROLE_NAME

        return Response(
            {
                "username": request.user.username,
                "name": display_name,
                "gender": gender_raw or None,
                "is_female": is_female,
                "role": role_name,
                "leave_policy": "intern" if is_intern else "employee",

                "total_leaves": summary.total_leaves,
                "used_leaves": summary.used_leaves,
                "remaining_leaves": summary.remaining_leaves,

                "emergency_leaves": summary.emergency_leaves,
                "remaining_emergency_leave": summary.emergency_leaves,

                "casual_leaves": 0 if is_intern else summary.casual_leaves,
                "earn_leaves": 0 if is_intern else summary.earn_leaves,
                "menstrual_leaves": summary.menstrual_leaves if is_female else 0,
                "unpaid_leaves": summary.unpaid_leaves,
                "short_leaves_remaining": summary.short_leaves_remaining,
                "short_leave_monthly_quota": short_leave_monthly_quota(),
            }
        )

    # ---------- GET: view history (my applications) ----------
    @action(detail=False, methods=["get"], url_path="view_history")
    def view_history(self, request):
        """
        Logged-in user's leave application history.
        GET /accounts/leave-applications/view_history/
        """
        qs = self.get_queryset().filter(applicant=request.user)
        serializer = LeaveApplicationResponseSerializer(qs, many=True)
        return Response(serializer.data)

    # ---------- PATCH / DELETE on a single history row ----------
    # Strict, applicant-scoped editing/cancellation of a row visible in the
    # applicant's own history. Implemented as a NEW detail action so the
    # standard CRUD endpoints (`partial_update`, `destroy`) keep their
    # existing behaviour and approver-side update flow stays untouched.
    #
    #   PATCH  /accounts/leave-applications/{id}/view_history/
    #     Edit content fields (start_date, duration_of_days, leave_subject,
    #     reason, leave_type, half_day_slots, alternative) of an application
    #     that the caller owns AND on which no approval has been granted yet.
    #     Approval-fields are not accepted here; use the regular
    #     PATCH /{id}/ for approver workflows.
    #
    #   DELETE /accounts/leave-applications/{id}/view_history/
    #     Cancel an application that the caller owns AND on which MD has not
    #     yet approved. Only the targeted row is deleted; no related rows or
    #     other tables are affected.
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="view_history",
        permission_classes=[IsAuthenticated],
    )
    def view_history_modify(self, request, pk=None):
        """Applicant-only PATCH (draft fields) / DELETE (pre-MD-approval) for own history rows."""
        instance = self.get_object()

        # Ownership check applies to BOTH methods. Approver-side actions must
        # keep using PATCH /{id}/ — they will get 403 here on purpose.
        if request.user != instance.applicant:
            return Response(
                {"detail": "You may only modify your own leave application."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method.upper() == "DELETE":
            if _is_short_leave_instance(instance):
                return Response(
                    {"detail": "Short leave requests cannot be deleted."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Same rule as the standard `destroy`: cannot delete after MD
            # approval. Only this single row is removed.
            if instance.MD_approval and instance.MD_approval.name == "Approved":
                return Response(
                    {"detail": "Cannot delete an application that has been approved by MD."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # ---- PATCH ----
        # Block editing once ANY approver has marked Approved (not just MD),
        # to keep the history view consistent with what approvers already
        # acted on. Mirrors the rule in `_apply_update_by_role`.
        has_approval = any([
            (instance.team_lead_approval and instance.team_lead_approval.name == "Approved"),
            (instance.HR_approval and instance.HR_approval.name == "Approved"),
            (instance.MD_approval and instance.MD_approval.name == "Approved"),
            (instance.admin_approval and instance.admin_approval.name == "Approved"),
        ])
        if has_approval:
            return Response(
                {"detail": "Cannot edit application after an approval has been granted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        DRAFT_FIELDS = (
            "start_date",
            "short_leave_start_time",
            "duration_of_days",
            "leave_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "alternative",
        )
        forbidden = sorted(set(request.data.keys()) - set(DRAFT_FIELDS))
        if forbidden:
            return Response(
                {"detail": f"Fields not editable from history: {forbidden}. Use the regular endpoint for approval fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaveApplicationUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Re-validate balance only if duration actually changed (not short leave).
        if "duration_of_days" in serializer.validated_data:
            lt_after = serializer.validated_data.get("leave_type") or getattr(instance, "leave_type", None)
            lt_name_after = getattr(lt_after, "name", "") or ""
            if lt_name_after != SHORT_LEAVE_TYPE_NAME:
                _validate_remaining_leaves(
                    instance.applicant, serializer.validated_data["duration_of_days"]
                )

        old_alternative_id = instance.alternative_id
        with transaction.atomic():
            updated_fields = []
            for field in DRAFT_FIELDS:
                if field in serializer.validated_data:
                    setattr(instance, field, serializer.validated_data[field])
                    updated_fields.append(field)
            if "alternative" in serializer.validated_data:
                status_map = _get_leave_status_map()
                _resync_alternative_approval_if_alternative_changed(
                    instance, status_map, old_alternative_id
                )
                for extra in ("alternative_approval", "alternative_responded_at"):
                    if extra not in updated_fields:
                        updated_fields.append(extra)
            if updated_fields:
                instance.save(update_fields=updated_fields)

        instance.refresh_from_db()
        return Response(LeaveApplicationResponseSerializer(instance).data)

    # ---------- GET: approval tab (Team lead + HR / Admin / MD + cover person – single API) ----------
    @action(detail=False, methods=["get"], url_path="approval")
    def approval(self, request):
        """
        Leave applications for the current user's approval tab. Parallel visibility:
        - Team lead: ALL applications where team_lead = user (any status).
        - HR: ALL applications where HR is an approver (HR_approval is set), any status.
        - Admin: ALL applications where Admin is an approver (admin_approval is set), any status.
        - MD: ALL applications where MD is an approver (MD_approval is set), any status.
          MD's approval is the final confirmation regardless of other approvers' state.
        - Cover person (alternative): applications where this user is the designated alternative
          and they have not yet accepted/rejected (same rules as alternative-requests/).
        Single endpoint: GET /accounts/leave-applications/approval/
        Optional pagination: ?limit=&offset= (plain array when omitted).
        """
        role = _get_user_role_sync(request.user)
        base = self.get_queryset()
        q = Q()

        # Team lead: all applications assigned to this user as team_lead (any status)
        if role in ("TeamLead", "Teamlead"):
            q |= Q(team_lead=request.user)
        # HR: parallel visibility — every application where HR is an approver,
        # regardless of team-lead state (Pending / Approved / Rejected all included).
        if role == "HR":
            q |= Q(HR_approval__isnull=False)
        # Admin: parallel visibility — every application where Admin is an approver.
        if role == "Admin":
            q |= Q(admin_approval__isnull=False)
        # MD: parallel visibility — every application where MD is an approver.
        # MD's approval is the final confirmation regardless of others' state.
        if role == "MD":
            q |= Q(MD_approval__isnull=False)

        # Cover requests: any authenticated user may be designated alternative (often not TL/HR/MD).
        # Scoped to pending response only — mirrors GET .../alternative-requests/.
        q |= Q(alternative=request.user) & (
            Q(alternative_approval__isnull=True) | Q(alternative_approval__name="Pending")
        )

        qs = (
            base.filter(q)
            .distinct()
            .select_related(
                "applicant__leave_summary",
                "applicant__accounts_profile__Role",
            )
        )
        limit, offset, paginate_enabled = _parse_pagination_params(request)
        if not paginate_enabled:
            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)

        page_qs = qs[offset : offset + limit]
        serializer = self.get_serializer(page_qs, many=True)
        return _paginated_response(qs, serializer.data, limit, offset)

    @action(detail=False, methods=["get"], url_path="alternative-requests")
    def alternative_requests(self, request):
        """
        Leave applications where the current user is the designated alternative
        and has not yet accepted/rejected (Pending or legacy null with alternative set).
        GET /accounts/leave-applications/alternative-requests/
        """
        qs = (
            self.get_queryset()
            .filter(alternative=request.user)
            .filter(Q(alternative_approval__isnull=True) | Q(alternative_approval__name="Pending"))
            .order_by("-application_date", "-id")
        )
        serializer = LeaveApplicationResponseSerializer(qs, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="alternative-respond",
        permission_classes=[IsAuthenticated],
    )
    def alternative_respond(self, request, pk=None):
        """
        Cover person accepts or rejects the handover request.
        POST /accounts/leave-applications/{id}/alternative-respond/
        Body: {"decision": "accept" | "reject"}
        Does not alter team lead / HR / MD approval state.
        """
        from rest_framework import serializers as s

        instance = self.get_object()
        if not instance.alternative_id:
            return Response(
                {"detail": "This application has no designated alternative."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance.alternative_id != request.user.id:
            return Response(
                {"detail": "Only the designated alternative can respond."},
                status=status.HTTP_403_FORBIDDEN,
            )
        cur = getattr(getattr(instance, "alternative_approval", None), "name", None)
        if cur in ("Approved", "Rejected"):
            return Response(
                {"detail": "You have already responded to this request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = AlternativeRespondSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        decision = ser.validated_data["decision"]
        status_map = _get_leave_status_map()
        approved = status_map.get("Approved")
        rejected = status_map.get("Rejected")
        if decision == "accept":
            if not approved:
                raise s.ValidationError({"detail": "Approved status is not configured."})
            instance.alternative_approval = approved
        else:
            if not rejected:
                raise s.ValidationError({"detail": "Rejected status is not configured."})
            instance.alternative_approval = rejected
        instance.alternative_responded_at = timezone.now()
        instance.save(update_fields=["alternative_approval", "alternative_responded_at"])
        instance.refresh_from_db()
        return Response(LeaveApplicationResponseSerializer(instance).data)
