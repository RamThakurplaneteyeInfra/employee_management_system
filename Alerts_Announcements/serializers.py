"""
Serializers for Alerts and Announcements.
"""
from rest_framework import serializers
from accounts.models import User
from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str
from project.models import Product
from task_management.models import TaskStatus

from .models import Alert, AlertType, Announcement, AnnouncementType


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
    # created_by is always taken from the logged-in user in the view; do not allow clients to set it.
    created_by = serializers.SlugRelatedField(
        read_only=True,
        slug_field="username",
    )
    product = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="name",
        required=True,
        allow_null=False,
    )
    percentage = serializers.IntegerField(required=True)
    # GET helpers: full creator name and IST timestamp; type/product already returned as names via SlugRelatedField.
    creator_name = serializers.SerializerMethodField()
    created_at_ist = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id",
            "announcement",
            "created_by",
            "creator_name",
            "type",
            "product",
            "percentage",
            "created_at",
            "created_at_ist",
        ]
        read_only_fields = ["created_at", "created_by"]

    def get_creator_name(self, obj):
        if not obj.created_by_id:
            return None
        return _get_users_Name_sync(obj.created_by)

    def get_created_at_ist(self, obj):
        return gmt_to_ist_str(obj.created_at, "%d/%m/%Y %H:%M:%S") if obj.created_at else None

    def validate(self, attrs):
        """
        Enforce required fields for POST:
        - announcement: non-empty text
        - type: required (AnnouncementType, by name)
        - product: required (Product, by name)
        - percentage: required (int)
        """
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
