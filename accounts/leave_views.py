"""
Leave application APIs: POST (regular + emergency), GET, PATCH, PUT, DELETE.
Approval hierarchy by applicant role; remaining-leaves validation; HR-only emergency leave.
"""
from decimal import Decimal

from django.utils import timezone
from django.db import transaction
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
)
from .filters import _get_user_role_sync


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
    """Return the Decimal amount to debit for a given (non-Menstrual, non-Emergency) leave."""
    leave_type_name = getattr(getattr(application, "leave_type", None), "name", "") or ""
    if leave_type_name == "Half_day":
        return Decimal("0.5")
    return Decimal(application.duration_of_days or 0)


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
        )
        .order_by("-application_date", "-id")
    )
    serializer_class = LeaveApplicationResponseSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return LeaveApplicationCreateSerializer
        if self.action == "emergency_leave":
            return LeaveApplicationEmergencyCreateSerializer
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
            application.save(update_fields=[
                "team_lead", "team_lead_approval", "HR_approval", "MD_approval", "admin_approval",
                "approved_by_MD_at",
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
            application.save(update_fields=[
                "is_emergency",
                "team_lead",
                "team_lead_approval",
                "HR_approval",
                "MD_approval",
                "admin_approval",
                "approved_by_MD_at",
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

        # Capture MD approval state before we change it (for leave_summary update)
        old_md_approved = (
            instance.MD_approval
            and getattr(instance.MD_approval, "name", None) == "Approved"
        )

        approval_updates = {}
        if "team_lead_approval" in validated_data and is_teamlead:
            approval_updates["team_lead_approval"] = validated_data.pop("team_lead_approval")
        if "HR_approval" in validated_data and role == "HR":
            approval_updates["HR_approval"] = validated_data.pop("HR_approval")
        if "admin_approval" in validated_data and role == "Admin":
            approval_updates["admin_approval"] = validated_data.pop("admin_approval")
        if "MD_approval" in validated_data and is_md:
            md_status = validated_data.pop("MD_approval")
            approval_updates["MD_approval"] = md_status
            if md_status and md_status.name == "Approved":
                approval_updates["approved_by_MD_at"] = timezone.now()

        for key, value in approval_updates.items():
            setattr(instance, key, value)

        draft_fields = ("start_date", "duration_of_days", "leave_subject", "reason", "leave_type", "half_day_slots", "alternative")
        updated_fields = list(approval_updates.keys())

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
            else:
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
                for field in draft_fields:
                    if field in validated_data:
                        setattr(instance, field, validated_data[field])
                        updated_fields.append(field)
                if "duration_of_days" in validated_data:
                    _validate_remaining_leaves(instance.applicant, validated_data["duration_of_days"])

        instance.save(update_fields=updated_fields)

    def destroy(self, request, *args, **kwargs):
        """DELETE: applicant can delete own application if MD has not yet approved."""
        instance = self.get_object()
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
        `username`, `name`, `gender`, `is_female`, `emergency_leaves`,
        `casual_leaves`, `earn_leaves`, `menstrual_leaves`.
        `menstrual_leaves` is always `0` for non-female employees.
        """
        summary, _ = LeaveSummary.objects.get_or_create(
            user=request.user,
            defaults={"total_leaves": 0, "used_leaves": 0},
        )

        profile = Profile.objects.filter(Employee_id=request.user).first()
        display_name = (getattr(profile, "Name", None) or request.user.username) if profile else request.user.username
        gender_raw = (getattr(profile, "gender", None) or "") if profile else ""
        is_female = gender_raw.strip().lower() == "female"

        return Response(
            {
                "username": request.user.username,
                "name": display_name,
                "gender": gender_raw or None,
                "is_female": is_female,

                "total_leaves": summary.total_leaves,
                "used_leaves": summary.used_leaves,
                "remaining_leaves": summary.remaining_leaves,

                "emergency_leaves": summary.emergency_leaves,
                "remaining_emergency_leave": summary.emergency_leaves,

                "casual_leaves": summary.casual_leaves,
                "earn_leaves": summary.earn_leaves,
                "menstrual_leaves": summary.menstrual_leaves if is_female else 0,
                "unpaid_leaves": summary.unpaid_leaves,
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

        # Re-validate balance only if duration actually changed.
        if "duration_of_days" in serializer.validated_data:
            _validate_remaining_leaves(
                instance.applicant, serializer.validated_data["duration_of_days"]
            )

        with transaction.atomic():
            updated_fields = []
            for field in DRAFT_FIELDS:
                if field in serializer.validated_data:
                    setattr(instance, field, serializer.validated_data[field])
                    updated_fields.append(field)
            if updated_fields:
                instance.save(update_fields=updated_fields)

        instance.refresh_from_db()
        return Response(LeaveApplicationResponseSerializer(instance).data)

    # ---------- GET: approval tab (Team lead + HR / Admin / MD – single API) ----------
    @action(detail=False, methods=["get"], url_path="approval")
    def approval(self, request):
        """
        Leave applications for the current user's approval tab. Parallel visibility:
        - Team lead: ALL applications where team_lead = user (any status).
        - HR: ALL applications where HR is an approver (HR_approval is set), any status.
        - Admin: ALL applications where Admin is an approver (admin_approval is set), any status.
        - MD: ALL applications where MD is an approver (MD_approval is set), any status.
          MD's approval is the final confirmation regardless of other approvers' state.
        Single endpoint: GET /accounts/leave-applications/approval/
        """
        from django.db.models import Q

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

        qs = base.filter(q).distinct()
        serializer = LeaveApplicationResponseSerializer(qs, many=True)
        return Response(serializer.data)
