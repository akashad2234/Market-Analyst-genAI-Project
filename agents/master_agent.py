from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger

from data_sources.yahoo_finance import normalize_ticker
from langgraph.graph_builder import AnalysisState, run_analysis_graph
from utils.cache import get_cached_analysis, set_cached_analysis
from utils.llm_client import generate as llm_generate
from utils.portfolio_analyzer import (
    PortfolioInsight,
    _StockInput,
    analyze_portfolio,
)
from utils.prompt_templates import SUMMARY_ANALYSIS_PROMPT


class QueryType(Enum):
    SINGLE_STOCK = "single_stock"
    PORTFOLIO = "portfolio"
    COMPARISON = "comparison"


@dataclass
class AnalysisRequest:
    """Validated input for the master agent."""

    query_type: QueryType
    tickers: list[str]
    company_names: dict[str, str] = field(default_factory=dict)
    raw_query: str = ""


@dataclass
class StockAnalysis:
    """Analysis result for a single stock within a response."""

    ticker: str
    fundamental_score: float | None = None
    fundamental_verdict: str = ""
    technical_score: float | None = None
    technical_verdict: str = ""
    sentiment_score: float | None = None
    sentiment_verdict: str = ""
    final_score: float | None = None
    recommendation: str = ""
    errors: dict[str, str] = field(default_factory=dict)
    explanation: str = ""


@dataclass
class AnalysisResponse:
    """Structured output from the master agent."""

    query_type: QueryType
    stocks: list[StockAnalysis] = field(default_factory=list)
    summary: str = ""
    portfolio_insight: PortfolioInsight | None = None


_TICKER_PATTERN = re.compile(r"^[A-Z0-9&.\-]+$")


def _clean_ticker(raw: str) -> str:
    t = normalize_ticker(raw)
    if not _TICKER_PATTERN.match(t):
        raise ValueError(f"Invalid ticker format: '{raw}'")
    return t


def parse_intent(raw_query: str) -> AnalysisRequest:
    """Parse a raw user query string into a structured AnalysisRequest.

    Supports formats:
      - "RELIANCE.NS" -> single stock
      - "TATAMOTORS.NS, INFY.NS, M&M.NS" -> portfolio
      - "TATAMOTORS.NS vs M&M.NS" -> comparison
    """
    raw_query = raw_query.strip()
    logger.info("Parsing intent from query: '{}'", raw_query)

    if " vs " in raw_query.lower() or " vs. " in raw_query.lower():
        parts = re.split(r"\s+vs\.?\s+", raw_query, flags=re.IGNORECASE)
        tickers = [_clean_ticker(p) for p in parts if p.strip()]
        if len(tickers) < 2:
            raise ValueError("Comparison requires at least two tickers.")
        logger.info("Parsed as COMPARISON: {}", tickers)
        return AnalysisRequest(
            query_type=QueryType.COMPARISON,
            tickers=tickers,
            raw_query=raw_query,
        )

    if "," in raw_query:
        parts = [p.strip() for p in raw_query.split(",") if p.strip()]
        tickers = [_clean_ticker(p) for p in parts]
        if len(tickers) >= 2:
            logger.info("Parsed as PORTFOLIO: {}", tickers)
            return AnalysisRequest(
                query_type=QueryType.PORTFOLIO,
                tickers=tickers,
                raw_query=raw_query,
            )
        if len(tickers) == 1:
            logger.info("Parsed as SINGLE_STOCK (trailing comma stripped): {}", tickers[0])
            return AnalysisRequest(
                query_type=QueryType.SINGLE_STOCK,
                tickers=tickers,
                raw_query=raw_query,
            )

    ticker = _clean_ticker(raw_query)
    logger.info("Parsed as SINGLE_STOCK: {}", ticker)
    return AnalysisRequest(
        query_type=QueryType.SINGLE_STOCK,
        tickers=[ticker],
        raw_query=raw_query,
    )


def _state_to_stock_analysis(state: AnalysisState) -> StockAnalysis:
    """Convert an AnalysisState into a StockAnalysis response object."""
    sa = StockAnalysis(ticker=state.ticker)

    if state.fundamental:
        sa.fundamental_score = state.fundamental.score
        sa.fundamental_verdict = state.fundamental.verdict
    if state.technical:
        sa.technical_score = state.technical.score
        sa.technical_verdict = state.technical.verdict
    if state.sentiment:
        sa.sentiment_score = state.sentiment.score
        sa.sentiment_verdict = state.sentiment.verdict

    sa.final_score = state.final_score
    sa.recommendation = state.recommendation or ""
    sa.errors = state.errors

    parts = []
    if state.fundamental:
        parts.append(f"Fundamental: {state.fundamental.verdict} ({state.fundamental.score:.1f})")
    if state.technical:
        parts.append(f"Technical: {state.technical.verdict} ({state.technical.score:.1f})")
    if state.sentiment:
        parts.append(f"Sentiment: {state.sentiment.verdict} ({state.sentiment.score:.1f})")
    if state.final_score is not None:
        parts.append(f"Final Score: {state.final_score:.1f}/100")
    if state.recommendation:
        parts.append(f"Recommendation: {state.recommendation}")
    sa.explanation = " | ".join(parts)

    return sa


def _build_summary(query_type: QueryType, stocks: list[StockAnalysis]) -> str:
    """Build a summary string for the response."""
    if query_type == QueryType.SINGLE_STOCK and stocks:
        s = stocks[0]
        return f"{s.ticker}: {s.recommendation} (score {s.final_score:.1f}/100)"

    if query_type == QueryType.COMPARISON and len(stocks) >= 2:
        ranked = sorted(stocks, key=lambda s: s.final_score or 0, reverse=True)
        lines = ["Comparison Results:"]
        for i, s in enumerate(ranked, 1):
            lines.append(f"  {i}. {s.ticker}: {s.recommendation} ({s.final_score:.1f}/100)")
        best = ranked[0]
        lines.append(f"Recommendation: {best.ticker} shows stronger overall profile.")
        return "\n".join(lines)

    if query_type == QueryType.PORTFOLIO and stocks:
        insight = _run_portfolio_insight(stocks)
        return insight.summary if insight else ""

    return ""


def _run_portfolio_insight(stocks: list[StockAnalysis]) -> PortfolioInsight:
    """Build enriched portfolio-level insights from per-stock results."""
    inputs = [
        _StockInput(
            ticker=s.ticker,
            final_score=s.final_score,
            fundamental_score=s.fundamental_score,
            technical_score=s.technical_score,
            sentiment_score=s.sentiment_score,
        )
        for s in stocks
    ]
    return analyze_portfolio(inputs)


def _to_cacheable(sa: StockAnalysis) -> dict:
    """Extract the score/verdict fields worth caching (no explanation)."""
    return {
        "ticker": sa.ticker,
        "fundamental_score": sa.fundamental_score,
        "fundamental_verdict": sa.fundamental_verdict,
        "technical_score": sa.technical_score,
        "technical_verdict": sa.technical_verdict,
        "sentiment_score": sa.sentiment_score,
        "sentiment_verdict": sa.sentiment_verdict,
        "final_score": sa.final_score,
        "recommendation": sa.recommendation,
        "errors": sa.errors,
    }


def _from_cache(data: dict) -> StockAnalysis:
    """Rebuild a StockAnalysis from cached scores (explanation left empty)."""
    return StockAnalysis(
        ticker=data["ticker"],
        fundamental_score=data.get("fundamental_score"),
        fundamental_verdict=data.get("fundamental_verdict", ""),
        technical_score=data.get("technical_score"),
        technical_verdict=data.get("technical_verdict", ""),
        sentiment_score=data.get("sentiment_score"),
        sentiment_verdict=data.get("sentiment_verdict", ""),
        final_score=data.get("final_score"),
        recommendation=data.get("recommendation", ""),
        errors=data.get("errors", {}),
    )


def _generate_narrative(sa: StockAnalysis) -> str:
    """Call the LLM to produce a fresh narrative for cached scores."""
    prompt = SUMMARY_ANALYSIS_PROMPT.format(
        ticker=sa.ticker,
        fundamental_score=sa.fundamental_score or "N/A",
        fundamental_verdict=sa.fundamental_verdict or "N/A",
        technical_score=sa.technical_score or "N/A",
        technical_verdict=sa.technical_verdict or "N/A",
        sentiment_score=sa.sentiment_score or "N/A",
        sentiment_verdict=sa.sentiment_verdict or "N/A",
        final_score=sa.final_score or "N/A",
        recommendation=sa.recommendation or "N/A",
    )
    narrative = llm_generate(prompt)
    if narrative:
        logger.debug("LLM narrative generated for {} ({} chars)", sa.ticker, len(narrative))
        return narrative

    parts = []
    if sa.fundamental_score is not None:
        parts.append(f"Fundamental: {sa.fundamental_verdict} ({sa.fundamental_score:.1f})")
    if sa.technical_score is not None:
        parts.append(f"Technical: {sa.technical_verdict} ({sa.technical_score:.1f})")
    if sa.sentiment_score is not None:
        parts.append(f"Sentiment: {sa.sentiment_verdict} ({sa.sentiment_score:.1f})")
    if sa.final_score is not None:
        parts.append(f"Final Score: {sa.final_score:.1f}/100")
    if sa.recommendation:
        parts.append(f"Recommendation: {sa.recommendation}")
    return " | ".join(parts)


def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """Execute analysis based on a parsed request. Main entry point for the master agent."""
    logger.info(
        "Master agent: running {} analysis for {}",
        request.query_type.value, request.tickers,
    )

    stocks: list[StockAnalysis] = []

    for ticker in request.tickers:
        cached = get_cached_analysis(ticker)
        if cached is not None:
            logger.info("Using cached analysis for {}, generating fresh narrative", ticker)
            sa = _from_cache(cached)
            sa.explanation = _generate_narrative(sa)
            stocks.append(sa)
            continue

        company_name = request.company_names.get(ticker)
        state = run_analysis_graph(ticker, company_name=company_name)
        sa = _state_to_stock_analysis(state)
        set_cached_analysis(ticker, _to_cacheable(sa))
        stocks.append(sa)

    summary = _build_summary(request.query_type, stocks)

    portfolio_insight = None
    if request.query_type == QueryType.PORTFOLIO and stocks:
        portfolio_insight = _run_portfolio_insight(stocks)

    response = AnalysisResponse(
        query_type=request.query_type,
        stocks=stocks,
        summary=summary,
        portfolio_insight=portfolio_insight,
    )

    logger.info("Master agent: analysis complete. Summary:\n{}", summary)
    return response


def analyze_query(raw_query: str) -> AnalysisResponse:
    """End-to-end convenience: parse a raw query string and run analysis."""
    request = parse_intent(raw_query)
    return run_analysis(request)
