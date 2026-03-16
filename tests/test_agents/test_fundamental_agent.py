from unittest.mock import patch

import pytest

from agents.fundamental_agent import (
    FundamentalResult,
    _score_debt_to_equity,
    _score_pe_ratio,
    _score_peg_ratio,
    _score_profit_margin,
    _score_return_on_equity,
    _score_revenue_growth,
    _verdict_from_score,
    analyze,
    compute_fundamental_scores,
)

# --- Fixture data ---

STRONG_FINANCIALS = {
    "ticker": "RELIANCE.NS",
    "pe_ratio": 12.0,
    "forward_pe": 10.5,
    "peg_ratio": 0.8,
    "price_to_book": 2.1,
    "debt_to_equity": 30.0,
    "return_on_equity": 0.22,
    "profit_margin": 0.18,
    "revenue_growth": 0.20,
    "market_cap": 17_000_000_000_000,
    "dividend_yield": 0.003,
    "beta": 0.85,
    "fifty_two_week_high": 2800.0,
    "fifty_two_week_low": 2100.0,
}

WEAK_FINANCIALS = {
    "ticker": "WEAK.NS",
    "pe_ratio": 55.0,
    "forward_pe": 50.0,
    "peg_ratio": 3.0,
    "price_to_book": 8.0,
    "debt_to_equity": 250.0,
    "return_on_equity": 0.03,
    "profit_margin": 0.02,
    "revenue_growth": -0.15,
    "market_cap": 500_000_000,
    "dividend_yield": None,
    "beta": 1.8,
    "fifty_two_week_high": 100.0,
    "fifty_two_week_low": 30.0,
}

ALL_NONE_FINANCIALS = {
    "ticker": "SPARSE.NS",
    "pe_ratio": None,
    "forward_pe": None,
    "peg_ratio": None,
    "price_to_book": None,
    "debt_to_equity": None,
    "return_on_equity": None,
    "profit_margin": None,
    "revenue_growth": None,
    "market_cap": None,
    "dividend_yield": None,
    "beta": None,
    "fifty_two_week_high": None,
    "fifty_two_week_low": None,
}


# ===================== Individual scorer tests =====================


class TestScorePeRatio:
    def test_none_returns_neutral(self):
        assert _score_pe_ratio(None) == 50.0

    def test_negative_pe(self):
        assert _score_pe_ratio(-5.0) == 10.0

    def test_low_pe_high_score(self):
        assert _score_pe_ratio(8.0) == 95.0

    def test_moderate_pe(self):
        assert _score_pe_ratio(18.0) == 70.0

    def test_high_pe_low_score(self):
        assert _score_pe_ratio(60.0) == 15.0

    def test_boundary_at_10(self):
        assert _score_pe_ratio(10.0) == 95.0

    def test_boundary_at_15(self):
        assert _score_pe_ratio(15.0) == 85.0


class TestScoreDebtToEquity:
    def test_none_returns_neutral(self):
        assert _score_debt_to_equity(None) == 50.0

    def test_low_de_percentage(self):
        # yfinance returns 30 meaning 30% = 0.30 ratio, which is <= 0.3
        assert _score_debt_to_equity(30.0) == 95.0

    def test_high_de_percentage(self):
        # 250% = 2.50 ratio, which is <= 2.5
        assert _score_debt_to_equity(250.0) == 25.0

    def test_extreme_de_percentage(self):
        # 300% = 3.00 ratio, which is > 2.5
        assert _score_debt_to_equity(300.0) == 10.0

    def test_very_low_de_as_ratio(self):
        assert _score_debt_to_equity(0.2) == 95.0

    def test_moderate_de(self):
        assert _score_debt_to_equity(80.0) == 65.0


class TestScoreReturnOnEquity:
    def test_none_returns_neutral(self):
        assert _score_return_on_equity(None) == 50.0

    def test_negative_roe(self):
        assert _score_return_on_equity(-0.05) == 10.0

    def test_excellent_roe(self):
        assert _score_return_on_equity(0.30) == 95.0

    def test_moderate_roe(self):
        assert _score_return_on_equity(0.12) == 65.0

    def test_low_roe(self):
        assert _score_return_on_equity(0.03) == 30.0


class TestScoreProfitMargin:
    def test_none_returns_neutral(self):
        assert _score_profit_margin(None) == 50.0

    def test_negative_margin(self):
        assert _score_profit_margin(-0.05) == 10.0

    def test_high_margin(self):
        assert _score_profit_margin(0.30) == 95.0

    def test_moderate_margin(self):
        assert _score_profit_margin(0.10) == 65.0

    def test_low_margin(self):
        assert _score_profit_margin(0.02) == 25.0


class TestScoreRevenueGrowth:
    def test_none_returns_neutral(self):
        assert _score_revenue_growth(None) == 50.0

    def test_severe_decline(self):
        assert _score_revenue_growth(-0.15) == 10.0

    def test_mild_decline(self):
        assert _score_revenue_growth(-0.05) == 30.0

    def test_strong_growth(self):
        assert _score_revenue_growth(0.30) == 95.0

    def test_moderate_growth(self):
        assert _score_revenue_growth(0.14) == 65.0

    def test_low_growth(self):
        assert _score_revenue_growth(0.02) == 35.0


class TestScorePegRatio:
    def test_none_returns_neutral(self):
        assert _score_peg_ratio(None) == 50.0

    def test_negative_peg(self):
        assert _score_peg_ratio(-0.5) == 10.0

    def test_ideal_peg(self):
        assert _score_peg_ratio(0.9) == 85.0

    def test_overvalued_peg(self):
        assert _score_peg_ratio(3.0) == 20.0

    def test_undervalued_peg(self):
        assert _score_peg_ratio(0.4) == 90.0


# ===================== Verdict tests =====================


class TestVerdict:
    def test_strong(self):
        assert _verdict_from_score(80.0) == "Strong"

    def test_moderate(self):
        assert _verdict_from_score(60.0) == "Moderate"

    def test_weak(self):
        assert _verdict_from_score(40.0) == "Weak"

    def test_very_weak(self):
        assert _verdict_from_score(20.0) == "Very Weak"

    def test_boundary_75(self):
        assert _verdict_from_score(75.0) == "Strong"

    def test_boundary_55(self):
        assert _verdict_from_score(55.0) == "Moderate"

    def test_boundary_35(self):
        assert _verdict_from_score(35.0) == "Weak"


# ===================== compute_fundamental_scores tests =====================


class TestComputeFundamentalScores:
    def test_strong_financials_high_score(self):
        metric_scores, total = compute_fundamental_scores(STRONG_FINANCIALS)
        assert total >= 70.0
        assert "pe_ratio" in metric_scores
        assert "debt_to_equity" in metric_scores
        assert len(metric_scores) == 6

    def test_weak_financials_low_score(self):
        metric_scores, total = compute_fundamental_scores(WEAK_FINANCIALS)
        assert total <= 30.0

    def test_all_none_returns_neutral(self):
        metric_scores, total = compute_fundamental_scores(ALL_NONE_FINANCIALS)
        assert total == pytest.approx(50.0)
        assert all(v == 50.0 for v in metric_scores.values())

    def test_score_between_0_and_100(self):
        _, total = compute_fundamental_scores(STRONG_FINANCIALS)
        assert 0 <= total <= 100
        _, total = compute_fundamental_scores(WEAK_FINANCIALS)
        assert 0 <= total <= 100

    def test_weights_sum_to_one(self):
        from agents.fundamental_agent import _METRIC_WEIGHTS

        assert sum(_METRIC_WEIGHTS.values()) == pytest.approx(1.0)


# ===================== analyze() integration tests =====================


class TestAnalyze:
    @patch("agents.fundamental_agent.get_financials")
    def test_strong_stock_returns_strong_verdict(self, mock_get_fin):
        mock_get_fin.return_value = STRONG_FINANCIALS
        result = analyze("RELIANCE.NS")

        assert isinstance(result, FundamentalResult)
        assert result.ticker == "RELIANCE.NS"
        assert result.score >= 70.0
        assert result.verdict == "Strong"
        assert "Fundamental Analysis" in result.explanation
        assert result.metrics == STRONG_FINANCIALS

    @patch("agents.fundamental_agent.get_financials")
    def test_weak_stock_returns_weak_verdict(self, mock_get_fin):
        mock_get_fin.return_value = WEAK_FINANCIALS
        result = analyze("WEAK.NS")

        assert result.score <= 30.0
        assert result.verdict in ("Weak", "Very Weak")

    @patch("agents.fundamental_agent.get_financials")
    def test_sparse_data_returns_neutral(self, mock_get_fin):
        mock_get_fin.return_value = ALL_NONE_FINANCIALS
        result = analyze("SPARSE.NS")

        assert result.score == pytest.approx(50.0)
        assert result.verdict == "Weak"

    @patch("agents.fundamental_agent.get_financials")
    def test_ticker_normalized_to_uppercase(self, mock_get_fin):
        mock_get_fin.return_value = STRONG_FINANCIALS
        result = analyze("  reliance.ns  ")
        assert result.ticker == "RELIANCE.NS"

    @patch("agents.fundamental_agent.get_financials")
    def test_explanation_contains_key_info(self, mock_get_fin):
        mock_get_fin.return_value = STRONG_FINANCIALS
        result = analyze("RELIANCE.NS")

        assert "PE Ratio" in result.explanation
        assert "Debt/Equity" in result.explanation
        assert "ROE" in result.explanation
        assert "Verdict" in result.explanation
        assert "/100" in result.explanation

    @patch("agents.fundamental_agent.get_financials")
    def test_metric_scores_all_present(self, mock_get_fin):
        mock_get_fin.return_value = STRONG_FINANCIALS
        result = analyze("RELIANCE.NS")

        expected_keys = {
            "pe_ratio", "debt_to_equity", "return_on_equity",
            "profit_margin", "revenue_growth", "peg_ratio",
        }
        assert set(result.metric_scores.keys()) == expected_keys
        assert all(0 <= v <= 100 for v in result.metric_scores.values())

    @patch("agents.fundamental_agent.get_financials")
    def test_data_source_error_propagates(self, mock_get_fin):
        from data_sources.yahoo_finance import YahooFinanceError

        mock_get_fin.side_effect = YahooFinanceError("invalid ticker")
        with pytest.raises(YahooFinanceError):
            analyze("INVALID")


class TestLLMNarrative:
    @patch("agents.fundamental_agent.llm_generate", return_value=None)
    @patch("agents.fundamental_agent.get_financials")
    def test_no_narrative_when_llm_disabled(self, mock_fin, mock_llm):
        mock_fin.return_value = STRONG_FINANCIALS
        result = analyze("RELIANCE.NS")
        assert "AI Narrative" not in result.explanation
        assert "PE Ratio" in result.explanation

    @patch(
        "agents.fundamental_agent.llm_generate",
        return_value="The stock shows strong fundamentals.",
    )
    @patch("agents.fundamental_agent.get_financials")
    def test_narrative_appended_when_llm_returns_text(self, mock_fin, mock_llm):
        mock_fin.return_value = STRONG_FINANCIALS
        result = analyze("RELIANCE.NS")
        assert "AI Narrative:" in result.explanation
        assert "The stock shows strong fundamentals." in result.explanation
        assert "PE Ratio" in result.explanation

    @patch(
        "agents.fundamental_agent.llm_generate",
        return_value="Generated narrative.",
    )
    @patch("agents.fundamental_agent.get_financials")
    def test_llm_prompt_contains_ticker(self, mock_fin, mock_llm):
        mock_fin.return_value = STRONG_FINANCIALS
        analyze("RELIANCE.NS")
        prompt_arg = mock_llm.call_args[0][0]
        assert "RELIANCE.NS" in prompt_arg
