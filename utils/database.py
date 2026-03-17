"""SQLite database layer for caching, analysis history, and persistent metrics.

Provides thread-safe connection management with automatic schema initialization.
The database file is created lazily on first access.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from loguru import logger

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS analysis_cache (
    cache_key   TEXT PRIMARY KEY,
    data_json   TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    ticker      TEXT    NOT NULL,
    created_at  REAL    NOT NULL,
    ttl_seconds INTEGER NOT NULL DEFAULT 900
);

CREATE TABLE IF NOT EXISTS analysis_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT    NOT NULL,
    query_type          TEXT    NOT NULL,
    fundamental_score   REAL,
    technical_score     REAL,
    sentiment_score     REAL,
    final_score         REAL,
    recommendation      TEXT,
    response_json       TEXT,
    created_at          REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics_snapshot (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot    TEXT    NOT NULL,
    created_at  REAL   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cache_source_ticker
    ON analysis_cache(source, ticker);
CREATE INDEX IF NOT EXISTS idx_cache_created
    ON analysis_cache(created_at);
CREATE INDEX IF NOT EXISTS idx_history_ticker
    ON analysis_history(ticker);
CREATE INDEX IF NOT EXISTS idx_history_created
    ON analysis_history(created_at);
"""

_lock = threading.Lock()
_connections: dict[int, sqlite3.Connection] = {}
_db_path: str | None = None


def _get_db_path() -> str:
    global _db_path  # noqa: PLW0603
    if _db_path is not None:
        return _db_path
    try:
        from utils.config import DB_PATH
        _db_path = DB_PATH
    except Exception:
        _db_path = "data/market_analyst.db"
    return _db_path


def get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating it if needed."""
    tid = threading.get_ident()
    if tid in _connections:
        return _connections[tid]

    with _lock:
        if tid in _connections:
            return _connections[tid]

        db_path = _get_db_path()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.executescript(_SCHEMA_SQL)
        conn.commit()

        _connections[tid] = conn
        logger.debug("Opened SQLite connection for thread {} at {}", tid, db_path)
        return conn


def close_all() -> None:
    """Close all thread-local connections (for shutdown / tests)."""
    with _lock:
        for tid, conn in _connections.items():
            try:
                conn.close()
            except Exception:
                pass
        _connections.clear()
    logger.debug("All SQLite connections closed")


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------

def cache_get(source: str, ticker: str) -> Any | None:
    """Retrieve a cached value if it exists and hasn't expired."""
    conn = get_connection()
    row = conn.execute(
        "SELECT data_json, created_at, ttl_seconds FROM analysis_cache "
        "WHERE cache_key = ?",
        (_cache_key(source, ticker),),
    ).fetchone()

    if row is None:
        return None

    age = time.time() - row["created_at"]
    if age > row["ttl_seconds"]:
        conn.execute(
            "DELETE FROM analysis_cache WHERE cache_key = ?",
            (_cache_key(source, ticker),),
        )
        conn.commit()
        logger.debug("Cache expired for {}:{} (age={:.0f}s)", source, ticker, age)
        return None

    logger.debug("Cache hit for {}:{} (age={:.0f}s)", source, ticker, age)
    return json.loads(row["data_json"])


def cache_set(source: str, ticker: str, data: Any, ttl_seconds: int) -> None:
    """Store a value in the cache with the given TTL."""
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO analysis_cache "
        "(cache_key, data_json, source, ticker, created_at, ttl_seconds) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_cache_key(source, ticker), json.dumps(data), source, ticker, time.time(), ttl_seconds),
    )
    conn.commit()
    logger.debug("Cached {}:{} (ttl={}s)", source, ticker, ttl_seconds)


def cache_clear(source: str | None = None) -> int:
    """Delete cached entries. If source is given, only clear that source."""
    conn = get_connection()
    if source:
        cur = conn.execute("DELETE FROM analysis_cache WHERE source = ?", (source,))
    else:
        cur = conn.execute("DELETE FROM analysis_cache")
    conn.commit()
    logger.info("Cleared {} cache entries (source={})", cur.rowcount, source or "all")
    return cur.rowcount


def cache_stats() -> dict[str, Any]:
    """Return cache statistics: total entries, entries per source, expired count."""
    conn = get_connection()
    now = time.time()

    total = conn.execute("SELECT COUNT(*) FROM analysis_cache").fetchone()[0]
    expired = conn.execute(
        "SELECT COUNT(*) FROM analysis_cache WHERE (? - created_at) > ttl_seconds",
        (now,),
    ).fetchone()[0]

    by_source = {}
    for row in conn.execute(
        "SELECT source, COUNT(*) as cnt FROM analysis_cache GROUP BY source"
    ):
        by_source[row["source"]] = row["cnt"]

    return {"total": total, "expired": expired, "by_source": by_source}


def _cache_key(source: str, ticker: str) -> str:
    return f"{source}:{ticker}"


# ---------------------------------------------------------------------------
# Analysis history
# ---------------------------------------------------------------------------

def history_save(
    ticker: str,
    query_type: str,
    fundamental_score: float | None,
    technical_score: float | None,
    sentiment_score: float | None,
    final_score: float | None,
    recommendation: str | None,
    response_json: str | None = None,
) -> int:
    """Save an analysis result to history. Returns the row ID."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO analysis_history "
        "(ticker, query_type, fundamental_score, technical_score, "
        "sentiment_score, final_score, recommendation, response_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ticker, query_type, fundamental_score, technical_score,
            sentiment_score, final_score, recommendation, response_json,
            time.time(),
        ),
    )
    conn.commit()
    logger.debug("Saved history for {} (id={})", ticker, cur.lastrowid)
    return cur.lastrowid  # type: ignore[return-value]


def history_get(
    ticker: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve analysis history, optionally filtered by ticker."""
    conn = get_connection()
    if ticker:
        rows = conn.execute(
            "SELECT * FROM analysis_history WHERE ticker = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (ticker.upper(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM analysis_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Metrics persistence
# ---------------------------------------------------------------------------

def metrics_save(snapshot: dict[str, Any]) -> int:
    """Persist a metrics snapshot."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO metrics_snapshot (snapshot, created_at) VALUES (?, ?)",
        (json.dumps(snapshot), time.time()),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def metrics_latest() -> dict[str, Any] | None:
    """Retrieve the most recent metrics snapshot."""
    conn = get_connection()
    row = conn.execute(
        "SELECT snapshot FROM metrics_snapshot ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if row:
        return json.loads(row["snapshot"])
    return None


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def purge_expired_cache() -> int:
    """Delete all expired cache entries. Returns count deleted."""
    conn = get_connection()
    now = time.time()
    cur = conn.execute(
        "DELETE FROM analysis_cache WHERE (? - created_at) > ttl_seconds",
        (now,),
    )
    conn.commit()
    logger.info("Purged {} expired cache entries", cur.rowcount)
    return cur.rowcount
