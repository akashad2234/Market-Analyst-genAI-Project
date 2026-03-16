from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


class RiskLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class StockRiskProfile:
    ticker: str
    risk_level: RiskLevel
    risk_factors: list[str] = field(default_factory=list)


@dataclass
class PortfolioInsight:
    average_score: float
    overall_risk: RiskLevel
    best_performer: str
    worst_performer: str
    diversification_score: float
    risk_profiles: list[StockRiskProfile] = field(default_factory=list)
    rebalance_suggestion: str = ""
    summary: str = ""


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------

_HIGH_RISK_THRESHOLD = 40.0
_LOW_RISK_THRESHOLD = 70.0


def assess_stock_risk(
    ticker: str,
    final_score: float | None,
    fundamental_score: float | None,
    technical_score: float | None,
    sentiment_score: float | None,
) -> StockRiskProfile:
    """Categorise a single stock's risk based on its scores."""
    factors: list[str] = []

    effective_score = final_score if final_score is not None else 50.0

    if fundamental_score is not None and fundamental_score < _HIGH_RISK_THRESHOLD:
        factors.append("Weak fundamentals")
    if technical_score is not None and technical_score < _HIGH_RISK_THRESHOLD:
        factors.append("Bearish technicals")
    if sentiment_score is not None and sentiment_score < _HIGH_RISK_THRESHOLD:
        factors.append("Negative sentiment")

    sub_scores = [s for s in (fundamental_score, technical_score, sentiment_score) if s is not None]
    if len(sub_scores) >= 2:
        spread = max(sub_scores) - min(sub_scores)
        if spread > 40:
            factors.append("High divergence between analysts")

    if effective_score < _HIGH_RISK_THRESHOLD or len(factors) >= 2:
        risk = RiskLevel.HIGH
    elif effective_score >= _LOW_RISK_THRESHOLD and len(factors) == 0:
        risk = RiskLevel.LOW
    else:
        risk = RiskLevel.MEDIUM

    logger.debug("Risk for {}: {} (factors: {})", ticker, risk.value, factors)
    return StockRiskProfile(ticker=ticker, risk_level=risk, risk_factors=factors)


# ---------------------------------------------------------------------------
# Diversification scoring
# ---------------------------------------------------------------------------


def compute_diversification_score(scores: list[float]) -> float:
    """Measure portfolio diversification based on score variance.

    Returns 0-100 where higher means more diversified (wider spread of
    outcomes across holdings). A single-stock portfolio returns 0.
    """
    if len(scores) <= 1:
        return 0.0

    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)

    # Normalise: std_dev of 0 -> 0, std_dev of 50 (max realistic) -> 100
    raw = min(std_dev / 50.0, 1.0) * 100.0
    result = round(raw, 1)

    logger.debug("Diversification score: {:.1f} (std_dev={:.2f}, n={})", result, std_dev, len(scores))
    return result


# ---------------------------------------------------------------------------
# Rebalance logic
# ---------------------------------------------------------------------------


def generate_rebalance_suggestion(
    risk_profiles: list[StockRiskProfile],
    average_score: float,
) -> str:
    """Generate a human-readable rebalance suggestion based on risk distribution."""
    high_risk = [p for p in risk_profiles if p.risk_level == RiskLevel.HIGH]
    low_risk = [p for p in risk_profiles if p.risk_level == RiskLevel.LOW]
    total = len(risk_profiles)

    if total == 0:
        return "No holdings to analyse."

    high_pct = len(high_risk) / total
    low_pct = len(low_risk) / total

    parts: list[str] = []

    if high_pct > 0.5:
        parts.append(
            f"Portfolio is heavily weighted toward high-risk holdings "
            f"({len(high_risk)}/{total}). Consider reducing exposure to: "
            f"{', '.join(p.ticker for p in high_risk)}."
        )
    elif high_pct > 0:
        parts.append(
            f"{len(high_risk)} holding(s) flagged as high risk: "
            f"{', '.join(p.ticker for p in high_risk)}. Monitor closely or consider trimming."
        )

    if low_pct == 1.0:
        parts.append("All holdings are low risk. Portfolio is defensively positioned.")
    elif low_pct == 0 and len(risk_profiles) > 1:
        parts.append("No low-risk holdings detected. Consider adding defensive positions for balance.")

    if average_score >= 70:
        parts.append("Overall portfolio health is strong.")
    elif average_score >= 50:
        parts.append("Overall portfolio health is moderate.")
    else:
        parts.append("Overall portfolio health is weak. Rebalancing is recommended.")

    suggestion = " ".join(parts) if parts else "Portfolio is balanced. No immediate rebalancing needed."
    logger.debug("Rebalance suggestion: {}", suggestion)
    return suggestion


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@dataclass
class _StockInput:
    ticker: str
    final_score: float | None = None
    fundamental_score: float | None = None
    technical_score: float | None = None
    sentiment_score: float | None = None


def analyze_portfolio(stocks: list[_StockInput]) -> PortfolioInsight:
    """Run portfolio-level analysis over pre-computed per-stock results.

    Accepts a list of _StockInput (or anything duck-typed with the same
    attributes) and returns a PortfolioInsight with risk profiles,
    diversification, and rebalance advice.
    """
    logger.info("Portfolio analyzer: processing {} stocks", len(stocks))

    if not stocks:
        return PortfolioInsight(
            average_score=0.0,
            overall_risk=RiskLevel.HIGH,
            best_performer="N/A",
            worst_performer="N/A",
            diversification_score=0.0,
            rebalance_suggestion="No holdings to analyse.",
            summary="Empty portfolio.",
        )

    risk_profiles = [
        assess_stock_risk(
            s.ticker, s.final_score, s.fundamental_score,
            s.technical_score, s.sentiment_score,
        )
        for s in stocks
    ]

    effective_scores = [(s.final_score if s.final_score is not None else 50.0) for s in stocks]
    average_score = round(sum(effective_scores) / len(effective_scores), 2)

    diversification = compute_diversification_score(effective_scores)

    sorted_by_score = sorted(stocks, key=lambda s: s.final_score if s.final_score is not None else 50.0, reverse=True)
    best = sorted_by_score[0].ticker
    worst = sorted_by_score[-1].ticker

    high_count = sum(1 for p in risk_profiles if p.risk_level == RiskLevel.HIGH)
    if high_count > len(stocks) / 2:
        overall_risk = RiskLevel.HIGH
    elif high_count == 0 and average_score >= _LOW_RISK_THRESHOLD:
        overall_risk = RiskLevel.LOW
    else:
        overall_risk = RiskLevel.MEDIUM

    rebalance = generate_rebalance_suggestion(risk_profiles, average_score)

    lines = [
        f"Portfolio Summary ({len(stocks)} holdings):",
        f"  Average Score: {average_score:.1f}/100",
        f"  Overall Risk: {overall_risk.value}",
        f"  Diversification: {diversification:.1f}/100",
        f"  Best Performing: {best}",
        f"  Most Risky: {worst}",
        "",
        f"Recommendation: {rebalance}",
    ]
    summary = "\n".join(lines)

    insight = PortfolioInsight(
        average_score=average_score,
        overall_risk=overall_risk,
        best_performer=best,
        worst_performer=worst,
        diversification_score=diversification,
        risk_profiles=risk_profiles,
        rebalance_suggestion=rebalance,
        summary=summary,
    )

    logger.info("Portfolio analyzer complete. Avg={:.1f}, Risk={}", average_score, overall_risk.value)
    return insight
