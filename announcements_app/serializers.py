from rest_framework import serializers

from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str

from .models import AnnouncementPost


class AnnouncementPostSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementPost
        fields = [
            "id",
            "title",
            "description",
            "announcement_date",
            "created_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "created_by"]

    def get_created_by(self, obj):
        if not getattr(obj, "created_by_id", None):
            return None
        return _get_users_Name_sync(obj.created_by)

    def get_created_at(self, obj):
        return gmt_to_ist_str(obj.created_at, "%d/%m/%Y %H:%M:%S") if obj.created_at else None

