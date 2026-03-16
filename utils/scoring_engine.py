from __future__ import annotations

from loguru import logger

_DEFAULT_WEIGHTS = {
    "fundamental": 0.4,
    "technical": 0.4,
    "sentiment": 0.2,
}

_DEFAULT_THRESHOLDS = [
    (80, "Strong Buy"),
    (60, "Buy"),
    (40, "Hold"),
    (0, "Avoid"),
]


def compute_final_score(
    fundamental_score: float,
    technical_score: float,
    sentiment_score: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Compute a weighted final score from the three agent scores.

    Each input score should be 0-100. Returns a score 0-100.
    """
    w = weights or _DEFAULT_WEIGHTS

    if abs(sum(w.values()) - 1.0) > 0.01:
        logger.warning("Scoring weights do not sum to 1.0: {}", w)

    score = (
        fundamental_score * w.get("fundamental", 0.4)
        + technical_score * w.get("technical", 0.4)
        + sentiment_score * w.get("sentiment", 0.2)
    )
    result = round(max(0.0, min(100.0, score)), 2)

    logger.debug(
        "Final score: {:.2f} (fund={:.1f}*{}, tech={:.1f}*{}, sent={:.1f}*{})",
        result,
        fundamental_score, w.get("fundamental", 0.4),
        technical_score, w.get("technical", 0.4),
        sentiment_score, w.get("sentiment", 0.2),
    )
    return result


def get_recommendation(
    score: float,
    thresholds: list[tuple[float, str]] | None = None,
) -> str:
    """Map a final score to a recommendation label.

    Thresholds should be a list of (min_score, label) sorted descending.
    """
    t = thresholds or _DEFAULT_THRESHOLDS

    for min_score, label in t:
        if score >= min_score:
            logger.debug("Score {:.2f} -> recommendation '{}'", score, label)
            return label

    return "Avoid"


def analyze_and_recommend(
    fundamental_score: float,
    technical_score: float,
    sentiment_score: float,
    weights: dict[str, float] | None = None,
    thresholds: list[tuple[float, str]] | None = None,
) -> tuple[float, str]:
    """Convenience function: compute final score and recommendation in one call."""
    score = compute_final_score(fundamental_score, technical_score, sentiment_score, weights)
    recommendation = get_recommendation(score, thresholds)

    logger.info(
        "Final recommendation: {} (score={:.2f}, fund={:.1f}, tech={:.1f}, sent={:.1f})",
        recommendation, score, fundamental_score, technical_score, sentiment_score,
    )
    return score, recommendation
