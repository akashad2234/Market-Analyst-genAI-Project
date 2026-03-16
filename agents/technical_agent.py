from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from loguru import logger
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

from data_sources.yahoo_finance import get_historical
from utils.llm_client import generate as llm_generate
from utils.prompt_templates import TECHNICAL_ANALYSIS_PROMPT


@dataclass
class TechnicalResult:
    """Structured output from the Technical Analyst Agent."""

    ticker: str
    score: float  # 0-100
    verdict: str  # Bullish, Moderately Bullish, Neutral, Moderately Bearish, Bearish
    indicators: dict[str, Any] = field(default_factory=dict)
    interpretations: dict[str, str] = field(default_factory=dict)
    indicator_scores: dict[str, float] = field(default_factory=dict)
    explanation: str = ""


_NEUTRAL = 50.0


# ---------------------------------------------------------------------------
# Indicator computation
# ---------------------------------------------------------------------------


def compute_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """Compute technical indicators from an OHLCV DataFrame.

    Expects columns: Close, Volume (at minimum).
    Returns a dict of indicator values.
    """
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float)

    rsi_indicator = RSIIndicator(close=close, window=14)
    rsi_series = rsi_indicator.rsi()
    rsi = rsi_series.iloc[-1] if not rsi_series.empty else None

    macd_indicator = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd_indicator.macd()
    macd_signal = macd_indicator.macd_signal()
    macd_hist = macd_indicator.macd_diff()

    macd_val = macd_line.iloc[-1] if not macd_line.empty else None
    macd_sig_val = macd_signal.iloc[-1] if not macd_signal.empty else None
    macd_hist_val = macd_hist.iloc[-1] if not macd_hist.empty else None

    sma_50 = SMAIndicator(close=close, window=min(50, len(close))).sma_indicator()
    sma_200 = SMAIndicator(close=close, window=min(200, len(close))).sma_indicator()

    ma_50 = sma_50.iloc[-1] if not sma_50.empty else None
    ma_200 = sma_200.iloc[-1] if not sma_200.empty else None

    current_price = close.iloc[-1]

    recent_vol = volume.tail(10).mean() if len(volume) >= 10 else volume.mean()
    older_vol = volume.tail(30).head(20).mean() if len(volume) >= 30 else volume.mean()
    volume_change_pct = ((recent_vol - older_vol) / older_vol * 100) if older_vol > 0 else 0.0

    indicators = {
        "rsi": _safe_float(rsi),
        "macd": _safe_float(macd_val),
        "macd_signal": _safe_float(macd_sig_val),
        "macd_histogram": _safe_float(macd_hist_val),
        "ma_50": _safe_float(ma_50),
        "ma_200": _safe_float(ma_200),
        "current_price": _safe_float(current_price),
        "volume_change_pct": round(volume_change_pct, 2),
    }

    logger.debug("Computed indicators: {}", indicators)
    return indicators


def _safe_float(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return round(float(val), 4)


# ---------------------------------------------------------------------------
# Indicator scoring functions (each returns 0-100)
# ---------------------------------------------------------------------------


def _score_rsi(rsi: float | None) -> tuple[float, str]:
    """Score RSI. Moderate values are best; extremes indicate overbought/oversold."""
    if rsi is None:
        return _NEUTRAL, "Insufficient data"
    if rsi >= 80:
        return 15.0, "Strongly Overbought"
    if rsi >= 70:
        return 30.0, "Overbought"
    if rsi >= 55:
        return 85.0, "Bullish"
    if rsi >= 45:
        return 60.0, "Neutral"
    if rsi >= 30:
        return 35.0, "Bearish"
    if rsi >= 20:
        return 20.0, "Oversold"
    return 10.0, "Strongly Oversold"


def _score_macd(macd: float | None, signal: float | None, histogram: float | None) -> tuple[float, str]:
    """Score MACD based on crossover and histogram direction."""
    if macd is None or signal is None:
        return _NEUTRAL, "Insufficient data"

    above_signal = macd > signal
    hist_positive = (histogram or 0) > 0

    if above_signal and hist_positive:
        return 85.0, "Bullish crossover, momentum increasing"
    if above_signal and not hist_positive:
        return 60.0, "Above signal but momentum fading"
    if not above_signal and not hist_positive:
        return 20.0, "Bearish crossover, momentum declining"
    return 40.0, "Below signal but momentum recovering"


def _score_moving_averages(price: float | None, ma_50: float | None, ma_200: float | None) -> tuple[float, str]:
    """Score based on price vs MAs and golden/death cross."""
    if price is None:
        return _NEUTRAL, "Insufficient data"
    if ma_50 is None and ma_200 is None:
        return _NEUTRAL, "Insufficient data"

    above_50 = ma_50 is not None and price > ma_50
    above_200 = ma_200 is not None and price > ma_200
    golden_cross = ma_50 is not None and ma_200 is not None and ma_50 > ma_200

    if above_50 and above_200 and golden_cross:
        return 95.0, "Golden Cross, price above both MAs"
    if above_50 and above_200:
        return 80.0, "Price above both MAs"
    if above_50 and not above_200:
        return 55.0, "Price above 50MA but below 200MA"
    if not above_50 and above_200:
        return 45.0, "Price below 50MA but above 200MA"

    death_cross = ma_50 is not None and ma_200 is not None and ma_50 < ma_200
    if not above_50 and not above_200 and death_cross:
        return 10.0, "Death Cross, price below both MAs"
    if not above_50 and not above_200:
        return 20.0, "Price below both MAs"

    return _NEUTRAL, "Mixed signals"


def _score_volume_trend(change_pct: float | None) -> tuple[float, str]:
    """Score volume trend. Increasing volume confirms trend strength."""
    if change_pct is None:
        return _NEUTRAL, "Insufficient data"
    if change_pct >= 30:
        return 85.0, "Volume surging"
    if change_pct >= 10:
        return 70.0, "Volume increasing"
    if change_pct >= -10:
        return 50.0, "Volume stable"
    if change_pct >= -30:
        return 35.0, "Volume declining"
    return 20.0, "Volume drying up"


# Weights for combining indicator scores
_INDICATOR_WEIGHTS: dict[str, float] = {
    "rsi": 0.25,
    "macd": 0.25,
    "moving_averages": 0.30,
    "volume_trend": 0.20,
}


def _verdict_from_score(score: float) -> str:
    if score >= 75:
        return "Bullish"
    if score >= 60:
        return "Moderately Bullish"
    if score >= 40:
        return "Neutral"
    if score >= 25:
        return "Moderately Bearish"
    return "Bearish"


def compute_technical_scores(
    indicators: dict[str, Any],
) -> tuple[dict[str, float], dict[str, str], float]:
    """Score each indicator and compute weighted total.

    Returns:
        (indicator_scores, interpretations, total_score)
    """
    indicator_scores: dict[str, float] = {}
    interpretations: dict[str, str] = {}

    sc, interp = _score_rsi(indicators.get("rsi"))
    indicator_scores["rsi"] = sc
    interpretations["rsi"] = interp

    sc, interp = _score_macd(
        indicators.get("macd"),
        indicators.get("macd_signal"),
        indicators.get("macd_histogram"),
    )
    indicator_scores["macd"] = sc
    interpretations["macd"] = interp

    sc, interp = _score_moving_averages(
        indicators.get("current_price"),
        indicators.get("ma_50"),
        indicators.get("ma_200"),
    )
    indicator_scores["moving_averages"] = sc
    interpretations["moving_averages"] = interp

    sc, interp = _score_volume_trend(indicators.get("volume_change_pct"))
    indicator_scores["volume_trend"] = sc
    interpretations["volume_trend"] = interp

    weighted_sum = sum(
        indicator_scores[k] * _INDICATOR_WEIGHTS[k] for k in _INDICATOR_WEIGHTS
    )
    total = round(weighted_sum, 2)

    return indicator_scores, interpretations, total


def _build_rule_explanation(
    ticker: str,
    indicators: dict[str, Any],
    indicator_scores: dict[str, float],
    interpretations: dict[str, str],
    score: float,
    verdict: str,
) -> str:
    """Build a rule-based, human-readable explanation of the technical analysis."""
    lines = [f"Technical Analysis for {ticker}", ""]

    rsi = indicators.get("rsi")
    if rsi:
        lines.append(
            f"  RSI (14): {rsi:.1f}"
            f" - {interpretations.get('rsi', 'N/A')}"
        )
    else:
        lines.append("  RSI (14): N/A")

    macd = indicators.get("macd")
    sig = indicators.get("macd_signal")
    if macd is not None and sig is not None:
        lines.append(
            f"  MACD: {macd:.4f} / Signal: {sig:.4f}"
            f" - {interpretations.get('macd', 'N/A')}"
        )
    else:
        lines.append("  MACD: N/A")

    ma50 = indicators.get("ma_50")
    ma200 = indicators.get("ma_200")
    price = indicators.get("current_price")
    ma_parts = []
    if ma50 is not None:
        ma_parts.append(f"50MA={ma50:.2f}")
    if ma200 is not None:
        ma_parts.append(f"200MA={ma200:.2f}")
    if price is not None:
        ma_parts.append(f"Price={price:.2f}")
    ma_str = ", ".join(ma_parts) if ma_parts else "N/A"
    lines.append(
        f"  Moving Averages: {ma_str}"
        f" - {interpretations.get('moving_averages', 'N/A')}"
    )

    vol_change = indicators.get("volume_change_pct")
    vol_str = f"{vol_change:+.1f}%" if vol_change is not None else "N/A"
    lines.append(
        f"  Volume Trend: {vol_str}"
        f" - {interpretations.get('volume_trend', 'N/A')}"
    )

    lines.append("")
    lines.append(f"Overall Score: {score:.1f}/100")
    lines.append(f"Verdict: {verdict} Momentum")

    return "\n".join(lines)


def _build_explanation(
    ticker: str,
    indicators: dict[str, Any],
    indicator_scores: dict[str, float],
    interpretations: dict[str, str],
    score: float,
    verdict: str,
) -> str:
    """Build explanation: LLM narrative when enabled, rule-based otherwise."""
    rule_text = _build_rule_explanation(
        ticker, indicators, indicator_scores, interpretations, score, verdict,
    )

    prompt = TECHNICAL_ANALYSIS_PROMPT.format(
        ticker=ticker,
        rsi=indicators.get("rsi", "N/A"),
        macd=indicators.get("macd", "N/A"),
        macd_signal=indicators.get("macd_signal", "N/A"),
        ma_50=indicators.get("ma_50", "N/A"),
        ma_200=indicators.get("ma_200", "N/A"),
        volume_trend=indicators.get("volume_change_pct", "N/A"),
        current_price=indicators.get("current_price", "N/A"),
        score=score,
        verdict=verdict,
    )
    llm_text = llm_generate(prompt)

    if llm_text:
        return f"{rule_text}\n\nAI Narrative:\n{llm_text}"
    return rule_text


def analyze(ticker: str, period_days: int = 365, interval: str = "1d") -> TechnicalResult:
    """Run technical analysis on a single stock ticker.

    Fetches historical data, computes indicators, scores each one,
    and returns a structured result with score (0-100) and verdict.
    """
    ticker = ticker.strip().upper()
    logger.info("Starting technical analysis for {} (period={}d, interval={})", ticker, period_days, interval)

    df = get_historical(ticker, period_days=period_days, interval=interval)
    logger.debug("Historical data shape for {}: {}", ticker, df.shape)

    indicators = compute_indicators(df)
    indicator_scores, interpretations, total_score = compute_technical_scores(indicators)
    verdict = _verdict_from_score(total_score)

    explanation = _build_explanation(ticker, indicators, indicator_scores, interpretations, total_score, verdict)

    result = TechnicalResult(
        ticker=ticker,
        score=total_score,
        verdict=verdict,
        indicators=indicators,
        interpretations=interpretations,
        indicator_scores=indicator_scores,
        explanation=explanation,
    )

    logger.info("Technical analysis for {}: score={}, verdict={}", ticker, total_score, verdict)
    logger.debug("Technical explanation:\n{}", explanation)
    return result
