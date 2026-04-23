from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .aggregates import build_metrics_payload
from .grok_client import call_grok_insight


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ems_insight(request):
    """
    GET /api/ai/ems-insight/ and GET /ai/ems-insight/

    Returns JSON (AiEmsInsightResponse shape):
      summary: str
      bullets: list[str]
      metrics: dict — role, insight_tier, org|personal aggregates (no secrets)
      model: str | null — Grok model id if call succeeded
      grok_error: str | null — set if Grok missing or failed (HTTP still 200)
    """
    metrics = build_metrics_payload(request.user)
    summary, bullets, model, grok_error = call_grok_insight(metrics)
    body = {
        "summary": summary,
        "bullets": bullets,
        "metrics": metrics,
        "model": model,
        "grok_error": grok_error,
    }
    return Response(body, status=status.HTTP_200_OK)
