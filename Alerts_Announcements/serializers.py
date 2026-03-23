"""
Serializers for Alerts and Announcements.
"""
from rest_framework import serializers
from accounts.models import User
from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str
from project.models import Product
from task_management.models import TaskStatus

from .models import Alert, AlertType, Announcement, AnnouncementType, Attention


# -------- Alert types (read-only list) --------
class AlertTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertType
        fields = ["id", "type_name"]


# -------- Alerts --------
class AlertSerializer(serializers.ModelSerializer):
    alert_type = serializers.SlugRelatedField(
        queryset=AlertType.objects.all(),
        slug_field="type_name",
    )
    status = serializers.SlugRelatedField(
        queryset=TaskStatus.objects.all(),
        slug_field="status_name",
        required=False,
        allow_null=True,
    )
    details = serializers.CharField(required=False, allow_blank=True)
    resolved_by = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username",
        write_only=True,
    )
    closed_by = serializers.DateTimeField(required=True)
    # GET response: formatted datetimes and names (alert_creator, resolved_by, raw created_at/close_at omitted)
    creator_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    close_at = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            "id",
            "alert_title",
            "alert_type",
            "alert_severity",
            "creator_name",
            "details",
            "created_at",
            "close_at",
            "resolved_by",
            "resolved_by_name",
            "closed_by",
            "status",
        ]
        read_only_fields = ["created_at", "close_at"]

    def get_creator_name(self, obj):
        if not obj.alert_creator_id:
            return None
        return _get_users_Name_sync(obj.alert_creator)

    def get_resolved_by_name(self, obj):
        if not obj.resolved_by_id:
            return None
        return _get_users_Name_sync(obj.resolved_by)

    def get_created_at(self, obj):
        return gmt_to_ist_str(obj.created_at, "%d/%m/%Y %H:%M:%S") if obj.created_at else None

    def get_close_at(self, obj):
        return gmt_to_ist_str(obj.close_at, "%d/%m/%Y %H:%M:%S") if obj.close_at else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Format closed_by as d/m/y H:M:S in GET response
        if instance.closed_by:
            data["closed_by"] = gmt_to_ist_str(instance.closed_by, "%d/%m/%Y %H:%M:%S")
        else:
            data["closed_by"] = None
        return data


# -------- Announcement types (read-only list) --------
class AnnouncementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementType
        fields = ["id", "type_name"]


# -------- Announcements --------
class AnnouncementSerializer(serializers.ModelSerializer):
    # Required fields for POST: announcement, type, product, percentage.
    announcement = serializers.CharField(required=True, allow_blank=False)
    type = serializers.SlugRelatedField(
        queryset=AnnouncementType.objects.all(),
        slug_field="type_name",
        required=True,
    )
    # GET: created_by returns full name of creator (username not exposed).
    created_by = serializers.SerializerMethodField()
    product = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="name",
        required=True,
        allow_null=False,
    )
    percentage = serializers.IntegerField(required=True)
    # GET: created_at returns IST-formatted datetime only.
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id",
            "announcement",
            "created_by",
            "type",
            "product",
            "percentage",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_created_by(self, obj):
        if not obj.created_by_id:
            return None
        return _get_users_Name_sync(obj.created_by)

    def get_created_at(self, obj):
        return gmt_to_ist_str(obj.created_at, "%d/%m/%Y %H:%M:%S") if obj.created_at else None

    def validate(self, attrs):
        """
        Enforce required fields only for POST/PUT (full payload). Skip for PATCH (partial update).
        """
        if self.partial:
            return attrs
        announcement = attrs.get("announcement")
        if not announcement or not str(announcement).strip():
            raise serializers.ValidationError({"announcement": "This field is required."})

        if attrs.get("type") is None:
            raise serializers.ValidationError({"type": "This field is required."})

        if attrs.get("product") is None:
            raise serializers.ValidationError({"product": "This field is required."})

        if attrs.get("percentage") is None:
            raise serializers.ValidationError({"percentage": "This field is required."})

        return attrs


# -------- Attention --------
class AttentionSerializer(serializers.ModelSerializer):
    """
    Attention is a separate model/section from Alert (“alter”).
    GET returns creator display name.
    """

    class StatusField(serializers.Field):
        """
        Accept status as:
        - int 1/2/3
        - numeric strings "1"/"2"/"3"
        - strings: pending, in_progress, in progress, complete
        Output is always int 1..3.
        """

        def to_representation(self, value):
            return int(value) if value is not None else None

        def to_internal_value(self, data):
            if data is None:
                raise serializers.ValidationError("status is required.")

            # ints: 1/2/3
            if isinstance(data, int):
                status_int = data
            else:
                # numeric strings / textual statuses
                if isinstance(data, str):
                    raw = data.strip()
                else:
                    raw = str(data).strip()

                # Numeric string support
                if raw.isdigit():
                    status_int = int(raw)
                else:
                    normalized = raw.lower().replace("_", " ")
                    normalized = " ".join(normalized.split())  # collapse whitespace
                    if normalized == "pending":
                        status_int = 1
                    elif normalized in ("in progress", "inprogress"):
                        status_int = 2
                    elif normalized == "complete":
                        status_int = 3
                    else:
                        raise serializers.ValidationError(
                            "Invalid status. Use 1/2/3 or pending/in_progress/complete."
                        )

            if status_int not in (1, 2, 3):
                raise serializers.ValidationError("Invalid status value. Allowed: 1, 2, 3.")
            return status_int

    attention_creator = serializers.SerializerMethodField()
    status = StatusField(required=False)
    target_employee = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Attention
        fields = [
            "id",
            "attention_title",
            "description",
            "attention_creator",
            "status",
            "target_employee",
            "created_at",
        ]
        read_only_fields = ["id", "attention_creator", "created_at"]

    def get_attention_creator(self, obj):
        return _get_users_Name_sync(obj.attention_creator)

    def create(self, validated_data):
        # attention_creator is set in viewset.
        return super().create(validated_data)

    def validate(self, attrs):
        """
        Enforce that target_employee is present for create/update requests.
        Allow missing on partial PATCH where user might only edit text fields.
        """
        if self.partial:
            return attrs
        # For PUT: required; for POST: required.
        if "target_employee" not in attrs or attrs.get("target_employee") is None:
            raise serializers.ValidationError({"target_employee": "This field is required."})
        return attrs
