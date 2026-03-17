from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from agents.master_agent import AnalysisResponse, QueryType, StockAnalysis
from utils.database import close_all


@pytest.fixture(autouse=True)
def _clean_db():
    import utils.database as db_mod

    db_mod._db_path = ":memory:"
    db_mod._connections.clear()
    yield
    close_all()
    db_mod._db_path = None


def _mock_stock(ticker: str, score: float = 72.0, rec: str = "Buy") -> StockAnalysis:
    return StockAnalysis(
        ticker=ticker,
        fundamental_score=75.0,
        fundamental_verdict="Strong",
        technical_score=70.0,
        technical_verdict="Moderately Bullish",
        sentiment_score=65.0,
        sentiment_verdict="Moderately Positive",
        final_score=score,
        recommendation=rec,
        explanation=f"{ticker}: {rec} ({score}/100)",
    )


@pytest.fixture
def client():
    from backend.main import app

    return TestClient(app)


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestAnalyzeStock:
    @patch("backend.routes.stock_routes.run_analysis")
    def test_success(self, mock_run, client):
        mock_run.return_value = AnalysisResponse(
            query_type=QueryType.SINGLE_STOCK,
            stocks=[_mock_stock("RELIANCE.NS")],
            summary="RELIANCE.NS: Buy (score 72.0/100)",
        )

        resp = client.post("/analyze_stock", json={"ticker": "RELIANCE.NS"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stock"]["ticker"] == "RELIANCE.NS"
        assert data["stock"]["final_score"] == 72.0
        assert data["stock"]["recommendation"] == "Buy"
        assert "summary" in data

    @patch("backend.routes.stock_routes.run_analysis")
    def test_empty_results_returns_404(self, mock_run, client):
        mock_run.return_value = AnalysisResponse(
            query_type=QueryType.SINGLE_STOCK,
            stocks=[],
            summary="",
        )

        resp = client.post("/analyze_stock", json={"ticker": "INVALID"})
        assert resp.status_code == 404

    def test_missing_ticker_returns_422(self, client):
        resp = client.post("/analyze_stock", json={})
        assert resp.status_code == 422

    def test_empty_ticker_returns_422(self, client):
        resp = client.post("/analyze_stock", json={"ticker": ""})
        assert resp.status_code == 422

    @patch("backend.routes.stock_routes.run_analysis")
    def test_internal_error_returns_500(self, mock_run, client):
        mock_run.side_effect = RuntimeError("database down")
        resp = client.post("/analyze_stock", json={"ticker": "RELIANCE.NS"})
        assert resp.status_code == 500


class TestPortfolioAnalysis:
    @patch("backend.routes.portfolio_routes.run_analysis")
    def test_success(self, mock_run, client):
        mock_run.return_value = AnalysisResponse(
            query_type=QueryType.PORTFOLIO,
            stocks=[
                _mock_stock("TATAMOTORS.NS", 75.0, "Buy"),
                _mock_stock("INFY.NS", 68.0, "Buy"),
                _mock_stock("M&M.NS", 55.0, "Hold"),
            ],
            summary="Portfolio Summary:\n  Best: TATAMOTORS.NS\n  Risky: M&M.NS",
        )

        resp = client.post("/portfolio_analysis", json={"stocks": ["TATAMOTORS.NS", "INFY.NS", "M&M.NS"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["stocks"]) == 3
        assert "summary" in data

    def test_empty_stocks_returns_422(self, client):
        resp = client.post("/portfolio_analysis", json={"stocks": []})
        assert resp.status_code == 422

    def test_missing_stocks_returns_422(self, client):
        resp = client.post("/portfolio_analysis", json={})
        assert resp.status_code == 422


class TestCompareStocks:
    @patch("backend.routes.portfolio_routes.run_analysis")
    def test_success(self, mock_run, client):
        mock_run.return_value = AnalysisResponse(
            query_type=QueryType.COMPARISON,
            stocks=[
                _mock_stock("TATAMOTORS.NS", 78.0, "Buy"),
                _mock_stock("M&M.NS", 62.0, "Buy"),
            ],
            summary="Comparison: TATAMOTORS.NS stronger",
        )

        resp = client.post("/compare_stocks", json={"stock1": "TATAMOTORS.NS", "stock2": "M&M.NS"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["stocks"]) == 2
        assert data["stocks"][0]["ticker"] in ("TATAMOTORS.NS", "M&M.NS")

    def test_missing_stock2_returns_422(self, client):
        resp = client.post("/compare_stocks", json={"stock1": "TATAMOTORS.NS"})
        assert resp.status_code == 422

    @patch("backend.routes.portfolio_routes.run_analysis")
    def test_internal_error_returns_500(self, mock_run, client):
        mock_run.side_effect = RuntimeError("timeout")
        resp = client.post("/compare_stocks", json={"stock1": "A.NS", "stock2": "B.NS"})
        assert resp.status_code == 500
