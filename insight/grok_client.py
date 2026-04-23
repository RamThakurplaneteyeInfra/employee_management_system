"""
Call xAI Grok (OpenAI-compatible chat completions). API key from settings only.
"""
from __future__ import annotations

import json
import re
from typing import Any

import requests
from django.conf import settings


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return t


def call_grok_insight(
    metrics: dict[str, Any],
) -> tuple[str, list[str], str | None, str | None]:
    """
    Returns (summary, bullets, model, error_message).
    On failure, error_message is set and summary/bullets are fallback.
    """
    key = getattr(settings, "GROK_API_KEY", None) or getattr(settings, "XAI_API_KEY", None)
    url = getattr(settings, "GROK_API_URL", "https://api.x.ai/v1/chat/completions")
    model = getattr(settings, "GROK_MODEL", "grok-2-latest")

    if not key:
        return (
            "AI insight is not configured (missing GROK_API_KEY or XAI_API_KEY).",
            [],
            None,
            "Missing API key",
        )

    payload = json.dumps(metrics, default=str)
    user_prompt = (
        "You help summarize EMS (employee management) metrics for a logged-in user. "
        "The JSON below contains ONLY pre-aggregated counts and totals — no person names, emails, or secrets.\n"
        "Respond with a single JSON object (no markdown fences) with exactly these keys:\n"
        '  "summary": string, 2-4 clear sentences in plain language;\n'
        '  "bullets": array of 3-5 short strings with actionable or observational points.\n'
        "Do not invent numbers; only interpret what is given. Do not mention passwords, tokens, or personal identifiers.\n\n"
        f"Metrics JSON:\n{payload}"
    )

    try:
        r = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You output only valid JSON with keys summary and bullets. No PII, no code fences unless inside JSON string values (avoid fences).",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        used = data.get("model") or model
        if not content:
            return (
                "The model returned an empty response.",
                [],
                used,
                "Empty content",
            )
        text = _strip_json_fence(content)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return (content[:2000], [], used, None)

        summary = (parsed.get("summary") or "").strip() or "No summary returned."
        bullets = parsed.get("bullets")
        if not isinstance(bullets, list):
            bullets = []
        bullets = [str(b).strip() for b in bullets if str(b).strip()][:8]
        return (summary, bullets, used, None)
    except requests.RequestException as e:
        return (
            "Unable to reach the AI service right now. Metrics are still included in this response.",
            [],
            None,
            str(e)[:200],
        )
    except (KeyError, TypeError, ValueError) as e:
        return (
            "The AI service returned an unexpected response.",
            [],
            None,
            str(e)[:200],
        )
