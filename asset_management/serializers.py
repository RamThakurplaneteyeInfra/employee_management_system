from django.db.models import Max
from rest_framework import serializers

from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            "id",
            "asset_name",
            "start_at",
            "end_at",
            "asset_type",
            "assigned_to",
            "location",
            "purpose",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        asset_name = attrs.get("asset_name", getattr(self.instance, "asset_name", None))
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))

        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError(
                {"end_at": "End must be after Start."}
            )

        # Prevent double-booking same asset for overlapping time window
        if asset_name and start_at and end_at:
            qs = Asset.objects.filter(asset_name=asset_name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            overlaps = qs.filter(start_at__lt=end_at, end_at__gt=start_at)
            if overlaps.exists():
                next_available = overlaps.aggregate(mx=Max("end_at"))["mx"]
                payload = {
                    "asset_name": "This asset is already booked for the selected time.",
                }
                if next_available:
                    payload["next_available"] = next_available.isoformat()
                raise serializers.ValidationError(payload)

        return attrs
