from unittest.mock import patch

import pytest

from agents.fundamental_agent import FundamentalResult
from agents.master_agent import (
    AnalysisRequest,
    AnalysisResponse,
    QueryType,
    StockAnalysis,
    _from_cache,
    _generate_narrative,
    _to_cacheable,
    analyze_query,
    parse_intent,
    run_analysis,
)
from agents.sentiment_agent import SentimentResult
from agents.technical_agent import TechnicalResult
from langgraph.graph_builder import AnalysisState
from utils.database import close_all


@pytest.fixture(autouse=True)
def _clean_db():
    """Ensure DB cache doesn't interfere between tests."""
    import utils.database as db_mod

    db_mod._db_path = ":memory:"
    db_mod._connections.clear()
    yield
    close_all()
    db_mod._db_path = None


def _mock_state(
    ticker: str,
    fund_score: float = 75.0,
    tech_score: float = 70.0,
    sent_score: float = 65.0,
) -> AnalysisState:
    state = AnalysisState(ticker=ticker)
    state.fundamental = FundamentalResult(ticker=ticker, score=fund_score, verdict="Strong")
    state.technical = TechnicalResult(ticker=ticker, score=tech_score, verdict="Moderately Bullish")
    state.sentiment = SentimentResult(ticker=ticker, score=sent_score, verdict="Moderately Positive")
    state.final_score = fund_score * 0.4 + tech_score * 0.4 + sent_score * 0.2
    state.recommendation = "Buy"
    return state


class TestParseIntent:
    def test_single_ticker(self):
        req = parse_intent("RELIANCE.NS")
        assert req.query_type == QueryType.SINGLE_STOCK
        assert req.tickers == ["RELIANCE.NS"]

    def test_single_ticker_with_whitespace(self):
        req = parse_intent("  reliance.ns  ")
        assert req.tickers == ["RELIANCE.NS"]

    def test_portfolio_comma_separated(self):
        req = parse_intent("TATAMOTORS.NS, INFY.NS, M&M.NS")
        assert req.query_type == QueryType.PORTFOLIO
        assert len(req.tickers) == 3
        assert "TATAMOTORS.NS" in req.tickers
        assert "M&M.NS" in req.tickers

    def test_comparison_vs(self):
        req = parse_intent("TATAMOTORS.NS vs M&M.NS")
        assert req.query_type == QueryType.COMPARISON
        assert len(req.tickers) == 2

    def test_comparison_vs_dot(self):
        req = parse_intent("TATAMOTORS.NS vs. M&M.NS")
        assert req.query_type == QueryType.COMPARISON
        assert len(req.tickers) == 2

    def test_comparison_case_insensitive(self):
        req = parse_intent("TATAMOTORS.NS VS M&M.NS")
        assert req.query_type == QueryType.COMPARISON

    def test_invalid_ticker_raises(self):
        with pytest.raises(ValueError, match="Invalid ticker"):
            parse_intent("$INVALID!")

    def test_spaces_normalized_to_valid_ticker(self):
        req = parse_intent("ADANI POWER")
        assert req.query_type == QueryType.SINGLE_STOCK
        assert req.tickers == ["ADANIPOWER.NS"]

    def test_single_comma_item_is_single_stock(self):
        req = parse_intent("RELIANCE.NS,")
        assert req.query_type == QueryType.SINGLE_STOCK
        assert req.tickers == ["RELIANCE.NS"]

    def test_raw_query_preserved(self):
        req = parse_intent("RELIANCE.NS")
        assert req.raw_query == "RELIANCE.NS"


class TestRunAnalysis:
    @patch("agents.master_agent.run_analysis_graph")
    def test_single_stock(self, mock_graph):
        mock_graph.return_value = _mock_state("RELIANCE.NS")

        req = AnalysisRequest(
            query_type=QueryType.SINGLE_STOCK,
            tickers=["RELIANCE.NS"],
        )
        resp = run_analysis(req)

        assert isinstance(resp, AnalysisResponse)
        assert resp.query_type == QueryType.SINGLE_STOCK
        assert len(resp.stocks) == 1
        assert resp.stocks[0].ticker == "RELIANCE.NS"
        assert resp.stocks[0].recommendation == "Buy"
        assert "RELIANCE.NS" in resp.summary

    @patch("agents.master_agent.run_analysis_graph")
    def test_portfolio(self, mock_graph):
        mock_graph.side_effect = [
            _mock_state("TATAMOTORS.NS", 80, 75, 70),
            _mock_state("INFY.NS", 70, 60, 50),
            _mock_state("M&M.NS", 60, 55, 45),
        ]

        req = AnalysisRequest(
            query_type=QueryType.PORTFOLIO,
            tickers=["TATAMOTORS.NS", "INFY.NS", "M&M.NS"],
        )
        resp = run_analysis(req)

        assert len(resp.stocks) == 3
        assert "Portfolio Summary" in resp.summary
        assert "Best Performing" in resp.summary
        assert "Most Risky" in resp.summary

    @patch("agents.master_agent.run_analysis_graph")
    def test_comparison(self, mock_graph):
        mock_graph.side_effect = [
            _mock_state("TATAMOTORS.NS", 80, 75, 70),
            _mock_state("M&M.NS", 60, 55, 50),
        ]

        req = AnalysisRequest(
            query_type=QueryType.COMPARISON,
            tickers=["TATAMOTORS.NS", "M&M.NS"],
        )
        resp = run_analysis(req)

        assert len(resp.stocks) == 2
        assert "Comparison Results" in resp.summary
        assert "TATAMOTORS.NS" in resp.summary

    @patch("agents.master_agent.run_analysis_graph")
    def test_stock_analysis_has_all_fields(self, mock_graph):
        mock_graph.return_value = _mock_state("RELIANCE.NS")

        req = AnalysisRequest(query_type=QueryType.SINGLE_STOCK, tickers=["RELIANCE.NS"])
        resp = run_analysis(req)

        sa = resp.stocks[0]
        assert isinstance(sa, StockAnalysis)
        assert sa.fundamental_score is not None
        assert sa.technical_score is not None
        assert sa.sentiment_score is not None
        assert sa.final_score is not None
        assert sa.recommendation != ""
        assert sa.explanation != ""


class TestAnalyzeQuery:
    @patch("agents.master_agent.run_analysis_graph")
    def test_end_to_end_single(self, mock_graph):
        mock_graph.return_value = _mock_state("RELIANCE.NS")

        resp = analyze_query("RELIANCE.NS")
        assert resp.query_type == QueryType.SINGLE_STOCK
        assert len(resp.stocks) == 1
        assert resp.stocks[0].ticker == "RELIANCE.NS"

    @patch("agents.master_agent.run_analysis_graph")
    def test_end_to_end_comparison(self, mock_graph):
        mock_graph.side_effect = [
            _mock_state("TATAMOTORS.NS"),
            _mock_state("M&M.NS"),
        ]

        resp = analyze_query("TATAMOTORS.NS vs M&M.NS")
        assert resp.query_type == QueryType.COMPARISON
        assert len(resp.stocks) == 2

    @patch("agents.master_agent.run_analysis_graph")
    def test_end_to_end_portfolio(self, mock_graph):
        mock_graph.side_effect = [
            _mock_state("A.NS"),
            _mock_state("B.NS"),
            _mock_state("C.NS"),
        ]

        resp = analyze_query("A.NS, B.NS, C.NS")
        assert resp.query_type == QueryType.PORTFOLIO
        assert len(resp.stocks) == 3


class TestCacheHelpers:
    def test_to_cacheable_extracts_scores(self):
        sa = StockAnalysis(
            ticker="RELIANCE.NS",
            fundamental_score=75.0,
            fundamental_verdict="Strong",
            technical_score=60.0,
            technical_verdict="Moderate",
            sentiment_score=80.0,
            sentiment_verdict="Positive",
            final_score=70.0,
            recommendation="Buy",
            explanation="Full LLM narrative here",
            errors={"sentiment": "timeout"},
        )
        cached = _to_cacheable(sa)
        assert cached["ticker"] == "RELIANCE.NS"
        assert cached["fundamental_score"] == 75.0
        assert cached["recommendation"] == "Buy"
        assert "explanation" not in cached

    def test_from_cache_rebuilds_stock_analysis(self):
        data = {
            "ticker": "TCS.NS",
            "fundamental_score": 70.0,
            "fundamental_verdict": "Strong",
            "technical_score": 55.0,
            "technical_verdict": "Neutral",
            "sentiment_score": 65.0,
            "sentiment_verdict": "Moderate",
            "final_score": 63.0,
            "recommendation": "Buy",
            "errors": {},
        }
        sa = _from_cache(data)
        assert sa.ticker == "TCS.NS"
        assert sa.fundamental_score == 70.0
        assert sa.final_score == 63.0
        assert sa.explanation == ""

    def test_round_trip_preserves_data(self):
        original = StockAnalysis(
            ticker="INFY.NS",
            fundamental_score=80.0,
            fundamental_verdict="Very Strong",
            technical_score=45.0,
            technical_verdict="Bearish",
            sentiment_score=60.0,
            sentiment_verdict="Neutral",
            final_score=62.0,
            recommendation="Hold",
        )
        restored = _from_cache(_to_cacheable(original))
        assert restored.ticker == original.ticker
        assert restored.fundamental_score == original.fundamental_score
        assert restored.final_score == original.final_score
        assert restored.recommendation == original.recommendation


class TestGenerateNarrative:
    @patch("agents.master_agent.llm_generate")
    def test_uses_llm_when_available(self, mock_llm):
        mock_llm.return_value = "This is a fresh LLM narrative."
        sa = StockAnalysis(
            ticker="TCS.NS",
            fundamental_score=70.0,
            fundamental_verdict="Strong",
            technical_score=60.0,
            technical_verdict="Moderate",
            sentiment_score=65.0,
            sentiment_verdict="Positive",
            final_score=65.0,
            recommendation="Buy",
        )
        result = _generate_narrative(sa)
        assert result == "This is a fresh LLM narrative."
        mock_llm.assert_called_once()

    @patch("agents.master_agent.llm_generate")
    def test_falls_back_to_rule_text(self, mock_llm):
        mock_llm.return_value = None
        sa = StockAnalysis(
            ticker="TCS.NS",
            fundamental_score=70.0,
            fundamental_verdict="Strong",
            technical_score=60.0,
            technical_verdict="Moderate",
            sentiment_score=65.0,
            sentiment_verdict="Positive",
            final_score=65.0,
            recommendation="Buy",
        )
        result = _generate_narrative(sa)
        assert "Fundamental: Strong" in result
        assert "Recommendation: Buy" in result

    @patch("agents.master_agent.llm_generate")
    def test_prompt_contains_ticker(self, mock_llm):
        mock_llm.return_value = "narrative"
        sa = StockAnalysis(ticker="RELIANCE.NS", final_score=70.0)
        _generate_narrative(sa)
        prompt_arg = mock_llm.call_args[0][0]
        assert "RELIANCE.NS" in prompt_arg


class TestCacheIntegration:
    @patch("agents.master_agent.run_analysis_graph")
    def test_cache_miss_calls_graph_and_stores(self, mock_graph):
        mock_graph.return_value = _mock_state("RELIANCE.NS")
        req = AnalysisRequest(query_type=QueryType.SINGLE_STOCK, tickers=["RELIANCE.NS"])
        resp = run_analysis(req)

        assert len(resp.stocks) == 1
        mock_graph.assert_called_once()

        from utils.cache import get_cached_analysis

        cached = get_cached_analysis("RELIANCE.NS")
        assert cached is not None
        assert cached["ticker"] == "RELIANCE.NS"

    @patch("agents.master_agent.llm_generate")
    @patch("agents.master_agent.run_analysis_graph")
    def test_cache_hit_skips_graph_calls_llm(self, mock_graph, mock_llm):
        from utils.cache import set_cached_analysis

        set_cached_analysis("RELIANCE.NS", {
            "ticker": "RELIANCE.NS",
            "fundamental_score": 75.0,
            "fundamental_verdict": "Strong",
            "technical_score": 70.0,
            "technical_verdict": "Bullish",
            "sentiment_score": 65.0,
            "sentiment_verdict": "Positive",
            "final_score": 71.0,
            "recommendation": "Buy",
            "errors": {},
        })
        mock_llm.return_value = "Fresh LLM narrative from cache hit"

        req = AnalysisRequest(query_type=QueryType.SINGLE_STOCK, tickers=["RELIANCE.NS"])
        resp = run_analysis(req)

        mock_graph.assert_not_called()
        mock_llm.assert_called_once()
        assert resp.stocks[0].explanation == "Fresh LLM narrative from cache hit"
        assert resp.stocks[0].fundamental_score == 75.0

    @patch("agents.master_agent.llm_generate")
    @patch("agents.master_agent.run_analysis_graph")
    def test_cache_hit_with_llm_failure_uses_fallback(self, mock_graph, mock_llm):
        from utils.cache import set_cached_analysis

        set_cached_analysis("TCS.NS", {
            "ticker": "TCS.NS",
            "fundamental_score": 60.0,
            "fundamental_verdict": "Moderate",
            "technical_score": 55.0,
            "technical_verdict": "Neutral",
            "sentiment_score": 50.0,
            "sentiment_verdict": "Neutral",
            "final_score": 56.0,
            "recommendation": "Hold",
            "errors": {},
        })
        mock_llm.return_value = None

        req = AnalysisRequest(query_type=QueryType.SINGLE_STOCK, tickers=["TCS.NS"])
        resp = run_analysis(req)

        mock_graph.assert_not_called()
        assert "Fundamental: Moderate" in resp.stocks[0].explanation
        assert "Recommendation: Hold" in resp.stocks[0].explanation
