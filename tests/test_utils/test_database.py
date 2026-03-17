import time
from unittest.mock import patch

import pytest

from utils.database import (
    cache_clear,
    cache_get,
    cache_set,
    cache_stats,
    close_all,
    get_connection,
    history_get,
    history_save,
    metrics_latest,
    metrics_save,
    purge_expired_cache,
)


@pytest.fixture(autouse=True)
def _clean_db():
    """Use an in-memory DB for each test to avoid cross-test contamination."""
    import utils.database as db_mod

    db_mod._db_path = ":memory:"
    db_mod._connections.clear()
    yield
    close_all()
    db_mod._db_path = None


class TestConnection:
    def test_get_connection_returns_connection(self):
        conn = get_connection()
        assert conn is not None
        result = conn.execute("SELECT 1").fetchone()
        assert result[0] == 1

    def test_same_thread_returns_same_connection(self):
        c1 = get_connection()
        c2 = get_connection()
        assert c1 is c2

    def test_schema_tables_created(self):
        conn = get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "analysis_cache" in names
        assert "analysis_history" in names
        assert "metrics_snapshot" in names


class TestCache:
    def test_set_and_get(self):
        cache_set("analysis", "RELIANCE.NS", {"score": 75}, 3600)
        result = cache_get("analysis", "RELIANCE.NS")
        assert result == {"score": 75}

    def test_get_missing_returns_none(self):
        assert cache_get("analysis", "NONEXISTENT") is None

    def test_expired_entry_returns_none(self):
        cache_set("analysis", "TCS.NS", {"score": 60}, 1)
        with patch("utils.database.time") as mock_time:
            mock_time.time.return_value = time.time() + 10
            result = cache_get("analysis", "TCS.NS")
        assert result is None

    def test_replace_existing_entry(self):
        cache_set("analysis", "INFY.NS", {"score": 50}, 3600)
        cache_set("analysis", "INFY.NS", {"score": 55}, 3600)
        result = cache_get("analysis", "INFY.NS")
        assert result == {"score": 55}

    def test_cache_dict_data(self):
        data = {"scores": {"fund": 70, "tech": 60}, "recommendation": "Buy"}
        cache_set("analysis", "TCS.NS", data, 900)
        result = cache_get("analysis", "TCS.NS")
        assert result == data

    def test_clear_by_source(self):
        cache_set("analysis", "A.NS", {"a": 1}, 3600)
        cache_set("other", "B.NS", {"b": 2}, 300)
        count = cache_clear("analysis")
        assert count == 1
        assert cache_get("analysis", "A.NS") is None
        assert cache_get("other", "B.NS") is not None

    def test_clear_all(self):
        cache_set("analysis", "A.NS", {"a": 1}, 3600)
        cache_set("analysis", "B.NS", {"b": 2}, 300)
        count = cache_clear()
        assert count == 2

    def test_cache_stats(self):
        cache_set("analysis", "A.NS", {}, 3600)
        cache_set("analysis", "B.NS", {}, 3600)
        cache_set("analysis", "C.NS", {}, 900)
        stats = cache_stats()
        assert stats["total"] == 3
        assert stats["by_source"]["analysis"] == 3

    def test_purge_expired(self):
        cache_set("analysis", "OLD.NS", {}, 1)
        with patch("utils.database.time") as mock_time:
            mock_time.time.return_value = time.time() + 10
            purged = purge_expired_cache()
        assert purged == 1


class TestHistory:
    def test_save_and_retrieve(self):
        row_id = history_save(
            ticker="RELIANCE.NS",
            query_type="single_stock",
            fundamental_score=75.0,
            technical_score=60.0,
            sentiment_score=80.0,
            final_score=71.0,
            recommendation="Buy",
        )
        assert row_id >= 1

        records = history_get(ticker="RELIANCE.NS")
        assert len(records) == 1
        assert records[0]["ticker"] == "RELIANCE.NS"
        assert records[0]["final_score"] == 71.0
        assert records[0]["recommendation"] == "Buy"

    def test_retrieve_all(self):
        history_save("A.NS", "single_stock", 50, 50, 50, 50, "Hold")
        history_save("B.NS", "portfolio", 70, 70, 70, 70, "Buy")
        records = history_get()
        assert len(records) == 2

    def test_limit_works(self):
        for i in range(10):
            history_save(f"T{i}.NS", "single_stock", 50, 50, 50, 50, "Hold")
        records = history_get(limit=3)
        assert len(records) == 3

    def test_most_recent_first(self):
        history_save("FIRST.NS", "single_stock", 50, 50, 50, 50, "Hold")
        history_save("SECOND.NS", "single_stock", 60, 60, 60, 60, "Buy")
        records = history_get()
        assert records[0]["ticker"] == "SECOND.NS"

    def test_filter_by_ticker(self):
        history_save("A.NS", "single_stock", 50, 50, 50, 50, "Hold")
        history_save("B.NS", "single_stock", 60, 60, 60, 60, "Buy")
        records = history_get(ticker="A.NS")
        assert len(records) == 1
        assert records[0]["ticker"] == "A.NS"

    def test_nullable_scores(self):
        history_save("X.NS", "portfolio", None, None, None, None, None)
        records = history_get(ticker="X.NS")
        assert records[0]["fundamental_score"] is None


class TestMetrics:
    def test_save_and_retrieve(self):
        snapshot = {"counters": {"requests": 100}, "errors": {"api": 2}}
        metrics_save(snapshot)
        latest = metrics_latest()
        assert latest == snapshot

    def test_latest_returns_most_recent(self):
        metrics_save({"version": 1})
        metrics_save({"version": 2})
        assert metrics_latest()["version"] == 2

    def test_no_snapshots_returns_none(self):
        assert metrics_latest() is None
