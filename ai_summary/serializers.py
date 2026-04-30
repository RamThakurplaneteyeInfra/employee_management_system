from __future__ import annotations

from rest_framework import serializers

from .models import AiSummary


class RunSummaryRequestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=AiSummary.SummaryType.choices)


class AiSummaryResponseSerializer(serializers.ModelSerializer):
    summary = serializers.CharField(source="markdown")

    class Meta:
        model = AiSummary
        fields = ["type", "metrics", "summary", "created_at"]

