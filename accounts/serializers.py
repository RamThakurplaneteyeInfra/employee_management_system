"""
Serializers for accounts app (leave applications, etc.).
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import LeaveApplicationData, LeaveTypes, LeaveStatus, Profile

User = get_user_model()


class LeaveApplicationListSerializer(serializers.ModelSerializer):
    """Read-only serializer for list/retrieve; includes nested names and team_lead username."""
    applicant_username = serializers.CharField(source="applicant.username", read_only=True)
    team_lead_username = serializers.CharField(
        source="team_lead.username", read_only=True, allow_null=True
    )
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    team_lead_approval_status = serializers.CharField(
        source="team_lead_approval.name", read_only=True, allow_null=True
    )
    hr_approval_status = serializers.CharField(
        source="HR_approval.name", read_only=True, allow_null=True
    )
    md_approval_status = serializers.CharField(
        source="MD_approval.name", read_only=True, allow_null=True
    )
    admin_approval_status = serializers.CharField(
        source="admin_approval.name", read_only=True, allow_null=True
    )

    class Meta:
        model = LeaveApplicationData
        fields = [
            "id",
            "applicant",
            "applicant_username",
            "team_lead",
            "team_lead_username",
            "start_date",
            "duration_of_days",
            "live_subject",
            "reason",
            "leave_type",
            "leave_type_name",
            "half_day_slots",
            "team_lead_approval",
            "team_lead_approval_status",
            "HR_approval",
            "hr_approval_status",
            "MD_approval",
            "md_approval_status",
            "admin_approval",
            "admin_approval_status",
            "is_emergency",
            "application_date",
            "approved_by_MD_at",
        ]
        read_only_fields = fields


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    """Create leave application (regular); applicant set from request.user."""
    applicant = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = LeaveApplicationData
        fields = [
            "applicant",
            "start_date",
            "duration_of_days",
            "live_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "is_emergency",
        ]

    def validate_duration_of_days(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("duration_of_days must be at least 1.")
        return value

    def validate_leave_type(self, value):
        if not value:
            raise serializers.ValidationError("leave_type is required.")
        return value


class LeaveApplicationEmergencyCreateSerializer(serializers.ModelSerializer):
    """HR-only: create emergency leave on behalf of any user. applicant = chosen user."""
    applicant = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    hr_approval_status = serializers.ChoiceField(
        choices=[("Approved", "Approved"), ("Pending", "Pending"), ("Rejected", "Rejected")],
        default="Approved",
        write_only=True,
        required=False,
    )

    class Meta:
        model = LeaveApplicationData
        fields = [
            "applicant",
            "start_date",
            "duration_of_days",
            "live_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "hr_approval_status",
        ]

    def validate_duration_of_days(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("duration_of_days must be at least 1.")
        return value


class LeaveApplicationUpdateSerializer(serializers.ModelSerializer):
    """PATCH/PUT: allow updating approval fields (by role) or applicant's own editable fields."""
    class Meta:
        model = LeaveApplicationData
        fields = [
            "start_date",
            "duration_of_days",
            "live_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "team_lead_approval",
            "HR_approval",
            "MD_approval",
            "admin_approval",
        ]
