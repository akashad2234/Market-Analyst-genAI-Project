from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from agents.fundamental_agent import FundamentalResult
from agents.fundamental_agent import analyze as fundamental_analyze
from agents.sentiment_agent import SentimentResult
from agents.sentiment_agent import analyze as sentiment_analyze
from agents.technical_agent import TechnicalResult
from agents.technical_agent import analyze as technical_analyze
from utils.metrics import metrics
from utils.scoring_engine import analyze_and_recommend

SCORING_WEIGHTS: dict[str, float] | None
SCORING_THRESHOLDS: list[tuple[float, str]] | None
try:
    from utils.config import SCORING_THRESHOLDS as SCORING_THRESHOLDS  # noqa: N811
    from utils.config import SCORING_WEIGHTS as SCORING_WEIGHTS  # noqa: N811
except Exception:
    SCORING_WEIGHTS = None
    SCORING_THRESHOLDS = None


@dataclass
class AnalysisState:
    """Shared state flowing through the LangGraph analysis pipeline."""

    ticker: str
    company_name: str | None = None
    fundamental: FundamentalResult | None = None
    technical: TechnicalResult | None = None
    sentiment: SentimentResult | None = None
    final_score: float | None = None
    recommendation: str | None = None
    errors: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def run_fundamental(state: AnalysisState) -> AnalysisState:
    """Node: run fundamental analysis."""
    logger.info("[graph] Running fundamental analysis for {}", state.ticker)
    try:
        with metrics.track("agent.fundamental"):
            state.fundamental = fundamental_analyze(state.ticker)
    except Exception as exc:
        logger.error("[graph] Fundamental analysis failed for {}: {}", state.ticker, exc)
        state.errors["fundamental"] = str(exc)
        metrics.record_error("agent.fundamental")
    return state


def run_technical(state: AnalysisState) -> AnalysisState:
    """Node: run technical analysis."""
    logger.info("[graph] Running technical analysis for {}", state.ticker)
    try:
        with metrics.track("agent.technical"):
            state.technical = technical_analyze(state.ticker)
    except Exception as exc:
        logger.error("[graph] Technical analysis failed for {}: {}", state.ticker, exc)
        state.errors["technical"] = str(exc)
        metrics.record_error("agent.technical")
    return state


def run_sentiment(state: AnalysisState) -> AnalysisState:
    """Node: run sentiment analysis."""
    logger.info("[graph] Running sentiment analysis for {}", state.ticker)
    try:
        with metrics.track("agent.sentiment"):
            state.sentiment = sentiment_analyze(
                state.ticker, company_name=state.company_name
            )
    except Exception as exc:
        logger.error("[graph] Sentiment analysis failed for {}: {}", state.ticker, exc)
        state.errors["sentiment"] = str(exc)
        metrics.record_error("agent.sentiment")
    return state


def aggregate_and_recommend(state: AnalysisState) -> AnalysisState:
    """Node: aggregate scores from all agents and produce a final recommendation."""
    logger.info("[graph] Aggregating results for {}", state.ticker)

    fund_score = state.fundamental.score if state.fundamental else 50.0
    tech_score = state.technical.score if state.technical else 50.0
    sent_score = state.sentiment.score if state.sentiment else 50.0

    if state.fundamental is None:
        logger.warning("[graph] Fundamental data missing for {}, using neutral 50", state.ticker)
    if state.technical is None:
        logger.warning("[graph] Technical data missing for {}, using neutral 50", state.ticker)
    if state.sentiment is None:
        logger.warning("[graph] Sentiment data missing for {}, using neutral 50", state.ticker)

    final_score, recommendation = analyze_and_recommend(
        fund_score, tech_score, sent_score,
        weights=SCORING_WEIGHTS,
        thresholds=SCORING_THRESHOLDS,
    )
    state.final_score = final_score
    state.recommendation = recommendation

    logger.info(
        "[graph] Final for {}: score={}, recommendation={}",
        state.ticker, final_score, recommendation,
    )
    return state


# ---------------------------------------------------------------------------
# Graph execution
# ---------------------------------------------------------------------------


def run_analysis_graph(ticker: str, company_name: str | None = None) -> AnalysisState:
    """Execute the full analysis pipeline for a single ticker.

    Runs fundamental, technical, and sentiment analysis (sequentially for
    reliability, with individual error isolation), then aggregates results.
    """
    logger.info("[graph] Starting analysis pipeline for {}", ticker)
    metrics.increment("pipeline.started")

    state = AnalysisState(ticker=ticker.strip().upper(), company_name=company_name)

    with metrics.track("pipeline.total"):
        state = run_fundamental(state)
        state = run_technical(state)
        state = run_sentiment(state)
        state = aggregate_and_recommend(state)

    metrics.increment("pipeline.completed")
    logger.info(
        "[graph] Pipeline complete for {}: score={}, recommendation={}, errors={}",
        state.ticker, state.final_score, state.recommendation, list(state.errors.keys()),
    )
    return state
