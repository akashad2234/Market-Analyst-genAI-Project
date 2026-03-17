import pytest

from utils.cache import get_cached_analysis, set_cached_analysis
from utils.database import cache_clear, close_all


@pytest.fixture(autouse=True)
def _clean_db():
    import utils.database as db_mod

    db_mod._db_path = ":memory:"
    db_mod._connections.clear()
    yield
    close_all()
    db_mod._db_path = None


class TestAnalysisCache:
    def test_round_trip(self):
        assert get_cached_analysis("RELIANCE.NS") is None
        data = {
            "ticker": "RELIANCE.NS",
            "fundamental_score": 75.0,
            "technical_score": 60.0,
            "final_score": 68.0,
            "recommendation": "Buy",
        }
        set_cached_analysis("RELIANCE.NS", data)
        result = get_cached_analysis("RELIANCE.NS")
        assert result == data

    def test_case_insensitive(self):
        set_cached_analysis("reliance.ns", {"score": 50})
        assert get_cached_analysis("RELIANCE.NS") == {"score": 50}

    def test_different_tickers_independent(self):
        set_cached_analysis("A.NS", {"ticker": "A.NS"})
        set_cached_analysis("B.NS", {"ticker": "B.NS"})
        assert get_cached_analysis("A.NS")["ticker"] == "A.NS"
        assert get_cached_analysis("B.NS")["ticker"] == "B.NS"

    def test_overwrite_on_same_ticker(self):
        set_cached_analysis("TCS.NS", {"v": 1})
        set_cached_analysis("TCS.NS", {"v": 2})
        assert get_cached_analysis("TCS.NS")["v"] == 2

    def test_miss_returns_none(self):
        assert get_cached_analysis("NONEXISTENT.NS") is None

    def test_clear_removes_entries(self):
        set_cached_analysis("X.NS", {"x": 1})
        cache_clear("analysis")
        assert get_cached_analysis("X.NS") is None
