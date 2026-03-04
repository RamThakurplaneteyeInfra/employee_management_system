"""
Leave application APIs: POST (regular + emergency), GET, PATCH, PUT, DELETE.
Approval hierarchy by applicant role; remaining-leaves validation; HR-only emergency leave.
"""
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
    LeaveApplicationListSerializer,
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


def _set_approvals_by_role(application, applicant, status_map, is_md_approval_by_default=False):
    """
    Set team_lead_approval, HR_approval, MD_approval, admin_approval on application
    based on applicant's role. If is_md_approval_by_default True (MD applicant), set MD=Approved.
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
        application.MD_approval_id = pending.id if pending else None
        application.admin_approval_id = None
        return
    if role_name == "HR":
        application.team_lead_approval_id = None
        application.HR_approval_id = None
        application.admin_approval_id = pending.id if pending else None
        application.MD_approval_id = pending.id if pending else None
        return
    # TeamLead, Employee, Intern (or no profile): TeamLead -> HR -> MD
    if teamlead:
        application.team_lead_approval_id = pending.id if pending else None
    else:
        application.team_lead_approval_id = None
    application.HR_approval_id = pending.id if pending else None
    application.MD_approval_id = pending.id if pending else None
    application.admin_approval_id = None


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
            "team_lead",
            "leave_type",
            "team_lead_approval",
            "HR_approval",
            "MD_approval",
            "admin_approval",
        )
        .order_by("-application_date", "-id")
    )
    serializer_class = LeaveApplicationListSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return LeaveApplicationCreateSerializer
        if self.action == "emergency_leave":
            return LeaveApplicationEmergencyCreateSerializer
        if self.action in ("update", "partial_update"):
            return LeaveApplicationUpdateSerializer
        return LeaveApplicationListSerializer

    def create(self, request, *args, **kwargs):
        """POST: apply for leave (self). Validates remaining leaves; sets approval chain by role."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applicant = request.user
        duration = serializer.validated_data.get("duration_of_days") or 0
        _validate_remaining_leaves(applicant, duration)

        status_map = _get_leave_status_map()
        with transaction.atomic():
            application = serializer.save()
            _set_team_lead_from_profile(application, applicant)
            _set_approvals_by_role(application, applicant, status_map, is_md_approval_by_default=(_get_user_role_sync(applicant) == "MD"))
            application.save(update_fields=[
                "team_lead", "team_lead_approval", "HR_approval", "MD_approval", "admin_approval",
                "approved_by_MD_at",
            ])
        application.refresh_from_db()
        return Response(
            LeaveApplicationListSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="emergency", permission_classes=[IsAuthenticated, IsHR])
    def emergency_leave(self, request):
        """
        HR only: create emergency leave on behalf of any user.
        team_lead_approval=Approved by default; HR_approval=choice; MD_approval=Pending.
        No remaining-leaves check.
        """
        serializer = LeaveApplicationEmergencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_map = _get_leave_status_map()
        approved = status_map.get("Approved")
        pending = status_map.get("Pending")
        hr_choice = serializer.validated_data.pop("hr_approval_status", "Approved")
        hr_status = status_map.get(hr_choice) or approved

        with transaction.atomic():
            application = serializer.save()
            application.is_emergency = True
            _set_team_lead_from_profile(application, application.applicant)
            application.team_lead_approval = approved
            application.HR_approval = hr_status
            application.MD_approval = pending
            application.admin_approval = None
            application.save(update_fields=[
                "is_emergency", "team_lead", "team_lead_approval", "HR_approval",
                "MD_approval", "admin_approval",
            ])
        application.refresh_from_db()
        return Response(
            LeaveApplicationListSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """PUT: full update; delegate to partial_update logic for allowed fields."""
        partial = kwargs.get("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self._apply_update_by_role(instance, serializer.validated_data, request.user)
        return Response(LeaveApplicationListSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        """PATCH: update allowed fields by role (approval fields or applicant's draft fields)."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self._apply_update_by_role(instance, serializer.validated_data, request.user)
        return Response(LeaveApplicationListSerializer(instance).data)

    def _apply_update_by_role(self, instance, validated_data, user):
        """Apply validated_data according to role: approvers set their approval; applicant can edit draft."""
        from rest_framework import serializers as s

        role = _get_user_role_sync(user)
        _, teamlead = _get_applicant_role_and_teamlead(instance.applicant)
        is_applicant = user == instance.applicant
        is_teamlead = teamlead == user

        approval_updates = {}
        if "team_lead_approval" in validated_data and is_teamlead:
            approval_updates["team_lead_approval"] = validated_data.pop("team_lead_approval")
        if "HR_approval" in validated_data and role == "HR":
            approval_updates["HR_approval"] = validated_data.pop("HR_approval")
        if "admin_approval" in validated_data and role == "Admin":
            approval_updates["admin_approval"] = validated_data.pop("admin_approval")
        if "MD_approval" in validated_data and role == "MD":
            md_status = validated_data.pop("MD_approval")
            approval_updates["MD_approval"] = md_status
            if md_status.name == "Approved":
                approval_updates["approved_by_MD_at"] = timezone.now()

        for key, value in approval_updates.items():
            setattr(instance, key, value)

        draft_fields = ("start_date", "duration_of_days", "live_subject", "reason", "leave_type", "half_day_slots")
        updated_fields = list(approval_updates.keys())

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

    # ---------- GET: view history (my applications) ----------
    @action(detail=False, methods=["get"], url_path="view_history")
    def view_history(self, request):
        """
        Logged-in user's leave application history.
        GET /accounts/leave-applications/view_history/
        """
        qs = self.get_queryset().filter(applicant=request.user)
        serializer = LeaveApplicationListSerializer(qs, many=True)
        return Response(serializer.data)

    # ---------- GET: approval tab by team lead ----------
    @action(detail=False, methods=["get"], url_path="approval_teamlead")
    def approval_teamlead(self, request):
        """
        Applications where the current user is the team lead (for approval tab).
        GET /accounts/leave-applications/approval_teamlead/
        """
        qs = self.get_queryset().filter(team_lead=request.user)
        serializer = LeaveApplicationListSerializer(qs, many=True)
        return Response(serializer.data)

    # ---------- GET: approval tab (HR / Admin / MD – single API by role) ----------
    @action(detail=False, methods=["get"], url_path="approval")
    def approval(self, request):
        """
        Leave applications pending the current user's approval. Role-based:
        - HR: applications where HR_approval = Pending
        - Admin: applications where admin_approval = Pending
        - MD: applications where MD_approval = Pending
        Returns [] if user is not HR, Admin, or MD.
        GET /accounts/leave-applications/approval/
        """
        role = _get_user_role_sync(request.user)
        if role == "HR":
            qs = self.get_queryset().filter(HR_approval__name="Pending")
        elif role == "Admin":
            qs = self.get_queryset().filter(admin_approval__name="Pending")
        elif role == "MD":
            qs = self.get_queryset().filter(MD_approval__name="Pending")
        else:
            qs = self.get_queryset().none()
        serializer = LeaveApplicationListSerializer(qs, many=True)
        return Response(serializer.data)
