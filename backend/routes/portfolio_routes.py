from fastapi import APIRouter, HTTPException
from loguru import logger

from agents.master_agent import (
    AnalysisRequest,
    QueryType,
    run_analysis,
)
from backend.schemas import (
    CompareStocksRequest,
    CompareStocksResponse,
    PortfolioAnalysisRequest,
    PortfolioAnalysisResponse,
    PortfolioInsightResponse,
    StockAnalysisResponse,
    StockRiskProfileResponse,
)
from data_sources.yahoo_finance import normalize_ticker

router = APIRouter(tags=["Portfolio & Comparison"])


def _to_stock_response(sa) -> StockAnalysisResponse:
    return StockAnalysisResponse(
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


@router.post("/portfolio_analysis", response_model=PortfolioAnalysisResponse)
def portfolio_analysis(request: PortfolioAnalysisRequest) -> PortfolioAnalysisResponse:
    logger.info("API: /portfolio_analysis called with stocks={}", request.stocks)

    try:
        tickers = [normalize_ticker(t) for t in request.stocks]
        analysis_request = AnalysisRequest(
            query_type=QueryType.PORTFOLIO,
            tickers=tickers,
            raw_query=", ".join(tickers),
        )
        response = run_analysis(analysis_request)

        stock_responses = [_to_stock_response(sa) for sa in response.stocks]

        insight_resp = None
        if response.portfolio_insight:
            pi = response.portfolio_insight
            insight_resp = PortfolioInsightResponse(
                average_score=pi.average_score,
                overall_risk=pi.overall_risk.value,
                best_performer=pi.best_performer,
                worst_performer=pi.worst_performer,
                diversification_score=pi.diversification_score,
                risk_profiles=[
                    StockRiskProfileResponse(
                        ticker=rp.ticker,
                        risk_level=rp.risk_level.value,
                        risk_factors=rp.risk_factors,
                    )
                    for rp in pi.risk_profiles
                ],
                rebalance_suggestion=pi.rebalance_suggestion,
            )

        logger.info("API: /portfolio_analysis complete for {} stocks", len(stock_responses))
        return PortfolioAnalysisResponse(
            stocks=stock_responses,
            summary=response.summary,
            portfolio_insight=insight_resp,
        )

    except Exception as exc:
        logger.error("API: /portfolio_analysis failed: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/compare_stocks", response_model=CompareStocksResponse)
def compare_stocks(request: CompareStocksRequest) -> CompareStocksResponse:
    logger.info("API: /compare_stocks called with stock1={}, stock2={}", request.stock1, request.stock2)

    try:
        tickers = [normalize_ticker(request.stock1), normalize_ticker(request.stock2)]
        analysis_request = AnalysisRequest(
            query_type=QueryType.COMPARISON,
            tickers=tickers,
            raw_query=f"{tickers[0]} vs {tickers[1]}",
        )
        response = run_analysis(analysis_request)

        stock_responses = [_to_stock_response(sa) for sa in response.stocks]

        logger.info("API: /compare_stocks complete: {} vs {}", tickers[0], tickers[1])
        return CompareStocksResponse(stocks=stock_responses, summary=response.summary)

    except Exception as exc:
        logger.error("API: /compare_stocks failed: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
