from unittest.mock import patch

import pytest

from agents.fundamental_agent import FundamentalResult
from agents.master_agent import (
    AnalysisRequest,
    AnalysisResponse,
    QueryType,
    StockAnalysis,
    analyze_query,
    parse_intent,
    run_analysis,
)
from agents.sentiment_agent import SentimentResult
from agents.technical_agent import TechnicalResult
from langgraph.graph_builder import AnalysisState


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
