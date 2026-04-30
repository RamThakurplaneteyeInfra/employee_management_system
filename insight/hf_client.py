"""
Hugging Face Inference API client for EMS insight.

Returns structured JSON: summary, bullets, improvements.
Never sends PII; input is aggregated metrics only.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _preview(text: str, max_len: int = 240) -> str:
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return t


def _extract_hf_text(data: Any) -> str:
    """
    Hugging Face Inference API output differs by pipeline/model.
    - text-generation / text2text-generation: [{"generated_text": "..."}]
    - translation: [{"translation_text": "..."}]
    - summarization: [{"summary_text": "..."}]
    Some models may return {"generated_text": "..."} or other dict shapes.
    """
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            for key in ("generated_text", "translation_text", "summary_text", "text", "output_text"):
                val = first.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        if isinstance(first, str) and first.strip():
            return first.strip()
        return ""

    if isinstance(data, dict):
        if isinstance(data.get("generated_text"), str) and data["generated_text"].strip():
            return data["generated_text"].strip()
        # Some endpoints nest results under keys like "result" or "results"
        nested = data.get("result") or data.get("results")
        if nested is not None:
            return _extract_hf_text(nested)
    return ""


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
        logger.warning(
            "HF insight skipped: no HF_API_TOKEN / HUGGINGFACE_API_TOKEN in environment."
        )
        return (
            "AI insight is not configured (missing HF_API_TOKEN).",
            [],
            ["Add HF_API_TOKEN and restart the server."],
            None,
            "Missing HF API token",
        )

    url = f"{base_url.rstrip('/')}/{model}"
    logger.info(
        "HF insight request: model=%s endpoint_host=%s token_configured=yes",
        model,
        url.split("/")[2] if url.startswith("http") else "?",
    )
    logger.debug("HF insight metrics keys: %s", sorted(metrics.keys()) if isinstance(metrics, dict) else type(metrics))

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
            url,
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
        logger.debug("HF insight HTTP status=%s", r.status_code)
        r.raise_for_status()
        data = r.json()

        if isinstance(data, dict) and data.get("error"):
            err = str(data.get("error"))[:200]
            logger.warning("HF insight API error payload: %s", err)
            return (
                "Unable to reach the AI service right now. Metrics are still included in this response.",
                [],
                ["Try again later; if it persists, verify HF_MODEL and token permissions."],
                model,
                err,
            )

        content = _extract_hf_text(data)
        logger.debug(
            "HF insight raw extracted text preview: %s",
            _preview(content, 400) if content else "(empty)",
        )

        if not content:
            logger.warning("HF insight empty content; response type=%s", type(data).__name__)
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
        except json.JSONDecodeError as exc:
            logger.warning(
                "HF insight JSON parse failed: %s; preview=%s",
                exc,
                _preview(text, 320),
            )
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

        logger.info(
            "HF insight OK: summary_preview=%s bullets=%d improvements=%d",
            _preview(summary, 280),
            len(bullets),
            len(improvements),
        )
        return (summary, bullets, improvements, model, None)
    except requests.RequestException as e:
        logger.warning("HF insight request failed: %s", str(e)[:200], exc_info=logger.isEnabledFor(logging.DEBUG))
        return (
            "Unable to reach the AI service right now. Metrics are still included in this response.",
            [],
            ["Verify HF_API_TOKEN, HF_MODEL, and network connectivity."],
            None,
            str(e)[:200],
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.exception("HF insight unexpected parse error: %s", str(e)[:200])
        return (
            "The AI service returned an unexpected response.",
            [],
            ["Switch to a more instruction-following HF_MODEL and re-test."],
            None,
            str(e)[:200],
        )
