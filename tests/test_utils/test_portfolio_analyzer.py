
from utils.portfolio_analyzer import (
    RiskLevel,
    StockRiskProfile,
    _StockInput,
    analyze_portfolio,
    assess_stock_risk,
    compute_diversification_score,
    generate_rebalance_suggestion,
)

# =========================================================================
# assess_stock_risk
# =========================================================================


class TestAssessStockRisk:
    def test_low_risk_all_scores_high(self):
        profile = assess_stock_risk("INFY.NS", 80.0, 85.0, 78.0, 72.0)
        assert profile.risk_level == RiskLevel.LOW
        assert profile.risk_factors == []

    def test_high_risk_low_final_score(self):
        profile = assess_stock_risk("M&M.NS", 30.0, 35.0, 25.0, 30.0)
        assert profile.risk_level == RiskLevel.HIGH
        assert "Bearish technicals" in profile.risk_factors

    def test_high_risk_multiple_factors(self):
        profile = assess_stock_risk("BAD.NS", 55.0, 30.0, 35.0, 60.0)
        assert profile.risk_level == RiskLevel.HIGH
        assert len(profile.risk_factors) >= 2

    def test_medium_risk_mixed_scores(self):
        profile = assess_stock_risk("MID.NS", 55.0, 60.0, 55.0, 50.0)
        assert profile.risk_level == RiskLevel.MEDIUM

    def test_none_final_score_defaults_neutral(self):
        profile = assess_stock_risk("UNKNOWN.NS", None, None, None, None)
        assert profile.risk_level == RiskLevel.MEDIUM

    def test_weak_fundamentals_detected(self):
        profile = assess_stock_risk("WEAK.NS", 60.0, 30.0, 70.0, 65.0)
        assert "Weak fundamentals" in profile.risk_factors

    def test_negative_sentiment_detected(self):
        profile = assess_stock_risk("NEG.NS", 55.0, 70.0, 60.0, 25.0)
        assert "Negative sentiment" in profile.risk_factors

    def test_high_divergence_detected(self):
        profile = assess_stock_risk("DIV.NS", 60.0, 90.0, 40.0, 60.0)
        assert "High divergence between analysts" in profile.risk_factors

    def test_no_divergence_when_scores_close(self):
        profile = assess_stock_risk("CLOSE.NS", 70.0, 72.0, 68.0, 70.0)
        assert "High divergence between analysts" not in profile.risk_factors

    def test_divergence_needs_at_least_two_sub_scores(self):
        profile = assess_stock_risk("ONE.NS", 60.0, 90.0, None, None)
        assert "High divergence between analysts" not in profile.risk_factors


# =========================================================================
# compute_diversification_score
# =========================================================================


class TestComputeDiversificationScore:
    def test_single_stock_returns_zero(self):
        assert compute_diversification_score([70.0]) == 0.0

    def test_empty_list_returns_zero(self):
        assert compute_diversification_score([]) == 0.0

    def test_identical_scores_returns_zero(self):
        assert compute_diversification_score([60.0, 60.0, 60.0]) == 0.0

    def test_moderate_spread(self):
        score = compute_diversification_score([40.0, 60.0, 80.0])
        assert 0 < score < 100

    def test_wide_spread_higher_than_narrow(self):
        narrow = compute_diversification_score([48.0, 50.0, 52.0])
        wide = compute_diversification_score([20.0, 50.0, 80.0])
        assert wide > narrow

    def test_extreme_spread_caps_at_100(self):
        score = compute_diversification_score([0.0, 100.0])
        assert score <= 100.0

    def test_two_stocks_moderate(self):
        score = compute_diversification_score([30.0, 70.0])
        assert score > 0


# =========================================================================
# generate_rebalance_suggestion
# =========================================================================


class TestGenerateRebalanceSuggestion:
    def test_empty_portfolio(self):
        result = generate_rebalance_suggestion([], 0.0)
        assert "No holdings" in result

    def test_all_low_risk(self):
        profiles = [
            StockRiskProfile("A", RiskLevel.LOW),
            StockRiskProfile("B", RiskLevel.LOW),
        ]
        result = generate_rebalance_suggestion(profiles, 80.0)
        assert "defensively positioned" in result
        assert "strong" in result.lower()

    def test_majority_high_risk(self):
        profiles = [
            StockRiskProfile("A", RiskLevel.HIGH),
            StockRiskProfile("B", RiskLevel.HIGH),
            StockRiskProfile("C", RiskLevel.LOW),
        ]
        result = generate_rebalance_suggestion(profiles, 35.0)
        assert "heavily weighted" in result.lower() or "high risk" in result.lower()

    def test_some_high_risk(self):
        profiles = [
            StockRiskProfile("A", RiskLevel.HIGH, ["Weak fundamentals"]),
            StockRiskProfile("B", RiskLevel.LOW),
            StockRiskProfile("C", RiskLevel.MEDIUM),
        ]
        result = generate_rebalance_suggestion(profiles, 55.0)
        assert "A" in result

    def test_moderate_health(self):
        profiles = [StockRiskProfile("X", RiskLevel.MEDIUM)]
        result = generate_rebalance_suggestion(profiles, 55.0)
        assert "moderate" in result.lower()

    def test_weak_health(self):
        profiles = [StockRiskProfile("X", RiskLevel.HIGH)]
        result = generate_rebalance_suggestion(profiles, 30.0)
        assert "weak" in result.lower() or "rebalanc" in result.lower()

    def test_no_low_risk_holdings(self):
        profiles = [
            StockRiskProfile("A", RiskLevel.MEDIUM),
            StockRiskProfile("B", RiskLevel.HIGH),
        ]
        result = generate_rebalance_suggestion(profiles, 50.0)
        assert "defensive" in result.lower()


# =========================================================================
# analyze_portfolio (integration)
# =========================================================================


class TestAnalyzePortfolio:
    def test_empty_portfolio(self):
        insight = analyze_portfolio([])
        assert insight.average_score == 0.0
        assert insight.overall_risk == RiskLevel.HIGH
        assert insight.best_performer == "N/A"
        assert "Empty portfolio" in insight.summary

    def test_single_stock(self):
        stocks = [_StockInput("RELIANCE.NS", 75.0, 80.0, 70.0, 65.0)]
        insight = analyze_portfolio(stocks)
        assert insight.average_score == 75.0
        assert insight.best_performer == "RELIANCE.NS"
        assert insight.worst_performer == "RELIANCE.NS"
        assert insight.diversification_score == 0.0

    def test_mixed_portfolio(self):
        stocks = [
            _StockInput("INFY.NS", 82.0, 85.0, 80.0, 78.0),
            _StockInput("TATAMOTORS.NS", 55.0, 50.0, 60.0, 55.0),
            _StockInput("M&M.NS", 35.0, 30.0, 35.0, 40.0),
        ]
        insight = analyze_portfolio(stocks)
        assert insight.best_performer == "INFY.NS"
        assert insight.worst_performer == "M&M.NS"
        assert len(insight.risk_profiles) == 3
        assert insight.diversification_score > 0

    def test_all_strong_stocks(self):
        stocks = [
            _StockInput("A.NS", 85.0, 90.0, 80.0, 82.0),
            _StockInput("B.NS", 78.0, 75.0, 80.0, 78.0),
        ]
        insight = analyze_portfolio(stocks)
        assert insight.overall_risk == RiskLevel.LOW
        assert "strong" in insight.rebalance_suggestion.lower()

    def test_all_weak_stocks(self):
        stocks = [
            _StockInput("X.NS", 25.0, 20.0, 25.0, 30.0),
            _StockInput("Y.NS", 30.0, 28.0, 32.0, 25.0),
        ]
        insight = analyze_portfolio(stocks)
        assert insight.overall_risk == RiskLevel.HIGH
        assert "weak" in insight.rebalance_suggestion.lower() or "rebalanc" in insight.rebalance_suggestion.lower()

    def test_none_scores_handled(self):
        stocks = [
            _StockInput("A.NS", None, None, None, None),
            _StockInput("B.NS", 70.0, 65.0, 72.0, 68.0),
        ]
        insight = analyze_portfolio(stocks)
        assert insight.average_score == 60.0
        assert len(insight.risk_profiles) == 2

    def test_summary_format(self):
        stocks = [
            _StockInput("A.NS", 70.0, 75.0, 65.0, 60.0),
            _StockInput("B.NS", 55.0, 50.0, 60.0, 55.0),
        ]
        insight = analyze_portfolio(stocks)
        assert "Portfolio Summary" in insight.summary
        assert "Average Score" in insight.summary
        assert "Overall Risk" in insight.summary
        assert "Best Performing" in insight.summary
        assert "Most Risky" in insight.summary
        assert "Recommendation" in insight.summary

    def test_risk_profiles_populated(self):
        stocks = [
            _StockInput("GOOD.NS", 80.0, 85.0, 75.0, 70.0),
            _StockInput("BAD.NS", 30.0, 25.0, 30.0, 35.0),
        ]
        insight = analyze_portfolio(stocks)
        tickers = {rp.ticker for rp in insight.risk_profiles}
        assert "GOOD.NS" in tickers
        assert "BAD.NS" in tickers

        bad_profile = next(rp for rp in insight.risk_profiles if rp.ticker == "BAD.NS")
        assert bad_profile.risk_level == RiskLevel.HIGH
        assert len(bad_profile.risk_factors) > 0

    def test_large_portfolio(self):
        stocks = [_StockInput(f"S{i}.NS", 50.0 + i * 5, 50.0, 50.0, 50.0) for i in range(10)]
        insight = analyze_portfolio(stocks)
        assert len(insight.risk_profiles) == 10
        assert insight.diversification_score > 0
