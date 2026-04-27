"""
Hugging Face Inference API client for EMS insight.

Returns structured JSON: summary, bullets, improvements.
Never sends PII; input is aggregated metrics only.
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


def call_hf_insight(
    metrics: dict[str, Any],
) -> tuple[str, list[str], list[str], str | None, str | None]:
    """
    Returns (summary, bullets, improvements, model, error_message).
    On failure, error_message is set and summary/bullets/improvements are safe fallback.
    """
    token = getattr(settings, "HF_API_TOKEN", None)
    base_url = getattr(settings, "HF_API_URL", "https://api-inference.huggingface.co/models/")
    model = getattr(settings, "HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")

    if not token:
        return (
            "AI insight is not configured (missing HF_API_TOKEN).",
            [],
            ["Add HF_API_TOKEN and restart the server."],
            None,
            "Missing HF API token",
        )

    payload = json.dumps(metrics, default=str)
    prompt = (
        "You are an analytics assistant for an Employee Management System (EMS).\n"
        "You will receive ONLY aggregated metrics JSON (no PII).\n"
        "Return ONLY ONE valid JSON object (no markdown fences) with EXACTLY these keys:\n"
        '  "summary": string (2-4 sentences),\n'
        '  "bullets": array of 3-5 short strings (observations),\n'
        '  "improvements": array of 3-7 actionable EMS improvement suggestions.\n'
        "Rules:\n"
        "- Do not invent numbers; only interpret provided metrics.\n"
        "- improvements MUST be present and non-empty.\n"
        "- Suggestions should be relevant to EMS modules (tasks, leaves, assets, billing/expenses, vendors, attendance).\n\n"
        f"Metrics JSON:\n{payload}"
    )

    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/{model}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 450,
                    "temperature": 0.2,
                    "return_full_text": False,
                },
                "options": {"wait_for_model": True},
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()

        # Common HF response: [{"generated_text": "..."}]
        content = ""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            content = data[0].get("generated_text", "") or ""
        elif isinstance(data, dict):
            if data.get("error"):
                return (
                    "Unable to reach the AI service right now. Metrics are still included in this response.",
                    [],
                    ["Try again later; if it persists, verify HF_MODEL and token permissions."],
                    model,
                    str(data.get("error"))[:200],
                )
            content = data.get("generated_text", "") or ""

        if not content:
            return (
                "The model returned an empty response.",
                [],
                ["Try a different HF_MODEL or check the inference endpoint output format."],
                model,
                "Empty content",
            )

        text = _strip_json_fence(content)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Still guarantee non-empty improvements.
            return (
                content[:2000],
                [],
                ["Use a more instruction-following model and ensure it outputs strict JSON."],
                model,
                "Non-JSON output",
            )

        summary = (parsed.get("summary") or "").strip() or "No summary returned."
        bullets = parsed.get("bullets")
        improvements = parsed.get("improvements")

        if not isinstance(bullets, list):
            bullets = []
        bullets = [str(b).strip() for b in bullets if str(b).strip()][:8]

        if not isinstance(improvements, list):
            improvements = []
        improvements = [str(x).strip() for x in improvements if str(x).strip()][:12]
        if not improvements:
            improvements = [
                "Add 1-2 EMS dashboards (tasks, leave, assets/expenses) with weekly targets so teams can act on trends."
            ]

        return (summary, bullets, improvements, model, None)
    except requests.RequestException as e:
        return (
            "Unable to reach the AI service right now. Metrics are still included in this response.",
            [],
            ["Verify HF_API_TOKEN, HF_MODEL, and network connectivity."],
            None,
            str(e)[:200],
        )
    except (KeyError, TypeError, ValueError) as e:
        return (
            "The AI service returned an unexpected response.",
            [],
            ["Switch to a more instruction-following HF_MODEL and re-test."],
            None,
            str(e)[:200],
        )
