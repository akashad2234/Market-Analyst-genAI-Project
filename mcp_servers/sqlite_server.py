"""MCP Server for the Market Analyst SQLite database.

Exposes tools for:
- Analysis cache management (get, clear, stats)
- Analysis history (query, search)
- Metrics persistence (save snapshot, get latest)
- Database maintenance (purge expired, table info)

Run standalone:
    python -m mcp_servers.sqlite_server
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp.server.fastmcp import FastMCP  # noqa: E402

from utils.database import (  # noqa: E402
    cache_clear,
    cache_get,
    cache_set,
    cache_stats,
    history_get,
    history_save,
    metrics_latest,
    metrics_save,
    purge_expired_cache,
)

mcp = FastMCP(
    "Market Analyst DB",
    instructions="SQLite database tools for the AI Market Analyst platform",
)


# ---------------------------------------------------------------------------
# Cache tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_cached_analysis(ticker: str) -> dict | None:
    """Retrieve cached analysis result for a ticker.

    Args:
        ticker: Stock ticker (e.g. 'RELIANCE.NS')

    Returns:
        Cached analysis dict (scores, verdicts, recommendation) or None.
    """
    return cache_get("analysis", ticker.upper())


@mcp.tool()
def store_cached_analysis(
    ticker: str,
    data: dict,
    ttl_seconds: int = 900,
) -> str:
    """Store an analysis result in the cache with a TTL.

    Args:
        ticker: Stock ticker
        data: Analysis data to cache (scores, verdicts, recommendation)
        ttl_seconds: Time-to-live in seconds (default 15 min)
    """
    cache_set("analysis", ticker.upper(), data, ttl_seconds)
    return f"Cached analysis for {ticker.upper()} with TTL={ttl_seconds}s"


@mcp.tool()
def clear_cache(source: str | None = None) -> str:
    """Clear cached entries, optionally filtered by source.

    Args:
        source: If provided, only clear entries for this source.
                If None, clears all cache entries.
    """
    count = cache_clear(source)
    scope = source or "all sources"
    return f"Cleared {count} cache entries ({scope})"


@mcp.tool()
def get_cache_stats() -> dict:
    """Get cache statistics: total entries, expired count, breakdown by source."""
    return cache_stats()


@mcp.tool()
def purge_expired() -> str:
    """Delete all expired cache entries from the database."""
    count = purge_expired_cache()
    return f"Purged {count} expired entries"


# ---------------------------------------------------------------------------
# History tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_analysis_history(ticker: str | None = None, limit: int = 20) -> list[dict]:
    """Retrieve past analysis results.

    Args:
        ticker: Filter by ticker (optional). If None, returns all.
        limit: Maximum number of results (default 20, max 100).

    Returns:
        List of analysis records sorted by most recent first.
    """
    limit = min(limit, 100)
    return history_get(ticker=ticker, limit=limit)


@mcp.tool()
def save_analysis(
    ticker: str,
    query_type: str,
    fundamental_score: float | None = None,
    technical_score: float | None = None,
    sentiment_score: float | None = None,
    final_score: float | None = None,
    recommendation: str | None = None,
) -> str:
    """Manually save an analysis result to history.

    Args:
        ticker: Stock ticker
        query_type: One of 'single_stock', 'portfolio', 'comparison'
        fundamental_score: Fundamental agent score (0-100)
        technical_score: Technical agent score (0-100)
        sentiment_score: Sentiment agent score (0-100)
        final_score: Weighted final score (0-100)
        recommendation: 'Strong Buy', 'Buy', 'Hold', or 'Avoid'
    """
    row_id = history_save(
        ticker=ticker.upper(),
        query_type=query_type,
        fundamental_score=fundamental_score,
        technical_score=technical_score,
        sentiment_score=sentiment_score,
        final_score=final_score,
        recommendation=recommendation,
    )
    return f"Saved analysis for {ticker.upper()} (id={row_id})"


# ---------------------------------------------------------------------------
# Metrics tools
# ---------------------------------------------------------------------------

@mcp.tool()
def save_metrics_snapshot(snapshot: dict) -> str:
    """Persist a metrics snapshot to the database.

    Args:
        snapshot: Metrics data (counters, latencies, errors) as a dict.
    """
    row_id = metrics_save(snapshot)
    return f"Saved metrics snapshot (id={row_id})"


@mcp.tool()
def get_latest_metrics() -> dict | None:
    """Retrieve the most recent persisted metrics snapshot."""
    return metrics_latest()


# ---------------------------------------------------------------------------
# Database info tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_tables() -> list[str]:
    """List all tables in the Market Analyst database."""
    from utils.database import get_connection

    conn = get_connection()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r["name"] for r in rows]


@mcp.tool()
def describe_table(table_name: str) -> list[dict]:
    """Get column info for a database table.

    Args:
        table_name: Name of the table to describe.
    """
    from utils.database import get_connection

    conn = get_connection()
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()  # noqa: S608
    return [
        {"name": r["name"], "type": r["type"], "nullable": not r["notnull"]}
        for r in rows
    ]


@mcp.tool()
def run_read_query(sql: str) -> list[dict]:
    """Execute a read-only SQL query against the database.

    Only SELECT statements are allowed.

    Args:
        sql: A SELECT SQL statement.
    """
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        return [{"error": "Only SELECT queries are allowed"}]

    from utils.database import get_connection

    conn = get_connection()
    try:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        return [{"error": str(exc)}]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
