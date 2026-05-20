from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from accounts.filters import _get_users_Name_sync
from accounts.models import Profile

from .models import TourAdvanceAttachment, TourAdvanceMember, TourAdvanceRequest
from .permissions import is_admin_or_md
from .s3_helpers import (
    attachment_read_payload,
    is_allowed_s3_key,
    normalize_s3_key_from_client,
)


def _resolve_user_by_employee_id(employee_id):
    if not employee_id:
        return None
    username = str(employee_id).strip()
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        raise serializers.ValidationError(
            {"employeeId": [f"No employee found with id '{username}'."]}
        )


def _member_detail(user):
    profile = getattr(user, "accounts_profile", None)
    name = getattr(profile, "Name", None) if profile else None
    return {
        "employeeId": user.username,
        "fullName": name or _get_users_Name_sync(user) or user.username,
    }


def _compute_no_of_days(start_date, end_date, provided):
    if provided is not None and provided > 0:
        return provided
    if start_date and end_date:
        delta = (end_date - start_date).days + 1
        return max(delta, 0)
    return provided or 0


def _parse_attachment_amount(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise serializers.ValidationError("amount must be a valid number.")
    if amount < 0:
        raise serializers.ValidationError("amount cannot be negative.")
    return amount


class TourAdvanceAttachmentInputSerializer(serializers.Serializer):
    fileName = serializers.CharField(required=False, allow_blank=True, default="")
    fileType = serializers.CharField(required=False, allow_blank=True, default="")
    fileSize = serializers.IntegerField(required=False, min_value=0, default=0)
    fileUrl = serializers.CharField()
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0")
    )

    def validate_fileUrl(self, value):
        key = normalize_s3_key_from_client(value)
        if not key:
            raise serializers.ValidationError("fileUrl is required.")
        if not is_allowed_s3_key(key):
            raise serializers.ValidationError(
                "fileUrl is not a valid tour advance attachment key."
            )
        return key

    def validate_amount(self, value):
        return _parse_attachment_amount(value)


class TourAdvanceReadSerializer(serializers.ModelSerializer):
    tourType = serializers.CharField(source="tour_type", read_only=True)
    fromLocation = serializers.CharField(source="from_location", read_only=True)
    fromLocationPincode = serializers.CharField(source="from_location_pincode", read_only=True)
    toLocation = serializers.CharField(source="to_location", read_only=True)
    toLocationPincode = serializers.CharField(source="to_location_pincode", read_only=True)
    clientName = serializers.CharField(source="client_name", read_only=True)
    purposeOfVisit = serializers.CharField(source="purpose_of_visit", read_only=True)
    startDate = serializers.DateField(source="start_date", read_only=True)
    endDate = serializers.DateField(source="end_date", read_only=True)
    noOfDays = serializers.IntegerField(source="no_of_days", read_only=True)
    employeeId = serializers.CharField(source="primary_employee.username", read_only=True)
    employeeIds = serializers.SerializerMethodField()
    memberDetails = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    createdBy = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = TourAdvanceRequest
        fields = [
            "id",
            "tourType",
            "project",
            "division",
            "fromLocation",
            "fromLocationPincode",
            "toLocation",
            "toLocationPincode",
            "clientName",
            "purposeOfVisit",
            "startDate",
            "endDate",
            "noOfDays",
            "advance",
            "status",
            "employeeId",
            "employeeIds",
            "memberDetails",
            "attachments",
            "createdBy",
            "createdAt",
            "updatedAt",
        ]

    def get_employeeIds(self, obj):
        return list(
            obj.member_links.select_related("member").values_list("member__username", flat=True)
        )

    def get_memberDetails(self, obj):
        return [
            _member_detail(link.member)
            for link in obj.member_links.select_related("member__accounts_profile").all()
        ]

    def get_attachments(self, obj):
        return [
            attachment_read_payload(
                att.s3_key,
                att.file_name,
                att.file_type,
                att.file_size,
                amount=att.amount,
                attachment_id=att.id,
            )
            for att in obj.attachments.all()
        ]

    def get_createdBy(self, obj):
        if not obj.created_by:
            return None
        return _member_detail(obj.created_by)


class TourAdvanceWriteSerializer(serializers.ModelSerializer):
    tourType = serializers.CharField(source="tour_type", required=False, allow_blank=True)
    fromLocation = serializers.CharField(
        source="from_location", required=False, allow_blank=True
    )
    fromLocationPincode = serializers.CharField(
        source="from_location_pincode", required=False, allow_blank=True
    )
    toLocation = serializers.CharField(source="to_location", required=False, allow_blank=True)
    toLocationPincode = serializers.CharField(
        source="to_location_pincode", required=False, allow_blank=True
    )
    clientName = serializers.CharField(source="client_name", required=False, allow_blank=True)
    purposeOfVisit = serializers.CharField(
        source="purpose_of_visit", required=False, allow_blank=True
    )
    startDate = serializers.DateField(source="start_date", required=False, allow_null=True)
    endDate = serializers.DateField(source="end_date", required=False, allow_null=True)
    noOfDays = serializers.IntegerField(
        source="no_of_days", required=False, min_value=0, default=0
    )
    employeeId = serializers.CharField(write_only=True, required=False)
    employeeIds = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    attachments = TourAdvanceAttachmentInputSerializer(many=True, required=False)

    class Meta:
        model = TourAdvanceRequest
        fields = [
            "tourType",
            "project",
            "division",
            "fromLocation",
            "fromLocationPincode",
            "toLocation",
            "toLocationPincode",
            "clientName",
            "purposeOfVisit",
            "startDate",
            "endDate",
            "noOfDays",
            "advance",
            "status",
            "employeeId",
            "employeeIds",
            "attachments",
        ]
        extra_kwargs = {
            "project": {"required": False, "allow_blank": True},
            "division": {"required": False, "allow_blank": True},
            "advance": {"required": False},
            "status": {"required": False},
        }

    def _request_user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def _validate_employee_access(self, primary_user, member_users, *, is_create=False):
        """
        On create: any valid employeeId / employeeIds allowed (existence checked elsewhere).
        On update: non-Admin/MD cannot reassign (handled in validate); this guards legacy paths.
        """
        if is_create:
            return
        user = self._request_user()
        if not user or is_admin_or_md(user):
            return
        allowed = {user.username}
        if primary_user.username not in allowed:
            raise serializers.ValidationError(
                {"employeeId": ["You can only create requests for yourself."]}
            )
        for m in member_users:
            if m.username not in allowed:
                raise serializers.ValidationError(
                    {"employeeIds": ["You can only add yourself as a member."]}
                )

    def validate(self, attrs):
        user = self._request_user()
        is_create = self.instance is None

        if is_create:
            employee_id = self.initial_data.get("employeeId")
            if employee_id:
                primary = _resolve_user_by_employee_id(employee_id)
            elif user:
                primary = user
            else:
                raise serializers.ValidationError(
                    {"employeeId": ["employeeId is required."]}
                )
            attrs["_primary_employee"] = primary
        else:
            primary = self.instance.primary_employee

        skip_member_update = (
            not is_create
            and user
            and not is_admin_or_md(user)
            and "employeeIds" in self.initial_data
        )
        if skip_member_update:
            pass
        elif "employeeIds" in self.initial_data or is_create:
            raw_ids = self.initial_data.get("employeeIds")
            if raw_ids is None:
                raw_ids = []
            seen = set()
            member_users = []
            for eid in raw_ids:
                u = _resolve_user_by_employee_id(eid)
                if u.username not in seen:
                    seen.add(u.username)
                    member_users.append(u)
            if primary.username not in seen:
                member_users.insert(0, primary)
            attrs["_member_users"] = member_users
            if not is_create and "employeeIds" in self.initial_data:
                self._validate_employee_access(
                    primary, member_users, is_create=False
                )

        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        no_of_days = attrs.get("no_of_days")
        attrs["no_of_days"] = _compute_no_of_days(start, end, no_of_days)

        if start and end and end < start:
            raise serializers.ValidationError(
                {"endDate": ["endDate must be on or after startDate."]}
            )

        status_val = attrs.get("status")
        if status_val is not None and user and not is_admin_or_md(user):
            raise serializers.ValidationError(
                {"status": ["Only Admin or MD can change status."]}
            )

        if not is_create and user and not is_admin_or_md(user):
            if self.instance.created_by_id != user.id:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Only the creator can edit this request."]}
                )
            if self.instance.status != TourAdvanceRequest.Status.PENDING:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Only pending requests can be edited."]}
                )
            # employeeId / employeeIds in body are ignored on update (no reassignment).

        if "attachments" in self.initial_data:
            attachments = self.initial_data.get("attachments") or []
            att_ser = TourAdvanceAttachmentInputSerializer(data=attachments, many=True)
            att_ser.is_valid(raise_exception=True)
            attrs["_attachments"] = att_ser.validated_data

        return attrs

    def create(self, validated_data):
        validated_data.pop("employeeId", None)
        validated_data.pop("employeeIds", None)
        validated_data.pop("attachments", None)
        primary = validated_data.pop("_primary_employee")
        member_users = validated_data.pop("_member_users", [primary])
        attachments_data = validated_data.pop("_attachments", [])
        validated_data.pop("status", None)

        request = self.context.get("request")
        user = getattr(request, "user", None)

        validated_data["primary_employee"] = primary
        validated_data["created_by"] = user
        validated_data["status"] = TourAdvanceRequest.Status.PENDING

        with transaction.atomic():
            instance = TourAdvanceRequest.objects.create(**validated_data)
            self._sync_members(instance, member_users)
            self._sync_attachments(instance, attachments_data, user)
        return instance

    def update(self, instance, validated_data):
        validated_data.pop("employeeId", None)
        validated_data.pop("employeeIds", None)
        validated_data.pop("attachments", None)
        member_users = validated_data.pop("_member_users", None)
        attachments_data = validated_data.pop("_attachments", None)
        validated_data.pop("_primary_employee", None)

        user = self._request_user()
        if user and not is_admin_or_md(user):
            validated_data.pop("status", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if member_users is not None and user and is_admin_or_md(user):
                self._sync_members(instance, member_users)

            if attachments_data is not None:
                self._sync_attachments(instance, attachments_data, user)

        return instance

    def _sync_members(self, instance, member_users):
        TourAdvanceMember.objects.filter(request=instance).delete()
        for member in member_users:
            TourAdvanceMember.objects.get_or_create(request=instance, member=member)

    def _sync_attachments(self, instance, attachments_data, user):
        """Add or update attachments by s3_key; never delete existing rows."""
        for att in attachments_data:
            s3_key = (att.get("fileUrl") or "").strip()
            if not s3_key:
                continue
            amount = att.get("amount")
            if amount is None:
                amount = Decimal("0")
            defaults = {
                "file_name": att.get("fileName") or "",
                "file_type": att.get("fileType") or "",
                "file_size": int(att.get("fileSize") or 0),
                "amount": amount,
                "uploaded_by": user,
            }
            obj, created = TourAdvanceAttachment.objects.get_or_create(
                request=instance,
                s3_key=s3_key,
                defaults=defaults,
            )
            if not created:
                for field, value in defaults.items():
                    setattr(obj, field, value)
                obj.save(update_fields=list(defaults.keys()))


class EmployeeLookupSerializer(serializers.ModelSerializer):
    employeeId = serializers.CharField(source="Employee_id_id")
    fullName = serializers.CharField(source="Name")
    department = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["employeeId", "fullName", "department"]

    def get_department(self, obj):
        dept = getattr(obj, "Department", None)
        if dept is None:
            return None
        return getattr(dept, "dept_name", None) or str(dept)
