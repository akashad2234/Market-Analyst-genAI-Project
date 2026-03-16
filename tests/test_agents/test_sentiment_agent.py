from unittest.mock import patch

import pytest

from agents.sentiment_agent import (
    SentimentResult,
    _aggregate_scores,
    _classify_article,
    _verdict_from_score,
    analyze,
)

POSITIVE_ARTICLE = {
    "title": "Tata Motors sales surge 18% in Q3, profits soar",
    "snippet": "Strong growth and record gains reported by the company.",
    "url": "https://example.com/1",
    "date": "2026-03-15",
    "source": "ET",
}

NEGATIVE_ARTICLE = {
    "title": "Stock crashes after fraud scandal, losses mount",
    "snippet": "Investors concerned about risk and declining revenue.",
    "url": "https://example.com/2",
    "date": "2026-03-14",
    "source": "MC",
}

NEUTRAL_ARTICLE = {
    "title": "Company announces board meeting next week",
    "snippet": "The meeting will discuss various agenda items.",
    "url": "https://example.com/3",
    "date": "2026-03-13",
    "source": "LM",
}


class TestClassifyArticle:
    def test_positive_article(self):
        label, score = _classify_article(POSITIVE_ARTICLE)
        assert label == "positive"
        assert score > 60

    def test_negative_article(self):
        label, score = _classify_article(NEGATIVE_ARTICLE)
        assert label == "negative"
        assert score < 40

    def test_neutral_article(self):
        label, score = _classify_article(NEUTRAL_ARTICLE)
        assert label == "neutral"
        assert score == 50.0

    def test_empty_article(self):
        label, score = _classify_article({})
        assert label == "neutral"
        assert score == 50.0

    def test_mixed_keywords_positive_wins(self):
        article = {
            "title": "Stock rally despite risk concerns, gains outweigh losses",
            "snippet": "Strong momentum and bullish outlook boost recovery.",
        }
        label, score = _classify_article(article)
        assert label == "positive"

    def test_mixed_keywords_negative_wins(self):
        article = {
            "title": "Stock falls despite recovery hopes",
            "snippet": "Decline continues with losses and weak performance. Bearish slump risk.",
        }
        label, score = _classify_article(article)
        assert label == "negative"


class TestAggregateScores:
    def test_empty_list(self):
        score, pos, neg, neu = _aggregate_scores([])
        assert score == 50.0
        assert pos == 0
        assert neg == 0
        assert neu == 0

    def test_all_positive(self):
        classified = [("positive", 80.0), ("positive", 70.0), ("positive", 90.0)]
        score, pos, neg, neu = _aggregate_scores(classified)
        assert score > 70
        assert pos == 3
        assert neg == 0

    def test_all_negative(self):
        classified = [("negative", 20.0), ("negative", 15.0), ("negative", 25.0)]
        score, pos, neg, neu = _aggregate_scores(classified)
        assert score < 30
        assert neg == 3
        assert pos == 0

    def test_mixed_leans_positive(self):
        classified = [("positive", 80.0), ("positive", 70.0), ("neutral", 50.0)]
        score, pos, neg, neu = _aggregate_scores(classified)
        assert score > 55
        assert pos == 2
        assert neu == 1

    def test_score_clamped_0_100(self):
        classified = [("positive", 95.0)] * 10
        score, _, _, _ = _aggregate_scores(classified)
        assert 0 <= score <= 100

        classified = [("negative", 5.0)] * 10
        score, _, _, _ = _aggregate_scores(classified)
        assert 0 <= score <= 100


class TestVerdict:
    def test_positive(self):
        assert _verdict_from_score(75.0) == "Positive"

    def test_moderately_positive(self):
        assert _verdict_from_score(60.0) == "Moderately Positive"

    def test_neutral(self):
        assert _verdict_from_score(50.0) == "Neutral"

    def test_moderately_negative(self):
        assert _verdict_from_score(35.0) == "Moderately Negative"

    def test_negative(self):
        assert _verdict_from_score(20.0) == "Negative"

    def test_boundary_70(self):
        assert _verdict_from_score(70.0) == "Positive"

    def test_boundary_55(self):
        assert _verdict_from_score(55.0) == "Moderately Positive"

    def test_boundary_45(self):
        assert _verdict_from_score(45.0) == "Neutral"

    def test_boundary_30(self):
        assert _verdict_from_score(30.0) == "Moderately Negative"


class TestAnalyze:
    @patch("agents.sentiment_agent.search_news")
    def test_positive_articles_positive_result(self, mock_search):
        mock_search.return_value = [POSITIVE_ARTICLE] * 5
        result = analyze("TATAMOTORS.NS")

        assert isinstance(result, SentimentResult)
        assert result.ticker == "TATAMOTORS.NS"
        assert result.score > 55
        assert result.verdict in ("Positive", "Moderately Positive")
        assert result.positive_count > 0

    @patch("agents.sentiment_agent.search_news")
    def test_negative_articles_negative_result(self, mock_search):
        mock_search.return_value = [NEGATIVE_ARTICLE] * 5
        result = analyze("WEAK.NS")

        assert result.score < 45
        assert result.verdict in ("Negative", "Moderately Negative")
        assert result.negative_count > 0

    @patch("agents.sentiment_agent.search_news")
    def test_no_articles_returns_neutral(self, mock_search):
        mock_search.return_value = []
        result = analyze("EMPTY.NS")

        assert result.score == 50.0
        assert result.verdict == "Neutral"
        assert "No news articles found" in result.explanation

    @patch("agents.sentiment_agent.search_news")
    def test_ticker_normalized(self, mock_search):
        mock_search.return_value = [NEUTRAL_ARTICLE]
        result = analyze("  reliance.ns  ")
        assert result.ticker == "RELIANCE.NS"

    @patch("agents.sentiment_agent.search_news")
    def test_explanation_contains_key_info(self, mock_search):
        mock_search.return_value = [POSITIVE_ARTICLE, NEGATIVE_ARTICLE, NEUTRAL_ARTICLE]
        result = analyze("TATAMOTORS.NS")

        assert "Sentiment Analysis" in result.explanation
        assert "Verdict" in result.explanation
        assert "/100" in result.explanation
        assert "Articles analyzed" in result.explanation

    @patch("agents.sentiment_agent.search_news")
    def test_company_name_forwarded(self, mock_search):
        mock_search.return_value = [NEUTRAL_ARTICLE]
        analyze("TATAMOTORS.NS", company_name="Tata Motors")
        mock_search.assert_called_once_with("TATAMOTORS.NS", company_name="Tata Motors", max_results=10)

    @patch("agents.sentiment_agent.search_news")
    def test_articles_stored_in_result(self, mock_search):
        articles = [POSITIVE_ARTICLE, NEGATIVE_ARTICLE]
        mock_search.return_value = articles
        result = analyze("TATAMOTORS.NS")
        assert len(result.articles) == 2

    @patch("agents.sentiment_agent.search_news")
    def test_search_error_propagates(self, mock_search):
        from data_sources.duckduckgo_search import DuckDuckGoSearchError

        mock_search.side_effect = DuckDuckGoSearchError("rate limited")
        with pytest.raises(DuckDuckGoSearchError):
            analyze("TATAMOTORS.NS")


class TestLLMNarrative:
    @patch("agents.sentiment_agent.llm_generate", return_value=None)
    @patch("agents.sentiment_agent.search_news")
    def test_no_narrative_when_llm_disabled(self, mock_search, mock_llm):
        mock_search.return_value = [POSITIVE_ARTICLE, NEGATIVE_ARTICLE]
        result = analyze("TATAMOTORS.NS")
        assert "AI Narrative" not in result.explanation
        assert "Sentiment Analysis" in result.explanation

    @patch(
        "agents.sentiment_agent.llm_generate",
        return_value="Market sentiment is cautiously optimistic.",
    )
    @patch("agents.sentiment_agent.search_news")
    def test_narrative_appended_when_llm_returns_text(self, mock_search, mock_llm):
        mock_search.return_value = [POSITIVE_ARTICLE, NEGATIVE_ARTICLE]
        result = analyze("TATAMOTORS.NS")
        assert "AI Narrative:" in result.explanation
        assert "cautiously optimistic" in result.explanation
        assert "Sentiment Analysis" in result.explanation

    @patch(
        "agents.sentiment_agent.llm_generate",
        return_value="Sentiment narrative.",
    )
    @patch("agents.sentiment_agent.search_news")
    def test_llm_prompt_contains_ticker(self, mock_search, mock_llm):
        mock_search.return_value = [POSITIVE_ARTICLE]
        analyze("TATAMOTORS.NS")
        prompt_arg = mock_llm.call_args[0][0]
        assert "TATAMOTORS.NS" in prompt_arg

    @patch(
        "agents.sentiment_agent.llm_generate",
        return_value="Headlines narrative.",
    )
    @patch("agents.sentiment_agent.search_news")
    def test_llm_prompt_contains_headlines(self, mock_search, mock_llm):
        mock_search.return_value = [POSITIVE_ARTICLE]
        analyze("TATAMOTORS.NS")
        prompt_arg = mock_llm.call_args[0][0]
        assert "sales surge" in prompt_arg
