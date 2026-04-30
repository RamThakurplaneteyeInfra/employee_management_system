from __future__ import annotations

import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import AiSummary
from .serializers import RunSummaryRequestSerializer, AiSummaryResponseSerializer
from .services.aggregation import build_metrics_for_type
from .services.groq_client import GroqNotConfigured, generate_markdown_summary
from .services.prompts import prompt_for_type

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_summary(request):
    """
    POST /api/ai/summary/run/
    Body: {"type": "intern" | "employee" | "teamlead" | "md"}
    Response: {type, metrics, summary, created_at}

    Side effects: INSERT only into AiSummary (no updates/deletes to other tables).
    """
    ser = RunSummaryRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    summary_type = ser.validated_data["type"]

    try:
        metrics, row_user = build_metrics_for_type(request.user, summary_type)
    except PermissionError:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    except ValueError:
        return Response({"detail": "Invalid type"}, status=status.HTTP_400_BAD_REQUEST)

    prompt = prompt_for_type(summary_type, metrics)
    try:
        markdown = generate_markdown_summary(prompt)
    except GroqNotConfigured:
        return Response(
            {"detail": "GROQ_API_KEY is not configured on the server."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    obj = AiSummary.objects.create(
        user=row_user,
        type=summary_type,
        metrics=metrics,
        markdown=markdown,
    )

    logger.info("ai_summary run OK: type=%s user=%s", summary_type, request.user.pk)
    return Response(AiSummaryResponseSerializer(obj).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def latest_summary(request):
    """
    GET /api/ai/summary/latest/?type=intern
    Response: same structure as /run/, or {"summary": null} if none exists.
    """
    summary_type = (request.GET.get("type") or "").strip().lower()
    if summary_type not in {c[0] for c in AiSummary.SummaryType.choices}:
        return Response({"detail": "Invalid type"}, status=status.HTTP_400_BAD_REQUEST)

    user_filter = {"user": request.user}
    if summary_type == "md":
        user_filter = {"user__isnull": True}

    obj = (
        AiSummary.objects.filter(type=summary_type, **user_filter)
        .order_by("-created_at")
        .first()
    )
    if not obj:
        return Response({"summary": None}, status=status.HTTP_200_OK)
    return Response(AiSummaryResponseSerializer(obj).data, status=status.HTTP_200_OK)

