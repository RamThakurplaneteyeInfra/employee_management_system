from rest_framework import serializers
from .models import Notification
from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str


class NotificationSerializer(serializers.ModelSerializer):
    from_user = serializers.SerializerMethodField()
    receipient = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "type_of_notification",
            "from_user",
            "receipient",
            "message",
            "is_read",
            "created_at",
        ]

    def get_created_at(self, obj):
        return gmt_to_ist_str(obj.created_at, "%d/%m/%y %H:%M:%S")

    def get_from_user(self, obj):
        if obj.from_user_id is None:
            return None
        return (
            getattr(getattr(obj.from_user, "accounts_profile", None), "Name", None)
            or _get_users_Name_sync(obj.from_user)
        )

    def get_receipient(self, obj):
        if obj.receipient_id is None:
            return None
        return (
            getattr(getattr(obj.receipient, "accounts_profile", None), "Name", None)
            or _get_users_Name_sync(obj.receipient)
        )