from unittest.mock import patch

import pytest

from agents.fundamental_agent import FundamentalResult
from agents.sentiment_agent import SentimentResult
from agents.technical_agent import TechnicalResult
from langgraph.graph_builder import (
    AnalysisState,
    aggregate_and_recommend,
    run_analysis_graph,
    run_fundamental,
    run_sentiment,
    run_technical,
)


def _mock_fundamental_result(ticker: str = "TEST.NS", score: float = 75.0) -> FundamentalResult:
    return FundamentalResult(ticker=ticker, score=score, verdict="Strong")


def _mock_technical_result(ticker: str = "TEST.NS", score: float = 70.0) -> TechnicalResult:
    return TechnicalResult(ticker=ticker, score=score, verdict="Moderately Bullish")


def _mock_sentiment_result(ticker: str = "TEST.NS", score: float = 65.0) -> SentimentResult:
    return SentimentResult(ticker=ticker, score=score, verdict="Moderately Positive")


class TestRunFundamental:
    @patch("langgraph.graph_builder.fundamental_analyze")
    def test_success(self, mock_analyze):
        mock_analyze.return_value = _mock_fundamental_result()
        state = AnalysisState(ticker="TEST.NS")
        state = run_fundamental(state)

        assert state.fundamental is not None
        assert state.fundamental.score == 75.0
        assert "fundamental" not in state.errors

    @patch("langgraph.graph_builder.fundamental_analyze")
    def test_error_isolated(self, mock_analyze):
        mock_analyze.side_effect = RuntimeError("data source down")
        state = AnalysisState(ticker="TEST.NS")
        state = run_fundamental(state)

        assert state.fundamental is None
        assert "fundamental" in state.errors


class TestRunTechnical:
    @patch("langgraph.graph_builder.technical_analyze")
    def test_success(self, mock_analyze):
        mock_analyze.return_value = _mock_technical_result()
        state = AnalysisState(ticker="TEST.NS")
        state = run_technical(state)

        assert state.technical is not None
        assert state.technical.score == 70.0

    @patch("langgraph.graph_builder.technical_analyze")
    def test_error_isolated(self, mock_analyze):
        mock_analyze.side_effect = RuntimeError("timeout")
        state = AnalysisState(ticker="TEST.NS")
        state = run_technical(state)

        assert state.technical is None
        assert "technical" in state.errors


class TestRunSentiment:
    @patch("langgraph.graph_builder.sentiment_analyze")
    def test_success(self, mock_analyze):
        mock_analyze.return_value = _mock_sentiment_result()
        state = AnalysisState(ticker="TEST.NS")
        state = run_sentiment(state)

        assert state.sentiment is not None
        assert state.sentiment.score == 65.0

    @patch("langgraph.graph_builder.sentiment_analyze")
    def test_error_isolated(self, mock_analyze):
        mock_analyze.side_effect = RuntimeError("rate limited")
        state = AnalysisState(ticker="TEST.NS")
        state = run_sentiment(state)

        assert state.sentiment is None
        assert "sentiment" in state.errors

    @patch("langgraph.graph_builder.sentiment_analyze")
    def test_company_name_forwarded(self, mock_analyze):
        mock_analyze.return_value = _mock_sentiment_result()
        state = AnalysisState(ticker="TEST.NS", company_name="Test Corp")
        run_sentiment(state)
        mock_analyze.assert_called_once_with("TEST.NS", company_name="Test Corp")


class TestAggregateAndRecommend:
    def test_all_agents_present(self):
        state = AnalysisState(ticker="TEST.NS")
        state.fundamental = _mock_fundamental_result(score=80.0)
        state.technical = _mock_technical_result(score=70.0)
        state.sentiment = _mock_sentiment_result(score=60.0)

        state = aggregate_and_recommend(state)

        expected = 80 * 0.4 + 70 * 0.4 + 60 * 0.2
        assert state.final_score == pytest.approx(expected)
        assert state.recommendation in ("Strong Buy", "Buy")

    def test_missing_agents_use_neutral(self):
        state = AnalysisState(ticker="TEST.NS")

        state = aggregate_and_recommend(state)

        assert state.final_score == pytest.approx(50.0)
        assert state.recommendation == "Hold"

    def test_partial_agents_degrade_gracefully(self):
        state = AnalysisState(ticker="TEST.NS")
        state.fundamental = _mock_fundamental_result(score=90.0)

        state = aggregate_and_recommend(state)

        assert state.final_score is not None
        assert state.recommendation is not None
        assert state.final_score > 50.0


class TestRunAnalysisGraph:
    @patch("langgraph.graph_builder.sentiment_analyze")
    @patch("langgraph.graph_builder.technical_analyze")
    @patch("langgraph.graph_builder.fundamental_analyze")
    def test_full_pipeline_success(self, mock_fund, mock_tech, mock_sent):
        mock_fund.return_value = _mock_fundamental_result(score=80.0)
        mock_tech.return_value = _mock_technical_result(score=70.0)
        mock_sent.return_value = _mock_sentiment_result(score=60.0)

        state = run_analysis_graph("TEST.NS")

        assert state.ticker == "TEST.NS"
        assert state.fundamental is not None
        assert state.technical is not None
        assert state.sentiment is not None
        assert state.final_score is not None
        assert state.recommendation is not None
        assert len(state.errors) == 0

    @patch("langgraph.graph_builder.sentiment_analyze")
    @patch("langgraph.graph_builder.technical_analyze")
    @patch("langgraph.graph_builder.fundamental_analyze")
    def test_one_agent_fails_others_proceed(self, mock_fund, mock_tech, mock_sent):
        mock_fund.side_effect = RuntimeError("fail")
        mock_tech.return_value = _mock_technical_result(score=70.0)
        mock_sent.return_value = _mock_sentiment_result(score=60.0)

        state = run_analysis_graph("TEST.NS")

        assert state.fundamental is None
        assert "fundamental" in state.errors
        assert state.technical is not None
        assert state.sentiment is not None
        assert state.final_score is not None

    @patch("langgraph.graph_builder.sentiment_analyze")
    @patch("langgraph.graph_builder.technical_analyze")
    @patch("langgraph.graph_builder.fundamental_analyze")
    def test_all_agents_fail_returns_neutral(self, mock_fund, mock_tech, mock_sent):
        mock_fund.side_effect = RuntimeError("fail")
        mock_tech.side_effect = RuntimeError("fail")
        mock_sent.side_effect = RuntimeError("fail")

        state = run_analysis_graph("TEST.NS")

        assert state.final_score == pytest.approx(50.0)
        assert state.recommendation == "Hold"
        assert len(state.errors) == 3

    @patch("langgraph.graph_builder.sentiment_analyze")
    @patch("langgraph.graph_builder.technical_analyze")
    @patch("langgraph.graph_builder.fundamental_analyze")
    def test_ticker_normalized(self, mock_fund, mock_tech, mock_sent):
        mock_fund.return_value = _mock_fundamental_result()
        mock_tech.return_value = _mock_technical_result()
        mock_sent.return_value = _mock_sentiment_result()

        state = run_analysis_graph("  test.ns  ")
        assert state.ticker == "TEST.NS"
