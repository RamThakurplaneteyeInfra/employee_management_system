from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class GroqNotConfigured(RuntimeError):
    pass


def _get_client():
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        raise GroqNotConfigured("Missing GROQ_API_KEY")

    # Import lazily so the project can run without Groq installed until used.
    from groq import Groq  # type: ignore

    return Groq(api_key=api_key)


def generate_markdown_summary(prompt: str, model: str = "llama-3.1-8b-instant") -> str:
    client = _get_client()
    logger.info("Groq summary request: model=%s", model)
    try:
        resp: Any = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
    except Exception as e:  # pragma: no cover
        logger.warning("Groq summary failed: %s", str(e)[:200])
        raise

