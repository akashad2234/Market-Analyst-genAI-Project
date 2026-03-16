from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AnalyzeStockRequest(BaseModel):
    ticker: str = Field(..., min_length=1, examples=["RELIANCE.NS"])


class PortfolioAnalysisRequest(BaseModel):
    stocks: list[str] = Field(..., min_length=1, examples=[["TATAMOTORS.NS", "M&M.NS", "INFY.NS"]])


class CompareStocksRequest(BaseModel):
    stock1: str = Field(..., min_length=1, examples=["TATAMOTORS.NS"])
    stock2: str = Field(..., min_length=1, examples=["M&M.NS"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class StockAnalysisResponse(BaseModel):
    ticker: str
    fundamental_score: float | None = None
    fundamental_verdict: str = ""
    technical_score: float | None = None
    technical_verdict: str = ""
    sentiment_score: float | None = None
    sentiment_verdict: str = ""
    final_score: float | None = None
    recommendation: str = ""
    explanation: str = ""
    errors: dict[str, str] = Field(default_factory=dict)


class AnalyzeStockResponse(BaseModel):
    stock: StockAnalysisResponse
    summary: str = ""


class StockRiskProfileResponse(BaseModel):
    ticker: str
    risk_level: str = ""
    risk_factors: list[str] = Field(default_factory=list)


class PortfolioInsightResponse(BaseModel):
    average_score: float = 0.0
    overall_risk: str = ""
    best_performer: str = ""
    worst_performer: str = ""
    diversification_score: float = 0.0
    risk_profiles: list[StockRiskProfileResponse] = Field(default_factory=list)
    rebalance_suggestion: str = ""


class PortfolioAnalysisResponse(BaseModel):
    stocks: list[StockAnalysisResponse]
    summary: str = ""
    portfolio_insight: PortfolioInsightResponse | None = None


class CompareStocksResponse(BaseModel):
    stocks: list[StockAnalysisResponse]
    summary: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
