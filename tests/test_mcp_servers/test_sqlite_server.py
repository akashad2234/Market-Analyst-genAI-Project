"""Tests for the MCP server tool functions (called directly, no MCP transport)."""

import pytest

from mcp_servers.sqlite_server import (
    clear_cache,
    describe_table,
    get_analysis_history,
    get_cache_stats,
    get_cached_analysis,
    get_latest_metrics,
    list_tables,
    purge_expired,
    run_read_query,
    save_analysis,
    save_metrics_snapshot,
    store_cached_analysis,
)
from utils.database import close_all


@pytest.fixture(autouse=True)
def _clean_db():
    import utils.database as db_mod

    db_mod._db_path = ":memory:"
    db_mod._connections.clear()
    yield
    close_all()
    db_mod._db_path = None


class TestCacheTools:
    def test_store_and_get(self):
        store_cached_analysis("TCS.NS", {"final_score": 72.0}, 3600)
        result = get_cached_analysis("TCS.NS")
        assert result == {"final_score": 72.0}

    def test_get_missing_returns_none(self):
        assert get_cached_analysis("NOPE.NS") is None

    def test_clear_returns_message(self):
        store_cached_analysis("A.NS", {"score": 50}, 300)
        msg = clear_cache("analysis")
        assert "1" in msg
        assert get_cached_analysis("A.NS") is None

    def test_stats(self):
        store_cached_analysis("A.NS", {}, 3600)
        store_cached_analysis("B.NS", {}, 3600)
        stats = get_cache_stats()
        assert stats["total"] == 2

    def test_purge_returns_message(self):
        msg = purge_expired()
        assert "Purged" in msg


class TestHistoryTools:
    def test_save_and_get(self):
        msg = save_analysis(
            ticker="INFY.NS",
            query_type="single_stock",
            fundamental_score=70.0,
            final_score=68.0,
            recommendation="Buy",
        )
        assert "INFY.NS" in msg

        records = get_analysis_history(ticker="INFY.NS")
        assert len(records) == 1
        assert records[0]["recommendation"] == "Buy"

    def test_limit_respected(self):
        for i in range(5):
            save_analysis(f"T{i}.NS", "single_stock")
        records = get_analysis_history(limit=2)
        assert len(records) == 2

    def test_limit_capped_at_100(self):
        records = get_analysis_history(limit=999)
        assert isinstance(records, list)


class TestMetricsTools:
    def test_save_and_get(self):
        save_metrics_snapshot({"requests": 42})
        result = get_latest_metrics()
        assert result == {"requests": 42}

    def test_no_snapshots(self):
        assert get_latest_metrics() is None


class TestDbInfoTools:
    def test_list_tables(self):
        tables = list_tables()
        assert "analysis_cache" in tables
        assert "analysis_history" in tables
        assert "metrics_snapshot" in tables

    def test_describe_table(self):
        cols = describe_table("analysis_cache")
        col_names = {c["name"] for c in cols}
        assert "cache_key" in col_names
        assert "data_json" in col_names
        assert "ttl_seconds" in col_names

    def test_run_select_query(self):
        store_cached_analysis("A.NS", {}, 3600)
        rows = run_read_query("SELECT COUNT(*) as cnt FROM analysis_cache")
        assert rows[0]["cnt"] == 1

    def test_reject_non_select(self):
        result = run_read_query("DELETE FROM analysis_cache")
        assert result[0]["error"] == "Only SELECT queries are allowed"

    def test_invalid_sql_returns_error(self):
        result = run_read_query("SELECT * FROM nonexistent_table")
        assert "error" in result[0]
