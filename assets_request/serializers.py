from django.contrib.auth.models import User
from rest_framework import serializers

from .models import AssetRequest


class AssetRequestSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(read_only=True, slug_field="username")
    assigned_to = serializers.SlugRelatedField(
        slug_field="username", queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = AssetRequest
        fields = [
            "id",
            "name",
            "category",
            "asset_type",
            "provider",
            "description",
            "assigned_to",
            "department",
            "admin_approval",
            "md_approval",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

