import time
from unittest.mock import MagicMock, patch

import pytest

from data_sources.duckduckgo_search import (
    DuckDuckGoSearchError,
    _build_query,
    _normalize_result,
    clear_cache,
    search_news,
)

MOCK_RAW_RESULTS = [
    {
        "title": "Tata Motors sales jump 18% in Q3",
        "body": "Tata Motors reported a strong 18% increase in sales during Q3 FY26.",
        "href": "https://example.com/tata-motors-q3",
        "date": "2026-03-15",
        "source": "Economic Times",
    },
    {
        "title": "Tata Motors launches new EV model",
        "body": "The company announced the launch of a new electric vehicle.",
        "url": "https://example.com/tata-ev",
        "date": "2026-03-14",
        "source": "Livemint",
    },
    {
        "title": "Auto sector outlook positive",
        "body": "Analysts expect strong growth in the Indian auto sector.",
        "href": "https://example.com/auto-outlook",
        "date": "2026-03-13",
        "source": "Moneycontrol",
    },
]


class TestBuildQuery:
    def test_ticker_only(self):
        assert _build_query("TATAMOTORS.NS") == "TATAMOTORS.NS stock news"

    def test_with_company_name(self):
        assert _build_query("TATAMOTORS.NS", "Tata Motors") == "Tata Motors TATAMOTORS.NS stock news"


class TestNormalizeResult:
    def test_standard_result(self):
        raw = MOCK_RAW_RESULTS[0]
        normalized = _normalize_result(raw)
        assert normalized["title"] == "Tata Motors sales jump 18% in Q3"
        assert normalized["snippet"] == raw["body"]
        assert normalized["url"] == "https://example.com/tata-motors-q3"
        assert normalized["date"] == "2026-03-15"
        assert normalized["source"] == "Economic Times"

    def test_url_fallback_from_href(self):
        raw = {"title": "Test", "body": "Body", "url": "https://fallback.com"}
        normalized = _normalize_result(raw)
        assert normalized["url"] == "https://fallback.com"

    def test_missing_fields_default_to_empty(self):
        normalized = _normalize_result({})
        assert normalized["title"] == ""
        assert normalized["snippet"] == ""
        assert normalized["url"] == ""
        assert normalized["date"] == ""
        assert normalized["source"] == ""


class TestSearchNews:
    def setup_method(self):
        clear_cache()

    @patch("data_sources.duckduckgo_search._rate_limit")
    @patch("data_sources.duckduckgo_search.DDGS")
    def test_returns_normalized_results(self, mock_ddgs_cls, mock_rate_limit):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.return_value = MOCK_RAW_RESULTS
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_cls.return_value = mock_ddgs_instance

        results = search_news("TATAMOTORS.NS", company_name="Tata Motors", use_cache=False)

        assert len(results) == 3
        assert results[0]["title"] == "Tata Motors sales jump 18% in Q3"
        assert results[1]["url"] == "https://example.com/tata-ev"
        assert all("title" in r and "snippet" in r and "url" in r for r in results)

    @patch("data_sources.duckduckgo_search._rate_limit")
    @patch("data_sources.duckduckgo_search.DDGS")
    def test_empty_results_returns_empty_list(self, mock_ddgs_cls, mock_rate_limit):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.return_value = []
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_cls.return_value = mock_ddgs_instance

        results = search_news("NONEXISTENT.NS", use_cache=False)
        assert results == []

    def test_empty_ticker_raises(self):
        with pytest.raises(DuckDuckGoSearchError, match="cannot be empty"):
            search_news("")

    @patch("data_sources.duckduckgo_search._rate_limit")
    @patch("data_sources.duckduckgo_search.DDGS")
    def test_api_exception_wrapped(self, mock_ddgs_cls, mock_rate_limit):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.side_effect = RuntimeError("rate limited")
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_cls.return_value = mock_ddgs_instance

        with pytest.raises(DuckDuckGoSearchError, match="Search failed"):
            search_news("TATAMOTORS.NS", use_cache=False)

    @patch("data_sources.duckduckgo_search._rate_limit")
    @patch("data_sources.duckduckgo_search.DDGS")
    def test_max_results_forwarded(self, mock_ddgs_cls, mock_rate_limit):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.return_value = MOCK_RAW_RESULTS[:1]
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_cls.return_value = mock_ddgs_instance

        search_news("TATAMOTORS.NS", max_results=5, use_cache=False)
        mock_ddgs_instance.news.assert_called_once()
        call_kwargs = mock_ddgs_instance.news.call_args
        assert call_kwargs.kwargs.get("max_results") == 5 or call_kwargs[1].get("max_results") == 5

    @patch("data_sources.duckduckgo_search._rate_limit")
    @patch("data_sources.duckduckgo_search.DDGS")
    def test_cache_returns_same_object(self, mock_ddgs_cls, mock_rate_limit):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.return_value = MOCK_RAW_RESULTS
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_cls.return_value = mock_ddgs_instance

        r1 = search_news("TATAMOTORS.NS", use_cache=True)
        r2 = search_news("TATAMOTORS.NS", use_cache=True)
        assert r1 == r2
        assert mock_ddgs_instance.news.call_count <= 1

    def test_clear_cache_works(self):
        clear_cache()


class TestRateLimit:
    @patch("data_sources.duckduckgo_search.DDGS")
    def test_rate_limiting_enforces_delay(self, mock_ddgs_cls):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.return_value = []
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_cls.return_value = mock_ddgs_instance

        import data_sources.duckduckgo_search as mod

        mod._last_request_time = time.time()

        start = time.time()
        search_news("TEST.NS", use_cache=False)
        elapsed = time.time() - start

        assert elapsed >= 1.0
