from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from duckduckgo_search import DDGS
from loguru import logger

try:
    from utils.config import (
        DDG_CACHE_SIZE,
        DDG_MAX_RESULTS,
        DDG_RATE_LIMIT_SECONDS,
        DDG_RETRY_ATTEMPTS,
        DDG_TIMEOUT,
    )
except Exception:
    DDG_MAX_RESULTS = 10
    DDG_CACHE_SIZE = 128
    DDG_RATE_LIMIT_SECONDS = 2.0
    DDG_TIMEOUT = 30
    DDG_RETRY_ATTEMPTS = 2

_MIN_REQUEST_INTERVAL_SECONDS: float = DDG_RATE_LIMIT_SECONDS
_last_request_time: float = 0.0


class DuckDuckGoSearchError(Exception):
    """Raised when DuckDuckGo search fails."""


def _rate_limit() -> None:
    """Enforce minimum interval between consecutive requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        wait = _MIN_REQUEST_INTERVAL_SECONDS - elapsed
        logger.debug("Rate limiting: sleeping {:.2f}s", wait)
        time.sleep(wait)
    _last_request_time = time.time()


def _build_query(ticker: str, company_name: str | None = None) -> str:
    """Build a search query string from ticker and optional company name."""
    parts = []
    if company_name:
        parts.append(company_name)
    parts.append(ticker)
    parts.append("stock news")
    return " ".join(parts)


def _normalize_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single DuckDuckGo result into a consistent structure."""
    return {
        "title": raw.get("title", ""),
        "snippet": raw.get("body", ""),
        "url": raw.get("href", raw.get("url", "")),
        "date": raw.get("date", ""),
        "source": raw.get("source", ""),
    }


def search_news(
    ticker: str,
    company_name: str | None = None,
    max_results: int | None = None,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Search recent news articles for a stock ticker.

    Args:
        ticker: Stock symbol (e.g. "RELIANCE.NS").
        company_name: Optional human-readable company name for better results.
        max_results: Maximum number of results to return.
        use_cache: Whether to use the LRU cache for repeated queries.

    Returns:
        List of dicts with keys: title, snippet, url, date, source.
    """
    ticker = ticker.strip().upper()
    if not ticker:
        raise DuckDuckGoSearchError("Ticker symbol cannot be empty.")

    if max_results is None:
        max_results = DDG_MAX_RESULTS
    query = _build_query(ticker, company_name)
    logger.info("Searching news: query='{}', max_results={}", query, max_results)

    if use_cache:
        return _cached_search(query, max_results)
    return _execute_search(query, max_results)


@lru_cache(maxsize=DDG_CACHE_SIZE)
def _cached_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Cached wrapper around the actual search execution."""
    return _execute_search(query, max_results)


def _execute_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Execute the DuckDuckGo news search with rate limiting, timeout, and retry."""
    _rate_limit()

    last_exc = None
    for attempt in range(DDG_RETRY_ATTEMPTS):
        try:
            with DDGS(timeout=DDG_TIMEOUT) as ddgs:
                raw_results = list(ddgs.news(query, max_results=max_results))

            if not raw_results:
                logger.warning("No news results found for query: '{}'", query)
                return []

            results = [_normalize_result(r) for r in raw_results]
            logger.debug("Found {} news results for '{}'", len(results), query)
            return results

        except DuckDuckGoSearchError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < DDG_RETRY_ATTEMPTS - 1:
                wait = 2.0 * (attempt + 1)
                logger.warning(
                    "DuckDuckGo search failed for '{}' (attempt {}/{}), retrying in {:.1f}s: {}",
                    query, attempt + 1, DDG_RETRY_ATTEMPTS, wait, exc,
                )
                time.sleep(wait)
            else:
                logger.error("DuckDuckGo search failed for '{}': {}", query, exc)
                raise DuckDuckGoSearchError(f"Search failed for '{query}': {exc}") from exc

    raise DuckDuckGoSearchError(f"Search failed for '{query}': {last_exc}") from last_exc


def clear_cache() -> None:
    """Clear the search results cache."""
    _cached_search.cache_clear()
    logger.info("DuckDuckGo search cache cleared")
