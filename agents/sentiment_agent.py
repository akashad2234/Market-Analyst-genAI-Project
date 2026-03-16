from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from data_sources.duckduckgo_search import search_news
from utils.llm_client import generate as llm_generate
from utils.prompt_templates import SENTIMENT_ANALYSIS_PROMPT

_POSITIVE_KEYWORDS = frozenset({
    "surge", "surges", "surging", "jump", "jumps", "jumping",
    "rally", "rallies", "rallying", "gain", "gains", "gaining",
    "rise", "rises", "rising", "soar", "soars", "soaring",
    "boost", "boosts", "boosting", "record", "high", "highs",
    "outperform", "upgrade", "upgrades", "buy", "bullish",
    "strong", "growth", "profit", "profits", "profitable",
    "beat", "beats", "exceeded", "positive", "optimistic",
    "upbeat", "recovery", "recovered", "breakout", "momentum",
})

_NEGATIVE_KEYWORDS = frozenset({
    "crash", "crashes", "crashing", "fall", "falls", "falling",
    "drop", "drops", "dropping", "plunge", "plunges", "plunging",
    "decline", "declines", "declining", "loss", "losses", "losing",
    "slump", "slumps", "slumping", "sink", "sinks", "sinking",
    "downgrade", "downgrades", "sell", "bearish", "weak",
    "debt", "default", "risk", "risks", "warning", "concern",
    "negative", "pessimistic", "miss", "missed", "misses",
    "cut", "cuts", "layoff", "layoffs", "fraud", "scandal",
})

_NEUTRAL = 50.0


@dataclass
class SentimentResult:
    """Structured output from the Sentiment Analyst Agent."""

    ticker: str
    score: float  # 0-100
    verdict: str  # Positive, Moderately Positive, Neutral, Moderately Negative, Negative
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    articles: list[dict[str, Any]] = field(default_factory=list)
    explanation: str = ""


def _classify_article(article: dict[str, Any]) -> tuple[str, float]:
    """Classify a single article as positive, negative, or neutral using keyword matching.

    Returns (label, score) where score is 0-100.
    """
    text = f"{article.get('title', '')} {article.get('snippet', '')}".lower()
    words = set(text.split())

    pos_hits = len(words & _POSITIVE_KEYWORDS)
    neg_hits = len(words & _NEGATIVE_KEYWORDS)

    if pos_hits > neg_hits:
        confidence = min(95.0, 60.0 + pos_hits * 10)
        return "positive", confidence
    if neg_hits > pos_hits:
        confidence = max(5.0, 40.0 - neg_hits * 10)
        return "negative", confidence
    return "neutral", 50.0


def _aggregate_scores(classified: list[tuple[str, float]]) -> tuple[float, int, int, int]:
    """Aggregate individual article scores into an overall sentiment score.

    Returns (overall_score, positive_count, negative_count, neutral_count).
    """
    if not classified:
        return _NEUTRAL, 0, 0, 0

    pos_count = sum(1 for label, _ in classified if label == "positive")
    neg_count = sum(1 for label, _ in classified if label == "negative")
    neu_count = sum(1 for label, _ in classified if label == "neutral")

    total = len(classified)
    avg_score = sum(score for _, score in classified) / total

    pos_ratio = pos_count / total
    neg_ratio = neg_count / total
    ratio_bias = (pos_ratio - neg_ratio) * 30

    overall = max(0.0, min(100.0, avg_score + ratio_bias))
    return round(overall, 2), pos_count, neg_count, neu_count


def _verdict_from_score(score: float) -> str:
    if score >= 70:
        return "Positive"
    if score >= 55:
        return "Moderately Positive"
    if score >= 45:
        return "Neutral"
    if score >= 30:
        return "Moderately Negative"
    return "Negative"


def _build_rule_explanation(
    ticker: str,
    articles: list[dict[str, Any]],
    classified: list[tuple[str, float]],
    score: float,
    verdict: str,
    pos: int,
    neg: int,
    neu: int,
) -> str:
    """Build a rule-based, human-readable explanation of the sentiment analysis."""
    lines = [f"Sentiment Analysis for {ticker}", ""]

    total = len(classified)
    lines.append(f"  Articles analyzed: {total}")
    lines.append(f"  Positive: {pos} | Negative: {neg} | Neutral: {neu}")
    lines.append("")

    for article, (label, art_score) in zip(articles[:5], classified[:5]):
        title = article.get("title", "Untitled")[:80]
        lines.append(
            f"  [{label.upper():>8}] ({art_score:.0f}) {title}"
        )

    if total > 5:
        lines.append(f"  ... and {total - 5} more articles")

    lines.append("")
    lines.append(f"Overall Score: {score:.1f}/100")
    lines.append(f"Verdict: {verdict} Sentiment")

    return "\n".join(lines)


def _build_explanation(
    ticker: str,
    articles: list[dict[str, Any]],
    classified: list[tuple[str, float]],
    score: float,
    verdict: str,
    pos: int,
    neg: int,
    neu: int,
) -> str:
    """Build explanation: LLM narrative when enabled, rule-based otherwise."""
    rule_text = _build_rule_explanation(
        ticker, articles, classified, score, verdict, pos, neg, neu,
    )

    headlines_text = "\n".join(
        f"- {a.get('title', 'Untitled')}" for a in articles[:10]
    )
    prompt = SENTIMENT_ANALYSIS_PROMPT.format(
        ticker=ticker,
        headlines=headlines_text or "(no headlines)",
        score=score,
        verdict=verdict,
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
    )
    llm_text = llm_generate(prompt)

    if llm_text:
        return f"{rule_text}\n\nAI Narrative:\n{llm_text}"
    return rule_text


def analyze(
    ticker: str,
    company_name: str | None = None,
    max_results: int = 10,
) -> SentimentResult:
    """Run sentiment analysis on a single stock ticker.

    Fetches recent news via DuckDuckGo, classifies each article,
    aggregates into an overall sentiment score (0-100), and returns a structured result.
    """
    ticker = ticker.strip().upper()
    logger.info("Starting sentiment analysis for {} (company={})", ticker, company_name)

    articles = search_news(ticker, company_name=company_name, max_results=max_results)
    logger.debug("Fetched {} articles for {}", len(articles), ticker)

    if not articles:
        logger.warning("No articles found for {}. Returning neutral sentiment.", ticker)
        return SentimentResult(
            ticker=ticker,
            score=_NEUTRAL,
            verdict="Neutral",
            explanation=(
                f"Sentiment Analysis for {ticker}\n\n"
                "  No news articles found. Defaulting to neutral sentiment.\n\n"
                "Overall Score: 50.0/100\nVerdict: Neutral Sentiment"
            ),
        )

    classified = [_classify_article(a) for a in articles]
    overall_score, pos, neg, neu = _aggregate_scores(classified)
    verdict = _verdict_from_score(overall_score)

    explanation = _build_explanation(ticker, articles, classified, overall_score, verdict, pos, neg, neu)

    result = SentimentResult(
        ticker=ticker,
        score=overall_score,
        verdict=verdict,
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
        articles=articles,
        explanation=explanation,
    )

    logger.info(
        "Sentiment analysis for {}: score={}, verdict={} (pos={}, neg={}, neu={})",
        ticker, overall_score, verdict, pos, neg, neu,
    )
    logger.debug("Sentiment explanation:\n{}", explanation)
    return result
