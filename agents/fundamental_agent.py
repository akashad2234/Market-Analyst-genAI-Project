from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from data_sources.yahoo_finance import get_financials
from utils.llm_client import generate as llm_generate
from utils.prompt_templates import FUNDAMENTAL_ANALYSIS_PROMPT


@dataclass
class FundamentalResult:
    """Structured output from the Fundamental Analyst Agent."""

    ticker: str
    score: float  # 0-100
    verdict: str  # Strong, Moderate, Weak, Very Weak
    metrics: dict[str, Any] = field(default_factory=dict)
    metric_scores: dict[str, float] = field(default_factory=dict)
    explanation: str = ""


# ---------------------------------------------------------------------------
# Metric scoring functions
#
# Each function takes a raw value and returns a score between 0 and 100.
# None values yield a neutral 50 (insufficient data).
# ---------------------------------------------------------------------------

_NEUTRAL = 50.0


def _score_pe_ratio(pe: float | None) -> float:
    """Lower PE is generally better (undervalued). Negative PE means losses."""
    if pe is None:
        return _NEUTRAL
    if pe < 0:
        return 10.0
    if pe <= 10:
        return 95.0
    if pe <= 15:
        return 85.0
    if pe <= 20:
        return 70.0
    if pe <= 30:
        return 55.0
    if pe <= 50:
        return 35.0
    return 15.0


def _score_debt_to_equity(de: float | None) -> float:
    """Lower D/E is safer. yfinance returns this as a percentage (e.g. 45 = 0.45 ratio)."""
    if de is None:
        return _NEUTRAL
    ratio = de / 100.0 if de > 5 else de
    if ratio <= 0.3:
        return 95.0
    if ratio <= 0.5:
        return 80.0
    if ratio <= 1.0:
        return 65.0
    if ratio <= 1.5:
        return 45.0
    if ratio <= 2.5:
        return 25.0
    return 10.0


def _score_return_on_equity(roe: float | None) -> float:
    """Higher ROE is better. Comes as a fraction (0.12 = 12%)."""
    if roe is None:
        return _NEUTRAL
    pct = roe * 100 if abs(roe) < 1 else roe
    if pct < 0:
        return 10.0
    if pct >= 25:
        return 95.0
    if pct >= 18:
        return 80.0
    if pct >= 12:
        return 65.0
    if pct >= 8:
        return 50.0
    return 30.0


def _score_profit_margin(margin: float | None) -> float:
    """Higher margin is better. Comes as a fraction (0.08 = 8%)."""
    if margin is None:
        return _NEUTRAL
    pct = margin * 100 if abs(margin) < 1 else margin
    if pct < 0:
        return 10.0
    if pct >= 25:
        return 95.0
    if pct >= 15:
        return 80.0
    if pct >= 10:
        return 65.0
    if pct >= 5:
        return 50.0
    return 25.0


def _score_revenue_growth(growth: float | None) -> float:
    """Higher growth is better. Comes as a fraction (0.14 = 14%)."""
    if growth is None:
        return _NEUTRAL
    pct = growth * 100 if abs(growth) < 2 else growth
    if pct < -10:
        return 10.0
    if pct < 0:
        return 30.0
    if pct >= 25:
        return 95.0
    if pct >= 15:
        return 80.0
    if pct >= 8:
        return 65.0
    if pct >= 3:
        return 50.0
    return 35.0


def _score_peg_ratio(peg: float | None) -> float:
    """PEG near 1 is ideal. < 1 is undervalued, > 2 is overvalued."""
    if peg is None:
        return _NEUTRAL
    if peg < 0:
        return 10.0
    if peg <= 0.5:
        return 90.0
    if peg <= 1.0:
        return 85.0
    if peg <= 1.5:
        return 65.0
    if peg <= 2.0:
        return 45.0
    return 20.0


# Weights for combining individual metric scores
_METRIC_WEIGHTS: dict[str, float] = {
    "pe_ratio": 0.20,
    "debt_to_equity": 0.20,
    "return_on_equity": 0.20,
    "profit_margin": 0.15,
    "revenue_growth": 0.15,
    "peg_ratio": 0.10,
}

_SCORERS: dict[str, Any] = {
    "pe_ratio": _score_pe_ratio,
    "debt_to_equity": _score_debt_to_equity,
    "return_on_equity": _score_return_on_equity,
    "profit_margin": _score_profit_margin,
    "revenue_growth": _score_revenue_growth,
    "peg_ratio": _score_peg_ratio,
}


def _verdict_from_score(score: float) -> str:
    if score >= 75:
        return "Strong"
    if score >= 55:
        return "Moderate"
    if score >= 35:
        return "Weak"
    return "Very Weak"


def _build_rule_explanation(
    ticker: str,
    metrics: dict,
    metric_scores: dict,
    score: float,
    verdict: str,
) -> str:
    """Build a rule-based, human-readable explanation of the fundamental analysis."""
    lines = [f"Fundamental Analysis for {ticker}", ""]

    def _fmt(key: str, label: str, fmt_func) -> str:
        val = metrics.get(key)
        sc = metric_scores.get(key, _NEUTRAL)
        val_str = fmt_func(val) if val is not None else "N/A"
        return f"  {label}: {val_str} (score: {sc:.0f}/100)"

    lines.append(_fmt("pe_ratio", "PE Ratio", lambda v: f"{v:.1f}"))
    lines.append(
        _fmt(
            "debt_to_equity",
            "Debt/Equity",
            lambda v: f"{v:.2f}" if v <= 5 else f"{v:.0f}%",
        )
    )
    lines.append(
        _fmt(
            "return_on_equity",
            "ROE",
            lambda v: f"{v * 100:.1f}%" if abs(v) < 1 else f"{v:.1f}%",
        )
    )
    lines.append(
        _fmt(
            "profit_margin",
            "Profit Margin",
            lambda v: f"{v * 100:.1f}%" if abs(v) < 1 else f"{v:.1f}%",
        )
    )
    lines.append(
        _fmt(
            "revenue_growth",
            "Revenue Growth",
            lambda v: f"{v * 100:.1f}%" if abs(v) < 2 else f"{v:.1f}%",
        )
    )
    lines.append(_fmt("peg_ratio", "PEG Ratio", lambda v: f"{v:.2f}"))
    lines.append("")
    lines.append(f"Overall Score: {score:.1f}/100")
    lines.append(f"Verdict: {verdict} Fundamentals")

    return "\n".join(lines)


def _build_explanation(
    ticker: str,
    metrics: dict,
    metric_scores: dict,
    score: float,
    verdict: str,
) -> str:
    """Build explanation: LLM narrative when enabled, rule-based otherwise."""
    rule_text = _build_rule_explanation(
        ticker, metrics, metric_scores, score, verdict,
    )

    prompt = FUNDAMENTAL_ANALYSIS_PROMPT.format(
        ticker=ticker,
        pe_ratio=metrics.get("pe_ratio", "N/A"),
        debt_to_equity=metrics.get("debt_to_equity", "N/A"),
        return_on_equity=metrics.get("return_on_equity", "N/A"),
        profit_margin=metrics.get("profit_margin", "N/A"),
        revenue_growth=metrics.get("revenue_growth", "N/A"),
        peg_ratio=metrics.get("peg_ratio", "N/A"),
        market_cap=metrics.get("market_cap", "N/A"),
        score=score,
        verdict=verdict,
    )
    llm_text = llm_generate(prompt)

    if llm_text:
        return f"{rule_text}\n\nAI Narrative:\n{llm_text}"
    return rule_text


def compute_fundamental_scores(financials: dict[str, Any]) -> tuple[dict[str, float], float]:
    """Compute per-metric scores and weighted total from raw financials.

    Returns:
        (metric_scores dict, total_score float)
    """
    metric_scores: dict[str, float] = {}
    weighted_sum = 0.0

    for metric, weight in _METRIC_WEIGHTS.items():
        raw_value = financials.get(metric)
        scorer = _SCORERS[metric]
        sc = scorer(raw_value)
        metric_scores[metric] = sc
        weighted_sum += sc * weight

    total = round(weighted_sum, 2)
    return metric_scores, total


def analyze(ticker: str) -> FundamentalResult:
    """Run fundamental analysis on a single stock ticker.

    Fetches financials from Yahoo Finance, scores each metric,
    computes a weighted total score (0-100), and returns a structured result.
    """
    ticker = ticker.strip().upper()
    logger.info("Starting fundamental analysis for {}", ticker)

    financials = get_financials(ticker)
    logger.debug("Raw financials for {}: {}", ticker, financials)

    metric_scores, total_score = compute_fundamental_scores(financials)
    verdict = _verdict_from_score(total_score)

    explanation = _build_explanation(ticker, financials, metric_scores, total_score, verdict)

    result = FundamentalResult(
        ticker=ticker,
        score=total_score,
        verdict=verdict,
        metrics=financials,
        metric_scores=metric_scores,
        explanation=explanation,
    )

    logger.info("Fundamental analysis for {}: score={}, verdict={}", ticker, total_score, verdict)
    logger.debug("Fundamental explanation:\n{}", explanation)
    return result
