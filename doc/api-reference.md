# API Reference

Base URL: `http://localhost:8000`

All endpoints return JSON. The API uses Pydantic models for request/response validation.

---

## Health Check

### `GET /health`

Returns service status.

**Response:**

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Metrics

### `GET /metrics`

Returns live in-memory metrics (counters, latencies, errors).

**Response:**

```json
{
  "counters": {
    "pipeline.started": 5,
    "pipeline.completed": 5,
    "agent.fundamental": 5,
    "agent.technical": 5,
    "agent.sentiment": 5,
    "pipeline.total": 5
  },
  "latencies": {
    "agent.fundamental": {
      "count": 5,
      "avg_ms": 320.5,
      "min_ms": 210.0,
      "max_ms": 450.0,
      "total_ms": 1602.5
    }
  },
  "errors": {}
}
```

---

## Stock Analysis

### `POST /analyze_stock`

Analyse a single stock ticker.

**Request:**

```json
{
  "ticker": "RELIANCE.NS"
}
```

**Response:**

```json
{
  "stock": {
    "ticker": "RELIANCE.NS",
    "fundamental_score": 72.5,
    "fundamental_verdict": "Moderate",
    "technical_score": 65.0,
    "technical_verdict": "Moderately Bullish",
    "sentiment_score": 58.0,
    "sentiment_verdict": "Moderately Positive",
    "final_score": 66.6,
    "recommendation": "Buy",
    "explanation": "Fundamental: Moderate (72.5) | Technical: Moderately Bullish (65.0) | ...",
    "errors": {}
  },
  "summary": "RELIANCE.NS: Buy (score 66.6/100)"
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 422 | Missing or empty `ticker` field |
| 404 | No analysis results returned |
| 500 | Internal error (agent failure, data source issue) |

---

## Portfolio Analysis

### `POST /portfolio_analysis`

Analyse multiple stocks as a portfolio with risk profiling and rebalance advice.

**Request:**

```json
{
  "stocks": ["TATAMOTORS.NS", "INFY.NS", "M&M.NS"]
}
```

**Response:**

```json
{
  "stocks": [
    {
      "ticker": "TATAMOTORS.NS",
      "fundamental_score": 68.0,
      "technical_score": 72.0,
      "sentiment_score": 60.0,
      "final_score": 68.0,
      "recommendation": "Buy",
      "explanation": "...",
      "errors": {}
    }
  ],
  "summary": "Portfolio Summary (3 holdings):\n  Average Score: 62.0/100\n  ...",
  "portfolio_insight": {
    "average_score": 62.0,
    "overall_risk": "Medium",
    "best_performer": "TATAMOTORS.NS",
    "worst_performer": "M&M.NS",
    "diversification_score": 35.2,
    "risk_profiles": [
      {
        "ticker": "TATAMOTORS.NS",
        "risk_level": "Low",
        "risk_factors": []
      },
      {
        "ticker": "M&M.NS",
        "risk_level": "High",
        "risk_factors": ["Weak fundamentals", "Bearish technicals"]
      }
    ],
    "rebalance_suggestion": "1 holding(s) flagged as high risk: M&M.NS. Monitor closely or consider trimming."
  }
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 422 | Missing `stocks` field or empty list |
| 500 | Internal error |

---

## Compare Stocks

### `POST /compare_stocks`

Compare two stocks side by side.

**Request:**

```json
{
  "stock1": "TATAMOTORS.NS",
  "stock2": "M&M.NS"
}
```

**Response:**

```json
{
  "stocks": [
    {
      "ticker": "TATAMOTORS.NS",
      "final_score": 72.0,
      "recommendation": "Buy",
      "...": "..."
    },
    {
      "ticker": "M&M.NS",
      "final_score": 55.0,
      "recommendation": "Hold",
      "...": "..."
    }
  ],
  "summary": "Comparison Results:\n  1. TATAMOTORS.NS: Buy (72.0/100)\n  2. M&M.NS: Hold (55.0/100)\nRecommendation: TATAMOTORS.NS shows stronger overall profile."
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| 422 | Missing `stock1` or `stock2` field |
| 500 | Internal error |

---

## Response Headers

All responses include:

| Header | Description |
|---|---|
| `X-Request-ID` | Unique correlation ID for the request (12-char hex or echoed from `X-Request-ID` in the request) |

---

## Pydantic Models

Defined in `backend/schemas.py`:

- `AnalyzeStockRequest` / `AnalyzeStockResponse`
- `PortfolioAnalysisRequest` / `PortfolioAnalysisResponse`
- `CompareStocksRequest` / `CompareStocksResponse`
- `StockAnalysisResponse` (shared per-stock result)
- `PortfolioInsightResponse` / `StockRiskProfileResponse`
- `HealthResponse`
