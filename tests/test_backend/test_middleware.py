from unittest.mock import patch

from fastapi.testclient import TestClient

from agents.master_agent import AnalysisResponse, QueryType, StockAnalysis


@patch("backend.routes.stock_routes.run_analysis")
def test_response_has_request_id_header(mock_run):
    mock_run.return_value = AnalysisResponse(
        query_type=QueryType.SINGLE_STOCK,
        stocks=[
            StockAnalysis(
                ticker="TEST.NS",
                final_score=60.0,
                recommendation="Buy",
            )
        ],
        summary="TEST.NS: Buy",
    )

    from backend.main import app

    client = TestClient(app)
    resp = client.post("/analyze_stock", json={"ticker": "TEST.NS"})
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) > 0


def test_custom_request_id_is_echoed():
    from backend.main import app

    client = TestClient(app)
    custom_rid = "my-custom-rid-123"
    resp = client.get("/health", headers={"x-request-id": custom_rid})
    assert resp.status_code == 200
    assert resp.headers["x-request-id"] == custom_rid


def test_health_generates_request_id():
    from backend.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    rid = resp.headers.get("x-request-id", "")
    assert len(rid) == 12


def test_metrics_endpoint_returns_structure():
    from backend.main import app

    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "counters" in data
    assert "latencies" in data
    assert "errors" in data
