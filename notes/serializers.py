from rest_framework import serializers

from .models import Note
from accounts.filters import _get_users_Name_sync


class NoteSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "content",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_created_by(self, obj):
        # If Profile row doesn't exist (e.g. in tests), fall back to username.
        try:
            name = _get_users_Name_sync(obj.created_by)
        except Exception:
            name = None
        return name or getattr(obj.created_by, "username", None)


class NoteCreateItemSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    content = serializers.CharField(required=True, allow_blank=False)

    def validate_title(self, value):
        if value is None:
            return None
        # store empty string as None
        v = str(value).strip()
        return v or None

    def validate_content(self, value):
        # Store trimmed content; DRF already checks it's not empty.
        return str(value).strip()

