from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data_sources.yahoo_finance import (
    YahooFinanceError,
    get_financials,
    get_historical,
    get_quote,
    normalize_ticker,
)

MOCK_INFO = {
    "shortName": "Reliance Industries",
    "longName": "Reliance Industries Limited",
    "sector": "Energy",
    "industry": "Oil & Gas Refining & Marketing",
    "marketCap": 17_000_000_000_000,
    "regularMarketPrice": 2450.50,
    "currentPrice": 2450.50,
    "previousClose": 2430.00,
    "currency": "INR",
    "exchange": "NSI",
    "trailingPE": 28.5,
    "forwardPE": 24.2,
    "pegRatio": 1.8,
    "priceToBook": 2.1,
    "debtToEquity": 45.0,
    "returnOnEquity": 0.12,
    "profitMargins": 0.08,
    "revenueGrowth": 0.14,
    "dividendYield": 0.003,
    "beta": 0.85,
    "fiftyTwoWeekHigh": 2800.0,
    "fiftyTwoWeekLow": 2100.0,
}

MOCK_HISTORY_DF = pd.DataFrame(
    {
        "Date": pd.date_range("2025-01-01", periods=5, freq="D"),
        "Open": [2400, 2420, 2440, 2430, 2450],
        "High": [2430, 2450, 2460, 2455, 2470],
        "Low": [2390, 2410, 2430, 2420, 2440],
        "Close": [2420, 2440, 2450, 2445, 2460],
        "Volume": [1_000_000, 1_100_000, 900_000, 1_200_000, 1_050_000],
    }
)


def _mock_ticker(info: dict | None = None, history_df: pd.DataFrame | None = None):
    """Create a mock yf.Ticker object."""
    mock = MagicMock()
    mock.info = info if info is not None else MOCK_INFO
    mock.history.return_value = history_df if history_df is not None else MOCK_HISTORY_DF
    return mock


class TestGetQuote:
    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_returns_expected_fields(self, mock_ticker_cls):
        mock_ticker_cls.return_value = _mock_ticker()
        result = get_quote("RELIANCE.NS")

        assert result["ticker"] == "RELIANCE.NS"
        assert result["name"] == "Reliance Industries"
        assert result["sector"] == "Energy"
        assert result["current_price"] == 2450.50
        assert result["market_cap"] == 17_000_000_000_000
        assert result["currency"] == "INR"

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_normalizes_ticker_to_uppercase(self, mock_ticker_cls):
        mock_ticker_cls.return_value = _mock_ticker()
        result = get_quote("  reliance.ns  ")
        assert result["ticker"] == "RELIANCE.NS"

    def test_empty_ticker_raises(self):
        with pytest.raises(YahooFinanceError, match="cannot be empty"):
            get_quote("")

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_no_data_raises(self, mock_ticker_cls):
        mock_ticker_cls.return_value = _mock_ticker(info={"regularMarketPrice": None})
        with pytest.raises(YahooFinanceError, match="No data returned"):
            get_quote("INVALID")

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_api_exception_wrapped(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = ConnectionError("network down")
        with pytest.raises(YahooFinanceError, match="Failed to fetch quote"):
            get_quote("RELIANCE.NS")


class TestGetHistorical:
    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_returns_dataframe_with_expected_columns(self, mock_ticker_cls):
        mock_ticker_cls.return_value = _mock_ticker()
        df = get_historical("RELIANCE.NS", period_days=30)

        assert isinstance(df, pd.DataFrame)
        assert "Date" in df.columns
        assert "Close" in df.columns
        assert "Volume" in df.columns
        assert len(df) == 5

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_empty_dataframe_raises(self, mock_ticker_cls):
        mock_ticker_cls.return_value = _mock_ticker(history_df=pd.DataFrame())
        with pytest.raises(YahooFinanceError, match="No historical data"):
            get_historical("INVALID")

    def test_empty_ticker_raises(self):
        with pytest.raises(YahooFinanceError, match="cannot be empty"):
            get_historical("  ")

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_custom_period_and_interval(self, mock_ticker_cls):
        mock = _mock_ticker()
        mock_ticker_cls.return_value = mock
        get_historical("RELIANCE.NS", period_days=60, interval="1wk")
        mock.history.assert_called_once()
        call_kwargs = mock.history.call_args
        assert call_kwargs.kwargs["interval"] == "1wk"

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_api_exception_wrapped(self, mock_ticker_cls):
        mock = _mock_ticker()
        mock.history.side_effect = RuntimeError("timeout")
        mock_ticker_cls.return_value = mock
        with pytest.raises(YahooFinanceError, match="Failed to fetch historical"):
            get_historical("RELIANCE.NS")


class TestGetFinancials:
    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_returns_expected_fields(self, mock_ticker_cls):
        mock_ticker_cls.return_value = _mock_ticker()
        result = get_financials("RELIANCE.NS")

        assert result["ticker"] == "RELIANCE.NS"
        assert result["pe_ratio"] == 28.5
        assert result["debt_to_equity"] == 45.0
        assert result["return_on_equity"] == 0.12
        assert result["revenue_growth"] == 0.14
        assert result["market_cap"] == 17_000_000_000_000
        assert result["beta"] == 0.85

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_missing_optional_fields_are_none(self, mock_ticker_cls):
        sparse_info = {"trailingPE": 20.0}
        mock_ticker_cls.return_value = _mock_ticker(info=sparse_info)
        result = get_financials("RELIANCE.NS")

        assert result["pe_ratio"] == 20.0
        assert result["forward_pe"] is None
        assert result["dividend_yield"] is None

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_no_info_raises(self, mock_ticker_cls):
        mock_ticker_cls.return_value = _mock_ticker(info={})
        with pytest.raises(YahooFinanceError, match="No financial data"):
            get_financials("INVALID")

    def test_empty_ticker_raises(self):
        with pytest.raises(YahooFinanceError, match="cannot be empty"):
            get_financials("")

    @patch("data_sources.yahoo_finance.yf.Ticker")
    def test_api_exception_wrapped(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = ValueError("bad request")
        with pytest.raises(YahooFinanceError, match="Failed to fetch financials"):
            get_financials("RELIANCE.NS")


class TestNormalizeTicker:
    def test_already_has_suffix(self):
        assert normalize_ticker("RELIANCE.NS") == "RELIANCE.NS"

    def test_appends_ns_when_no_suffix(self):
        assert normalize_ticker("TATAPOWER") == "TATAPOWER.NS"

    def test_removes_spaces(self):
        assert normalize_ticker("ADANI POWER") == "ADANIPOWER.NS"

    def test_strips_and_uppercases(self):
        assert normalize_ticker("  reliance.ns  ") == "RELIANCE.NS"

    def test_preserves_bo_suffix(self):
        assert normalize_ticker("INFY.BO") == "INFY.BO"

    def test_handles_ampersand(self):
        assert normalize_ticker("M&M") == "M&M.NS"

    def test_empty_raises(self):
        with pytest.raises(YahooFinanceError, match="cannot be empty"):
            normalize_ticker("")

    def test_whitespace_only_raises(self):
        with pytest.raises(YahooFinanceError, match="cannot be empty"):
            normalize_ticker("   ")
