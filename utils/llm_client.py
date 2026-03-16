"""Thin wrapper around Google GenAI SDK for narrative generation.

Provides a single ``generate`` function that:
1. Checks whether LLM is enabled (``LLM_ENABLED`` in config).
2. Calls Google Gemini with the given prompt.
3. Returns the generated text, or *None* on any failure so callers
   can fall back to their rule-based explanation.
"""

from __future__ import annotations

from loguru import logger

try:
    from google import genai
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]

_client = None


def _get_client():
    """Lazy singleton for the GenAI client."""
    global _client  # noqa: PLW0603
    if _client is not None:
        return _client

    from utils.config import GEMINI_API_KEY

    if genai is None:
        logger.warning(
            "google-genai package not installed; LLM narrative disabled"
        )
        return None

    _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def generate(prompt: str) -> str | None:
    """Call the LLM and return generated text, or None on failure.

    Returns None (instead of raising) when:
    - LLM is disabled via config
    - The SDK is not installed
    - The API call fails for any reason
    """
    from utils.config import LLM_ENABLED, LLM_MODEL, LLM_TEMPERATURE

    if not LLM_ENABLED:
        logger.debug("LLM narrative disabled (LLM_ENABLED=false)")
        return None

    client = _get_client()
    if client is None:
        return None

    try:
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config={
                "temperature": LLM_TEMPERATURE,
                "max_output_tokens": 512,
            },
        )

        if response and response.text:
            text: str = response.text.strip()
            logger.debug("LLM generated {} chars", len(text))
            return text

        logger.warning("LLM returned empty response")
        return None

    except Exception:
        logger.opt(exception=True).warning("LLM generation failed; using fallback")
        return None
