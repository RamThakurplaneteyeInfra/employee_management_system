"""
Serializers for accounts app (leave applications, etc.).
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from ems.utils import gmt_to_ist_str
from .models import LeaveApplicationData, LeaveTypes, LeaveStatus, Profile

User = get_user_model()


def _get_applicant_display_name(applicant):
    """Return Profile.Name if available else username."""
    if not applicant:
        return None
    try:
        profile = Profile.objects.get(Employee_id=applicant)
        return profile.Name or applicant.username
    except Profile.DoesNotExist:
        return applicant.username


class LeaveApplicationListSerializer(serializers.ModelSerializer):
    """Read-only serializer for list/retrieve; char/name fields only, no FK ids. User names from Profile.Name."""
    applicant_name = serializers.SerializerMethodField()
    team_lead_name = serializers.SerializerMethodField()
    alternative_name = serializers.SerializerMethodField()
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
    approved_by_MD_at = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplicationData
        fields = [
            "id",
            "applicant_name",
            "team_lead_name",
            "alternative_name",
            "start_date",
            "duration_of_days",
            "leave_subject",
            "reason",
            "note",
            "leave_type_name",
            "half_day_slots",
            "team_lead_approval_status",
            "hr_approval_status",
            "md_approval_status",
            "admin_approval_status",
            "is_emergency",
            "application_date",
            "approved_by_MD_at",
        ]
        read_only_fields = fields

    def get_applicant_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "applicant", None))

    def get_team_lead_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "team_lead", None))

    def get_alternative_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "alternative", None))

    def get_approved_by_MD_at(self, obj):
        return gmt_to_ist_str(obj.approved_by_MD_at, "%d/%m/%Y %H:%M:%S") if obj.approved_by_MD_at else None


class LeaveApplicationResponseSerializer(serializers.ModelSerializer):
    """POST/GET response: char/name fields only (no FK ids). User names from Profile.Name."""
    applicant_name = serializers.SerializerMethodField()
    team_lead_name = serializers.SerializerMethodField()
    alternative_name = serializers.SerializerMethodField()
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
    approved_by_MD_at = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplicationData
        fields = [
            "id",
            "applicant_name",
            "team_lead_name",
            "alternative_name",
            "start_date",
            "duration_of_days",
            "leave_subject",
            "reason",
            "note",
            "leave_type_name",
            "half_day_slots",
            "team_lead_approval_status",
            "hr_approval_status",
            "md_approval_status",
            "admin_approval_status",
            "is_emergency",
            "application_date",
            "approved_by_MD_at",
        ]

    def get_applicant_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "applicant", None))

    def get_team_lead_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "team_lead", None))

    def get_alternative_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "alternative", None))

    def get_approved_by_MD_at(self, obj):
        return gmt_to_ist_str(obj.approved_by_MD_at, "%d/%m/%Y %H:%M:%S") if obj.approved_by_MD_at else None


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    """Create leave application (regular). leave_type as string (Full_day/Half_day); validation by type."""
    applicant = serializers.HiddenField(default=serializers.CurrentUserDefault())
    leave_type = serializers.CharField(max_length=20, trim_whitespace=True)
    # Optional for Half_day (defaulted to 1 in validate()); required >= 1 for Full_day
    duration_of_days = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    alternative = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = LeaveApplicationData
        fields = [
            "applicant",
            "start_date",
            "duration_of_days",
            "leave_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "alternative",
            "is_emergency",
        ]

    def validate_alternative(self, value):
        if not value or (isinstance(value, str) and not value.strip()):
            return None
        username = value.strip()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Alternative user with this username does not exist.")

    def validate_leave_type(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("leave_type is required.")
        try:
            return LeaveTypes.objects.get(name__iexact=name)
        except LeaveTypes.DoesNotExist:
            raise serializers.ValidationError(
                f"leave_type must be one of: Full_day, Half_day (got '{value}')."
            )

    def validate(self, attrs):
        leave_type = attrs.get("leave_type")
        if not leave_type:
            return attrs
        name = getattr(leave_type, "name", None) or str(leave_type)
        half_day_slots = attrs.get("half_day_slots")
        if name == "Full_day":
            # No validation on half_day_slots for Full_day
            dur = attrs.get("duration_of_days")
            if dur is not None and dur < 1:
                raise serializers.ValidationError({"duration_of_days": "duration_of_days must be at least 1 for Full_day."})
            if dur is None:
                attrs["duration_of_days"] = 1
        elif name == "Half_day":
            # No validation on duration_of_days for Half_day; default to 1
            if attrs.get("duration_of_days") is None or attrs.get("duration_of_days", 0) < 1:
                attrs["duration_of_days"] = 1
            # Validation on half_day_slots required
            if not half_day_slots or (isinstance(half_day_slots, str) and not half_day_slots.strip()):
                raise serializers.ValidationError(
                    {"half_day_slots": "half_day_slots is required for Half_day (First_Half or Second_Half)."}
                )
            allowed = {"First_Half", "Second_Half"}
            if half_day_slots not in allowed and (isinstance(half_day_slots, str) and half_day_slots.strip() not in allowed):
                raise serializers.ValidationError(
                    {"half_day_slots": "half_day_slots must be First_Half or Second_Half for Half_day."}
                )
        return attrs


class LeaveApplicationEmergencyCreateSerializer(serializers.ModelSerializer):
    """HR-only: create emergency leave on behalf of any user. applicant = username, leave_type = string, with optional note."""
    applicant = serializers.CharField(trim_whitespace=True)
    leave_type = serializers.CharField(max_length=20, trim_whitespace=True)
    alternative = serializers.CharField(required=False, allow_blank=True, allow_null=True)
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
            "leave_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "alternative",
            "note",
            "hr_approval_status",
        ]

    def validate_alternative(self, value):
        if not value or (isinstance(value, str) and not value.strip()):
            return None
        username = value.strip()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Alternative user with this username does not exist.")

    def validate_leave_type(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("leave_type is required.")
        try:
            return LeaveTypes.objects.get(name__iexact=name)
        except LeaveTypes.DoesNotExist:
            raise serializers.ValidationError(
                "leave_type must be one of: Full_day, Half_day."
            )

    def validate_applicant(self, value):
        username = (value or "").strip()
        if not username:
            raise serializers.ValidationError("Applicant username is required.")
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this username does not exist.")

    def validate_duration_of_days(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("duration_of_days must be at least 1.")
        return value

    def create(self, validated_data):
        validated_data.pop("hr_approval_status", None)
        return super().create(validated_data)


class LeaveApplicationUpdateSerializer(serializers.ModelSerializer):
    """PATCH/PUT: all FK-like inputs as strings. Approval = Approved/Pending/Rejected; leave_type = Full_day/Half_day."""
    team_lead_approval = serializers.CharField(required=False, allow_blank=False)
    HR_approval = serializers.CharField(required=False, allow_blank=False)
    MD_approval = serializers.CharField(required=False, allow_blank=False)
    admin_approval = serializers.CharField(required=False, allow_blank=False)
    leave_type = serializers.CharField(required=False, allow_blank=True)
    alternative = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = LeaveApplicationData
        fields = [
            "start_date",
            "duration_of_days",
            "leave_subject",
            "reason",
            "leave_type",
            "half_day_slots",
            "alternative",
            "team_lead_approval",
            "HR_approval",
            "MD_approval",
            "admin_approval",
        ]

    def validate_alternative(self, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        username = (value or "").strip()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Alternative user with this username does not exist.")

    _APPROVAL_NAMES = {"Approved", "Pending", "Rejected"}
    _LEAVE_TYPE_NAMES = {"Full_day", "Half_day"}

    def validate(self, attrs):
        # Resolve approval status names to LeaveStatus
        for key in ("team_lead_approval", "HR_approval", "MD_approval", "admin_approval"):
            val = attrs.get(key)
            if val is not None and val != "":
                name = (val.strip() if isinstance(val, str) else str(val)).strip()
                if name not in self._APPROVAL_NAMES:
                    raise serializers.ValidationError(
                        {key: "Must be one of: Approved, Pending, Rejected."}
                    )
                attrs[key] = LeaveStatus.objects.get(name=name)
        # Resolve leave_type name to LeaveTypes (for applicant draft edit)
        val = attrs.get("leave_type")
        if val is not None and val != "":
            name = (val.strip() if isinstance(val, str) else str(val)).strip()
            if name not in self._LEAVE_TYPE_NAMES:
                raise serializers.ValidationError(
                    {"leave_type": "Must be one of: Full_day, Half_day."}
                )
            attrs["leave_type"] = LeaveTypes.objects.get(name=name)
        elif "leave_type" in attrs and (attrs["leave_type"] is None or attrs["leave_type"] == ""):
            attrs.pop("leave_type", None)
        return attrs
