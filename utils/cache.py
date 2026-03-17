"""Analysis-level caching backed by SQLite.

Caches computed analysis results (scores, verdicts, recommendation) per ticker.
The cache key is simply the ticker symbol. On a cache hit the caller still
generates a fresh LLM narrative, so every request involves at least one LLM call.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from utils.database import cache_get, cache_set

_SOURCE = "analysis"

try:
    from utils.config import CACHE_TTL_ANALYSIS
except Exception:
    CACHE_TTL_ANALYSIS = 900


def get_cached_analysis(ticker: str) -> dict[str, Any] | None:
    """Return cached analysis scores/verdicts for *ticker*, or None on miss."""
    result = cache_get(_SOURCE, ticker.upper())
    if result is not None:
        logger.info("Analysis cache hit for {}", ticker.upper())
    return result


def set_cached_analysis(ticker: str, data: dict[str, Any]) -> None:
    """Store analysis scores/verdicts for *ticker* with the configured TTL."""
    cache_set(_SOURCE, ticker.upper(), data, CACHE_TTL_ANALYSIS)
    logger.info("Cached analysis for {} (ttl={}s)", ticker.upper(), CACHE_TTL_ANALYSIS)
