from fastapi import APIRouter, HTTPException
from loguru import logger

from agents.master_agent import (
    AnalysisRequest,
    QueryType,
    run_analysis,
)
from backend.schemas import (
    AnalyzeStockRequest,
    AnalyzeStockResponse,
    StockAnalysisResponse,
)
from data_sources.yahoo_finance import normalize_ticker

router = APIRouter(tags=["Stock Analysis"])


@router.post("/analyze_stock", response_model=AnalyzeStockResponse)
def analyze_stock(request: AnalyzeStockRequest) -> AnalyzeStockResponse:
    logger.info("API: /analyze_stock called with ticker={}", request.ticker)

    try:
        ticker = normalize_ticker(request.ticker)
        analysis_request = AnalysisRequest(
            query_type=QueryType.SINGLE_STOCK,
            tickers=[ticker],
            raw_query=ticker,
        )
        response = run_analysis(analysis_request)

        if not response.stocks:
            raise HTTPException(status_code=404, detail=f"No analysis results for '{request.ticker}'")

        sa = response.stocks[0]
        stock_resp = StockAnalysisResponse(
            ticker=sa.ticker,
            fundamental_score=sa.fundamental_score,
            fundamental_verdict=sa.fundamental_verdict,
            technical_score=sa.technical_score,
            technical_verdict=sa.technical_verdict,
            sentiment_score=sa.sentiment_score,
            sentiment_verdict=sa.sentiment_verdict,
            final_score=sa.final_score,
            recommendation=sa.recommendation,
            explanation=sa.explanation,
            errors=sa.errors,
        )

        logger.info(
            "API: /analyze_stock response for {}: score={}, rec={}",
            sa.ticker, sa.final_score, sa.recommendation,
        )
        return AnalyzeStockResponse(stock=stock_resp, summary=response.summary)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API: /analyze_stock failed: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
