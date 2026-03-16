from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from agents.technical_agent import (
    _INDICATOR_WEIGHTS,
    TechnicalResult,
    _score_macd,
    _score_moving_averages,
    _score_rsi,
    _score_volume_trend,
    _verdict_from_score,
    analyze,
    compute_indicators,
    compute_technical_scores,
)

# ---------------------------------------------------------------------------
# Helper: build synthetic OHLCV DataFrames
# ---------------------------------------------------------------------------


def _make_uptrend_df(rows: int = 250) -> pd.DataFrame:
    """Simulate a stock in a sustained uptrend with increasing volume."""
    dates = pd.date_range("2025-01-01", periods=rows, freq="D")
    base = 100.0
    noise = np.random.RandomState(42).normal(0, 0.5, rows)
    close = np.array([base + i * 0.3 + noise[i] for i in range(rows)])
    volume_base = 1_000_000
    volume = np.array([volume_base + i * 5000 + int(noise[i] * 10000) for i in range(rows)])

    return pd.DataFrame({
        "Date": dates,
        "Open": close - 0.5,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": volume,
    })


def _make_downtrend_df(rows: int = 250) -> pd.DataFrame:
    """Simulate a stock in a sustained downtrend with declining volume."""
    dates = pd.date_range("2025-01-01", periods=rows, freq="D")
    base = 200.0
    noise = np.random.RandomState(99).normal(0, 0.5, rows)
    close = np.array([base - i * 0.3 + noise[i] for i in range(rows)])
    volume_base = 2_000_000
    volume = np.array([max(100_000, volume_base - i * 5000 + int(noise[i] * 10000)) for i in range(rows)])

    return pd.DataFrame({
        "Date": dates,
        "Open": close + 0.5,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": volume,
    })


def _make_flat_df(rows: int = 250) -> pd.DataFrame:
    """Simulate a sideways-moving stock."""
    dates = pd.date_range("2025-01-01", periods=rows, freq="D")
    noise = np.random.RandomState(7).normal(0, 1.0, rows)
    close = np.array([150.0 + noise[i] for i in range(rows)])
    volume = np.full(rows, 1_000_000)

    return pd.DataFrame({
        "Date": dates,
        "Open": close - 0.3,
        "High": close + 0.8,
        "Low": close - 0.8,
        "Close": close,
        "Volume": volume,
    })


def _make_short_df(rows: int = 20) -> pd.DataFrame:
    """Very short dataset to test edge cases with insufficient data."""
    dates = pd.date_range("2025-01-01", periods=rows, freq="D")
    close = np.linspace(100, 110, rows)
    volume = np.full(rows, 500_000)

    return pd.DataFrame({
        "Date": dates,
        "Open": close - 0.2,
        "High": close + 0.5,
        "Low": close - 0.5,
        "Close": close,
        "Volume": volume,
    })


# ===================== RSI scoring =====================


class TestScoreRsi:
    def test_none_returns_neutral(self):
        sc, interp = _score_rsi(None)
        assert sc == 50.0
        assert "Insufficient" in interp

    def test_strongly_overbought(self):
        sc, interp = _score_rsi(85.0)
        assert sc == 15.0
        assert "Strongly Overbought" in interp

    def test_overbought(self):
        sc, interp = _score_rsi(72.0)
        assert sc == 30.0

    def test_bullish(self):
        sc, interp = _score_rsi(62.0)
        assert sc == 85.0
        assert "Bullish" in interp

    def test_neutral(self):
        sc, interp = _score_rsi(50.0)
        assert sc == 60.0

    def test_bearish(self):
        sc, interp = _score_rsi(35.0)
        assert sc == 35.0

    def test_oversold(self):
        sc, interp = _score_rsi(25.0)
        assert sc == 20.0

    def test_strongly_oversold(self):
        sc, interp = _score_rsi(15.0)
        assert sc == 10.0


# ===================== MACD scoring =====================


class TestScoreMacd:
    def test_none_returns_neutral(self):
        sc, interp = _score_macd(None, None, None)
        assert sc == 50.0

    def test_bullish_crossover(self):
        sc, interp = _score_macd(1.5, 1.0, 0.5)
        assert sc == 85.0
        assert "Bullish" in interp

    def test_above_signal_fading(self):
        sc, interp = _score_macd(1.5, 1.0, -0.2)
        assert sc == 60.0
        assert "fading" in interp

    def test_bearish_crossover(self):
        sc, interp = _score_macd(-0.5, 0.3, -0.8)
        assert sc == 20.0
        assert "Bearish" in interp

    def test_below_signal_recovering(self):
        sc, interp = _score_macd(-0.5, 0.3, 0.2)
        assert sc == 40.0
        assert "recovering" in interp


# ===================== Moving average scoring =====================


class TestScoreMovingAverages:
    def test_none_price_returns_neutral(self):
        sc, interp = _score_moving_averages(None, 100.0, 95.0)
        assert sc == 50.0

    def test_golden_cross(self):
        sc, interp = _score_moving_averages(110.0, 105.0, 100.0)
        assert sc == 95.0
        assert "Golden Cross" in interp

    def test_above_both(self):
        # price above both MAs but no golden cross (ma_50 < ma_200)
        sc, interp = _score_moving_averages(110.0, 98.0, 105.0)
        assert sc == 80.0

    def test_above_50_below_200(self):
        sc, interp = _score_moving_averages(102.0, 100.0, 105.0)
        assert sc == 55.0

    def test_below_50_above_200(self):
        sc, interp = _score_moving_averages(102.0, 105.0, 100.0)
        assert sc == 45.0

    def test_death_cross(self):
        sc, interp = _score_moving_averages(90.0, 95.0, 100.0)
        assert sc == 10.0
        assert "Death Cross" in interp

    def test_below_both_no_cross(self):
        # below both MAs, but ma_50 == ma_200 (no death cross)
        sc, interp = _score_moving_averages(90.0, 100.0, 100.0)
        assert sc == 20.0

    def test_no_mas_available(self):
        sc, interp = _score_moving_averages(100.0, None, None)
        assert sc == 50.0


# ===================== Volume scoring =====================


class TestScoreVolumeTrend:
    def test_none_returns_neutral(self):
        sc, interp = _score_volume_trend(None)
        assert sc == 50.0

    def test_surging(self):
        sc, interp = _score_volume_trend(40.0)
        assert sc == 85.0

    def test_increasing(self):
        sc, interp = _score_volume_trend(15.0)
        assert sc == 70.0

    def test_stable(self):
        sc, interp = _score_volume_trend(0.0)
        assert sc == 50.0

    def test_declining(self):
        sc, interp = _score_volume_trend(-20.0)
        assert sc == 35.0

    def test_drying_up(self):
        sc, interp = _score_volume_trend(-40.0)
        assert sc == 20.0


# ===================== Verdict =====================


class TestVerdict:
    def test_bullish(self):
        assert _verdict_from_score(80.0) == "Bullish"

    def test_moderately_bullish(self):
        assert _verdict_from_score(65.0) == "Moderately Bullish"

    def test_neutral(self):
        assert _verdict_from_score(50.0) == "Neutral"

    def test_moderately_bearish(self):
        assert _verdict_from_score(30.0) == "Moderately Bearish"

    def test_bearish(self):
        assert _verdict_from_score(15.0) == "Bearish"

    def test_boundary_75(self):
        assert _verdict_from_score(75.0) == "Bullish"

    def test_boundary_60(self):
        assert _verdict_from_score(60.0) == "Moderately Bullish"

    def test_boundary_40(self):
        assert _verdict_from_score(40.0) == "Neutral"

    def test_boundary_25(self):
        assert _verdict_from_score(25.0) == "Moderately Bearish"


# ===================== compute_indicators =====================


class TestComputeIndicators:
    def test_uptrend_produces_valid_indicators(self):
        df = _make_uptrend_df()
        indicators = compute_indicators(df)

        assert "rsi" in indicators
        assert "macd" in indicators
        assert "ma_50" in indicators
        assert "ma_200" in indicators
        assert "volume_change_pct" in indicators
        assert indicators["rsi"] is not None
        assert 0 <= indicators["rsi"] <= 100

    def test_downtrend_produces_valid_indicators(self):
        df = _make_downtrend_df()
        indicators = compute_indicators(df)
        assert indicators["rsi"] is not None

    def test_short_data_still_works(self):
        df = _make_short_df(20)
        indicators = compute_indicators(df)
        assert indicators["current_price"] is not None
        assert indicators["ma_50"] is not None

    def test_flat_data_rsi_near_neutral(self):
        df = _make_flat_df()
        indicators = compute_indicators(df)
        assert indicators["rsi"] is not None
        assert 30 <= indicators["rsi"] <= 70


# ===================== compute_technical_scores =====================


class TestComputeTechnicalScores:
    def test_bullish_indicators_high_score(self):
        indicators = {
            "rsi": 60.0,
            "macd": 1.5,
            "macd_signal": 1.0,
            "macd_histogram": 0.5,
            "current_price": 110.0,
            "ma_50": 105.0,
            "ma_200": 100.0,
            "volume_change_pct": 20.0,
        }
        scores, interps, total = compute_technical_scores(indicators)
        assert total >= 70.0
        assert len(scores) == 4
        assert len(interps) == 4

    def test_bearish_indicators_low_score(self):
        indicators = {
            "rsi": 25.0,
            "macd": -1.0,
            "macd_signal": 0.5,
            "macd_histogram": -1.5,
            "current_price": 85.0,
            "ma_50": 95.0,
            "ma_200": 100.0,
            "volume_change_pct": -35.0,
        }
        scores, interps, total = compute_technical_scores(indicators)
        assert total <= 30.0

    def test_all_none_returns_neutral(self):
        indicators = {
            "rsi": None,
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "current_price": None,
            "ma_50": None,
            "ma_200": None,
            "volume_change_pct": None,
        }
        scores, interps, total = compute_technical_scores(indicators)
        assert total == pytest.approx(50.0)

    def test_weights_sum_to_one(self):
        assert sum(_INDICATOR_WEIGHTS.values()) == pytest.approx(1.0)


# ===================== analyze() integration =====================


class TestAnalyze:
    @patch("agents.technical_agent.get_historical")
    def test_uptrend_returns_bullish(self, mock_hist):
        mock_hist.return_value = _make_uptrend_df()
        result = analyze("RELIANCE.NS")

        assert isinstance(result, TechnicalResult)
        assert result.ticker == "RELIANCE.NS"
        assert 0 <= result.score <= 100
        assert result.verdict in ("Bullish", "Moderately Bullish", "Neutral")
        assert "Technical Analysis" in result.explanation

    @patch("agents.technical_agent.get_historical")
    def test_downtrend_returns_bearish(self, mock_hist):
        mock_hist.return_value = _make_downtrend_df()
        result = analyze("WEAK.NS")

        assert 0 <= result.score <= 100
        assert result.verdict in ("Bearish", "Moderately Bearish", "Neutral")

    @patch("agents.technical_agent.get_historical")
    def test_ticker_normalized_to_uppercase(self, mock_hist):
        mock_hist.return_value = _make_flat_df()
        result = analyze("  reliance.ns  ")
        assert result.ticker == "RELIANCE.NS"

    @patch("agents.technical_agent.get_historical")
    def test_explanation_contains_key_sections(self, mock_hist):
        mock_hist.return_value = _make_uptrend_df()
        result = analyze("RELIANCE.NS")

        assert "RSI" in result.explanation
        assert "MACD" in result.explanation
        assert "Moving Averages" in result.explanation
        assert "Volume Trend" in result.explanation
        assert "Verdict" in result.explanation
        assert "/100" in result.explanation

    @patch("agents.technical_agent.get_historical")
    def test_indicator_scores_present(self, mock_hist):
        mock_hist.return_value = _make_uptrend_df()
        result = analyze("RELIANCE.NS")

        expected_keys = {"rsi", "macd", "moving_averages", "volume_trend"}
        assert set(result.indicator_scores.keys()) == expected_keys
        assert all(0 <= v <= 100 for v in result.indicator_scores.values())

    @patch("agents.technical_agent.get_historical")
    def test_custom_period_and_interval_forwarded(self, mock_hist):
        mock_hist.return_value = _make_flat_df(100)
        analyze("RELIANCE.NS", period_days=90, interval="1wk")
        mock_hist.assert_called_once_with("RELIANCE.NS", period_days=90, interval="1wk")

    @patch("agents.technical_agent.get_historical")
    def test_data_source_error_propagates(self, mock_hist):
        from data_sources.yahoo_finance import YahooFinanceError

        mock_hist.side_effect = YahooFinanceError("no data")
        with pytest.raises(YahooFinanceError):
            analyze("INVALID")

    @patch("agents.technical_agent.get_historical")
    def test_short_data_does_not_crash(self, mock_hist):
        mock_hist.return_value = _make_short_df(20)
        result = analyze("SHORT.NS")
        assert isinstance(result, TechnicalResult)
        assert 0 <= result.score <= 100


class TestLLMNarrative:
    @patch("agents.technical_agent.llm_generate", return_value=None)
    @patch("agents.technical_agent.get_historical")
    def test_no_narrative_when_llm_disabled(self, mock_hist, mock_llm):
        mock_hist.return_value = _make_uptrend_df()
        result = analyze("RELIANCE.NS")
        assert "AI Narrative" not in result.explanation
        assert "RSI" in result.explanation

    @patch(
        "agents.technical_agent.llm_generate",
        return_value="Momentum is bullish with strong RSI support.",
    )
    @patch("agents.technical_agent.get_historical")
    def test_narrative_appended_when_llm_returns_text(self, mock_hist, mock_llm):
        mock_hist.return_value = _make_uptrend_df()
        result = analyze("RELIANCE.NS")
        assert "AI Narrative:" in result.explanation
        assert "Momentum is bullish" in result.explanation
        assert "RSI" in result.explanation

    @patch(
        "agents.technical_agent.llm_generate",
        return_value="Technical narrative.",
    )
    @patch("agents.technical_agent.get_historical")
    def test_llm_prompt_contains_ticker(self, mock_hist, mock_llm):
        mock_hist.return_value = _make_uptrend_df()
        analyze("RELIANCE.NS")
        prompt_arg = mock_llm.call_args[0][0]
        assert "RELIANCE.NS" in prompt_arg
