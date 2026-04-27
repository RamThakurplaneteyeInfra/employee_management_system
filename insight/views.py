from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .aggregates import build_metrics_payload
from .hf_client import call_hf_insight
from .grok_client import call_grok_insight


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ems_insight(request):
    """
    GET /api/ai/ems-insight/ and GET /ai/ems-insight/

    Returns JSON (AiEmsInsightResponse shape):
      summary: str
      bullets: list[str]
      improvements: list[str] — always present (best-effort), actionable suggestions
      metrics: dict — role, insight_tier, org|personal aggregates (no secrets)
      model: str | null — model id if call succeeded
      grok_error: str | null — set if AI missing or failed (HTTP still 200)
      ai_provider: str — "hf" or "grok" (best-effort)
    """
    metrics = build_metrics_payload(request.user)

    # Prefer Hugging Face. If not configured (or fails), fall back to Grok
    # to avoid breaking the endpoint for existing clients.
    summary, bullets, improvements, model, ai_error = call_hf_insight(metrics)
    provider = "hf"
    if ai_error:
        grok_summary, grok_bullets, grok_model, grok_error = call_grok_insight(metrics)
        # Use Grok output only if it produced something useful (or HF not configured).
        if grok_summary and (not grok_error):
            summary, bullets, model = grok_summary, grok_bullets, grok_model
            provider = "grok"
            ai_error = None
        else:
            # Keep HF error message (or Grok error if that is more informative).
            ai_error = (ai_error or grok_error) if (ai_error or grok_error) else None
        if not improvements:
            improvements = [
                "Add dashboards and alerts for task status, leave volume, and asset/expense trends so teams can act weekly.",
                "Define SLA targets for task completion and leave approvals; review exceptions in the weekly ops meeting.",
                "Introduce data quality checks for missing categories/statuses to improve reporting accuracy.",
            ]

    body = {
        "summary": summary,
        "bullets": bullets,
        "improvements": improvements,
        "metrics": metrics,
        "model": model,
        "grok_error": ai_error,
        "ai_provider": provider,
    }
    return Response(body, status=status.HTTP_200_OK)
