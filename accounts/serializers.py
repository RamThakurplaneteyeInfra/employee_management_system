"""
Serializers for accounts app (leave applications, etc.).
"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from rest_framework import serializers
from django.contrib.auth import get_user_model

from ems.utils import gmt_to_ist_str
from .models import LeaveApplicationData, LeaveTypes, LeaveStatus, Profile, LeaveSummary

User = get_user_model()

INTERN_ROLE_NAME = "Intern"
_HR_MD_LEAVE_BALANCE_VIEW_ROLES = frozenset({"HR", "Hr", "MD"})


def _viewer_can_see_applicant_leave_balances(serializer_context) -> bool:
    """HR / MD (and superuser) may see applicant casual / earn / unpaid on approval views."""
    request = serializer_context.get("request")
    if not request or not getattr(request.user, "is_authenticated", False):
        return False
    if request.user.is_superuser:
        return True
    from accounts.filters import _get_user_role_sync

    return _get_user_role_sync(request.user) in _HR_MD_LEAVE_BALANCE_VIEW_ROLES


def _build_applicant_leave_balances(applicant):
    """Read-only snapshot from LeaveSummary; no DB writes."""
    if not applicant:
        return None
    is_intern = False
    try:
        profile = applicant.accounts_profile
        role_name = getattr(getattr(profile, "Role", None), "role_name", None)
        is_intern = role_name == INTERN_ROLE_NAME
    except Profile.DoesNotExist:
        pass
    try:
        summary = applicant.leave_summary
        casual = summary.casual_leaves or Decimal("0")
        earn = summary.earn_leaves or Decimal("0")
        unpaid = summary.unpaid_leaves or Decimal("0")
    except LeaveSummary.DoesNotExist:
        casual = earn = unpaid = Decimal("0")
    if is_intern:
        casual = earn = Decimal("0")
    return {
        "casual_leaves": casual,
        "earn_leaves": earn,
        "unpaid_leaves": unpaid,
    }


def _get_applicant_display_name(applicant):
    """Return Profile.Name if available else username."""
    if not applicant:
        return None
    try:
        profile = Profile.objects.get(Employee_id=applicant)
        return profile.Name or applicant.username
    except Profile.DoesNotExist:
        return applicant.username


def _resolve_alternative_user(value):
    """Resolve the ``alternative`` field to a ``User`` instance.

    Accepts either an Employee ID / username (e.g. ``"EMP015"``) or the
    employee's full name (``Profile.Name``, case-insensitive). Returns
    ``None`` for blank/empty input. Raises ``serializers.ValidationError``
    when the value cannot be resolved to any user.

    Read-only lookup: this helper never creates, updates, or deletes data.
    """
    if value in (None, ""):
        return None
    val = str(value).strip()
    if not val:
        return None

    user = User.objects.filter(username=val).first()
    if user:
        return user

    profile = (
        Profile.objects.filter(Name__iexact=val)
        .select_related("Employee_id")
        .first()
    )
    if profile and profile.Employee_id:
        return profile.Employee_id

    raise serializers.ValidationError(
        f"Alternative user '{val}' not found. Provide a valid Employee ID or full name."
    )


def validate_short_leave_time_window(leaving_date, start_time):
    """
    Raise serializers.ValidationError if the configured short-leave duration
    does not fit inside SHORT_LEAVE_DAY_START / SHORT_LEAVE_DAY_END.
    """
    hrs = float(getattr(settings, "SHORT_LEAVE_DURATION_HOURS", 2))
    ws = getattr(settings, "SHORT_LEAVE_DAY_START")
    we = getattr(settings, "SHORT_LEAVE_DAY_END")
    day_start = datetime.combine(leaving_date, ws)
    day_end = datetime.combine(leaving_date, we)
    start_dt = datetime.combine(leaving_date, start_time)
    end_dt = start_dt + timedelta(hours=hrs)
    if start_dt < day_start or end_dt > day_end:
        raise serializers.ValidationError(
            {
                "short_leave_start_time": [
                    f"The {int(hrs)}-hour slot must fall within office hours ({ws}–{we})."
                ]
            }
        )


class LeaveApplicationListSerializer(serializers.ModelSerializer):
    """Read-only serializer for list/retrieve; char/name fields only, no FK ids. User names from Profile.Name."""
    applicant_name = serializers.SerializerMethodField()
    team_lead_name = serializers.SerializerMethodField()
    alternative_name = serializers.SerializerMethodField()
    # Emit duration_of_days as a JSON number (e.g. 1.0, 0.5) instead of the
    # default DecimalField string ("1.0"), so existing clients keep working.
    duration_of_days = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True
    )
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    team_lead_approval_status = serializers.SerializerMethodField()
    hr_approval_status = serializers.SerializerMethodField()
    md_approval_status = serializers.SerializerMethodField()
    admin_approval_status = serializers.SerializerMethodField()
    alternative_approval_status = serializers.SerializerMethodField()
    alternative_responded_at = serializers.SerializerMethodField()
    approved_by_MD_at = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplicationData
        fields = [
            "id",
            "applicant_name",
            "team_lead_name",
            "alternative_name",
            "start_date",
            "short_leave_start_time",
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
            "alternative_approval_status",
            "alternative_responded_at",
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
        # Same helper as applicant_name / team_lead_name so behaviour is
        # identical: returns Profile.Name, falls back to username, handles
        # users with no Profile via Profile.DoesNotExist.
        return _get_applicant_display_name(getattr(obj, "alternative", None))

    def get_team_lead_approval_status(self, obj):
        st = getattr(getattr(obj, "team_lead_approval", None), "name", None)
        return st

    def get_hr_approval_status(self, obj):
        st = getattr(getattr(obj, "HR_approval", None), "name", None)
        return st

    def get_md_approval_status(self, obj):
        st = getattr(getattr(obj, "MD_approval", None), "name", None)
        return st

    def get_admin_approval_status(self, obj):
        st = getattr(getattr(obj, "admin_approval", None), "name", None)
        return st

    def get_alternative_approval_status(self, obj):
        st = getattr(getattr(obj, "alternative_approval", None), "name", None)
        return st

    def get_approved_by_MD_at(self, obj):
        return gmt_to_ist_str(obj.approved_by_MD_at, "%d/%m/%Y %H:%M:%S") if obj.approved_by_MD_at else None

    def get_alternative_responded_at(self, obj):
        t = getattr(obj, "alternative_responded_at", None)
        return gmt_to_ist_str(t, "%d/%m/%Y %H:%M:%S") if t else None


class LeaveApplicationResponseSerializer(serializers.ModelSerializer):
    """POST/GET response: char/name fields only (no FK ids). User names from Profile.Name."""
    applicant_name = serializers.SerializerMethodField()
    applicant_username = serializers.SerializerMethodField()
    applicant_leave_balances = serializers.SerializerMethodField()
    team_lead_name = serializers.SerializerMethodField()
    alternative_name = serializers.SerializerMethodField()
    # Emit duration_of_days as a JSON number (e.g. 1.0, 0.5) instead of the
    # default DecimalField string ("1.0"), so existing clients keep working.
    duration_of_days = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True
    )
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    team_lead_approval_status = serializers.SerializerMethodField()
    hr_approval_status = serializers.SerializerMethodField()
    md_approval_status = serializers.SerializerMethodField()
    admin_approval_status = serializers.SerializerMethodField()
    alternative_approval_status = serializers.SerializerMethodField()
    alternative_responded_at = serializers.SerializerMethodField()
    approved_by_MD_at = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplicationData
        fields = [
            "id",
            "applicant_name",
            "applicant_username",
            "applicant_leave_balances",
            "team_lead_name",
            "alternative_name",
            "start_date",
            "short_leave_start_time",
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
            "alternative_approval_status",
            "alternative_responded_at",
            "is_emergency",
            "application_date",
            "approved_by_MD_at",
            "casual_used",
            "earn_used",
            "unpaid_used",
        ]

    def get_applicant_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "applicant", None))

    def get_applicant_username(self, obj):
        if not _viewer_can_see_applicant_leave_balances(self.context):
            return None
        applicant = getattr(obj, "applicant", None)
        return applicant.username if applicant else None

    def get_applicant_leave_balances(self, obj):
        if not _viewer_can_see_applicant_leave_balances(self.context):
            return None
        return _build_applicant_leave_balances(getattr(obj, "applicant", None))

    def get_team_lead_name(self, obj):
        return _get_applicant_display_name(getattr(obj, "team_lead", None))

    def get_alternative_name(self, obj):
        # Same helper as applicant_name / team_lead_name so behaviour is
        # identical: returns Profile.Name, falls back to username, handles
        # users with no Profile via Profile.DoesNotExist.
        return _get_applicant_display_name(getattr(obj, "alternative", None))

    def get_team_lead_approval_status(self, obj):
        st = getattr(getattr(obj, "team_lead_approval", None), "name", None)
        return st

    def get_hr_approval_status(self, obj):
        st = getattr(getattr(obj, "HR_approval", None), "name", None)
        return st

    def get_md_approval_status(self, obj):
        st = getattr(getattr(obj, "MD_approval", None), "name", None)
        return st

    def get_admin_approval_status(self, obj):
        st = getattr(getattr(obj, "admin_approval", None), "name", None)
        return st

    def get_alternative_approval_status(self, obj):
        st = getattr(getattr(obj, "alternative_approval", None), "name", None)
        return st

    def get_approved_by_MD_at(self, obj):
        return gmt_to_ist_str(obj.approved_by_MD_at, "%d/%m/%Y %H:%M:%S") if obj.approved_by_MD_at else None

    def get_alternative_responded_at(self, obj):
        t = getattr(obj, "alternative_responded_at", None)
        return gmt_to_ist_str(t, "%d/%m/%Y %H:%M:%S") if t else None


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    """Create leave application (regular). leave_type as string (Full_day/Half_day); validation by type."""
    applicant = serializers.HiddenField(default=serializers.CurrentUserDefault())
    leave_type = serializers.CharField(max_length=20, trim_whitespace=True)
    # Optional for Half_day (defaulted to 1 in validate()); required >= 1 for Full_day.
    # DecimalField with coerce_to_string=False so half-day floats (e.g. 0.5, 1.5)
    # are accepted on input and the response stays a JSON number, not a string.
    duration_of_days = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        allow_null=True,
        min_value=Decimal("0"),
        coerce_to_string=False,
    )
    # Accept the alternative user's username string (e.g. "EMP015").
    alternative = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="username of the alternative user",
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
            "is_emergency",
        ]

    def validate_alternative(self, value):
        return _resolve_alternative_user(value)

    def validate_leave_type(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("leave_type is required.")
        try:
            return LeaveTypes.objects.get(name__iexact=name)
        except LeaveTypes.DoesNotExist:
            raise serializers.ValidationError(
                f"leave_type must be one of: Full_day, Half_day, Menstrual (got '{value}')."
            )

    def validate(self, attrs):
        leave_type = attrs.get("leave_type")
        if leave_type:
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
            elif name == "Menstrual":
                # Female-only single-day leave from a separate monthly bucket.
                request = self.context.get("request") if hasattr(self, "context") else None
                applicant = getattr(request, "user", None) if request else None
                profile = Profile.objects.filter(Employee_id=applicant).first() if applicant else None
                gender = (getattr(profile, "gender", "") or "").strip().lower()
                if gender != "female":
                    raise serializers.ValidationError(
                        {"leave_type": "Menstrual leave is available to female employees only."}
                    )
                attrs["duration_of_days"] = 1
                attrs["half_day_slots"] = None
        applicant = attrs.get("applicant")
        alt_user = attrs.get("alternative")
        if alt_user and applicant and alt_user.pk == applicant.pk:
            raise serializers.ValidationError(
                {"alternative": "You cannot designate yourself as the alternative cover person."}
            )
        return attrs


class LeaveApplicationEmergencyCreateSerializer(serializers.ModelSerializer):
    """HR-only: create emergency leave on behalf of any user. applicant = username, leave_type = string, with optional note."""
    applicant = serializers.CharField(trim_whitespace=True)
    leave_type = serializers.CharField(max_length=20, trim_whitespace=True)
    # DecimalField mirrors the model: accepts half-day floats on input (>= 1
    # rule preserved in validate_duration_of_days below for emergency leaves).
    duration_of_days = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        coerce_to_string=False,
    )
    # Accept the alternative user's username string only.
    alternative = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="username of the alternative user",
    )
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
        return _resolve_alternative_user(value)

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

    def validate(self, attrs):
        applicant = attrs.get("applicant")
        alt = attrs.get("alternative")
        if applicant and alt and getattr(alt, "pk", None) == applicant.pk:
            raise serializers.ValidationError(
                {"alternative": "Applicant cannot be their own alternative cover person."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("hr_approval_status", None)
        return super().create(validated_data)


class LeaveApplicationUpdateSerializer(serializers.ModelSerializer):
    """PATCH/PUT: all FK-like inputs as strings. Approval = Approved/Pending/Rejected; leave_type = Full_day/Half_day."""
    team_lead_approval = serializers.CharField(required=False, allow_blank=False)
    HR_approval = serializers.CharField(required=False, allow_blank=False)
    MD_approval = serializers.CharField(required=False, allow_blank=False)
    admin_approval = serializers.CharField(required=False, allow_blank=False)
    # Cover person only (enforced in leave_views._apply_update_by_role).
    alternative_approval = serializers.CharField(required=False, allow_blank=False)
    leave_type = serializers.CharField(required=False, allow_blank=True)
    short_leave_start_time = serializers.TimeField(required=False, allow_null=True)
    # Accept half-day floats on PATCH/PUT; mirrors the model's DecimalField.
    duration_of_days = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        allow_null=True,
        min_value=Decimal("0"),
        coerce_to_string=False,
    )
    # Accept the alternative user's username string only.
    alternative = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="username of the alternative user",
    )

    class Meta:
        model = LeaveApplicationData
        fields = [
            "start_date",
            "short_leave_start_time",
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
            "alternative_approval",
        ]

    def validate_alternative(self, value):
        return _resolve_alternative_user(value)

    _APPROVAL_NAMES = {"Approved", "Pending", "Rejected"}
    _LEAVE_TYPE_NAMES = {"Full_day", "Half_day", "Short Leave"}

    def validate(self, attrs):
        # Resolve approval status names to LeaveStatus
        for key in (
            "team_lead_approval",
            "HR_approval",
            "MD_approval",
            "admin_approval",
            "alternative_approval",
        ):
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
                    {"leave_type": "Must be one of: Full_day, Half_day, Short Leave."}
                )
            attrs["leave_type"] = LeaveTypes.objects.get(name=name)
        elif "leave_type" in attrs and (attrs["leave_type"] is None or attrs["leave_type"] == ""):
            attrs.pop("leave_type", None)
        instance = getattr(self, "instance", None)
        alt = attrs.get("alternative")
        if alt is not None and instance and instance.applicant_id and getattr(alt, "pk", None) == instance.applicant_id:
            raise serializers.ValidationError(
                {"alternative": "You cannot designate yourself as the alternative cover person."}
            )
        if instance and instance.pk:
            eff_lt = attrs.get("leave_type") or getattr(instance, "leave_type", None)
            eff_name = getattr(eff_lt, "name", None) or ""
            if eff_name == "Short Leave":
                sd = attrs.get("start_date", getattr(instance, "start_date", None))
                st = attrs.get(
                    "short_leave_start_time",
                    getattr(instance, "short_leave_start_time", None),
                )
                if sd and st:
                    validate_short_leave_time_window(sd, st)
        return attrs


class AlternativeRespondSerializer(serializers.Serializer):
    """Body for POST .../leave-applications/{id}/alternative-respond/."""

    decision = serializers.ChoiceField(choices=["accept", "reject"])


class MenstrualLeaveCreateSerializer(serializers.Serializer):
    """
    Minimal payload for the dedicated menstrual leave endpoint.

    Accepts exactly three input fields:
        - date          : start date of the leave (mapped to LeaveApplicationData.start_date)
        - leave_subject : short subject line (max 255 chars)
        - reason        : free-form reason text

    The view fills in `leave_type=Menstrual`, `duration_of_days=1`,
    `half_day_slots=None`, `is_emergency=False`, and auto-approves all
    rails. This serializer only validates / shapes the input; it does
    not create or modify any DB rows.
    """

    date = serializers.DateField(required=True)
    leave_subject = serializers.CharField(required=True, max_length=255, allow_blank=False)
    reason = serializers.CharField(required=True, allow_blank=False)


class ShortLeaveCreateSerializer(serializers.Serializer):
    """
    POST /accounts/leave-applications/short/
    Fixed-duration short leave (see settings.SHORT_LEAVE_DURATION_HOURS).
    """

    date = serializers.DateField()
    short_leave_start_time = serializers.TimeField()
    leave_subject = serializers.CharField(required=True, max_length=255, allow_blank=False)
    reason = serializers.CharField(required=True, allow_blank=False)

    def validate(self, attrs):
        d = attrs["date"]
        t = attrs["short_leave_start_time"]
        validate_short_leave_time_window(d, t)
        return attrs

    @staticmethod
    def duration_of_days_decimal():
        h = Decimal(str(getattr(settings, "SHORT_LEAVE_DURATION_HOURS", 2)))
        day = Decimal(str(getattr(settings, "SHORT_LEAVE_WORKING_DAY_HOURS", 8)))
        if day <= 0:
            day = Decimal("8")
        return (h / day).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
