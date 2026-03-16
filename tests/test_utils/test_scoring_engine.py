import pytest

from utils.scoring_engine import (
    analyze_and_recommend,
    compute_final_score,
    get_recommendation,
)


class TestComputeFinalScore:
    def test_default_weights(self):
        score = compute_final_score(80.0, 70.0, 60.0)
        expected = 80 * 0.4 + 70 * 0.4 + 60 * 0.2
        assert score == pytest.approx(expected)

    def test_custom_weights(self):
        weights = {"fundamental": 0.5, "technical": 0.3, "sentiment": 0.2}
        score = compute_final_score(80.0, 70.0, 60.0, weights=weights)
        expected = 80 * 0.5 + 70 * 0.3 + 60 * 0.2
        assert score == pytest.approx(expected)

    def test_all_zeros(self):
        assert compute_final_score(0.0, 0.0, 0.0) == 0.0

    def test_all_hundred(self):
        assert compute_final_score(100.0, 100.0, 100.0) == 100.0

    def test_all_fifty(self):
        assert compute_final_score(50.0, 50.0, 50.0) == 50.0

    def test_clamped_to_100(self):
        score = compute_final_score(150.0, 150.0, 150.0)
        assert score == 100.0

    def test_clamped_to_0(self):
        score = compute_final_score(-50.0, -50.0, -50.0)
        assert score == 0.0

    def test_heavy_fundamental_bias(self):
        weights = {"fundamental": 1.0, "technical": 0.0, "sentiment": 0.0}
        score = compute_final_score(90.0, 10.0, 10.0, weights=weights)
        assert score == pytest.approx(90.0)


class TestGetRecommendation:
    def test_strong_buy(self):
        assert get_recommendation(85.0) == "Strong Buy"

    def test_buy(self):
        assert get_recommendation(65.0) == "Buy"

    def test_hold(self):
        assert get_recommendation(50.0) == "Hold"

    def test_avoid(self):
        assert get_recommendation(30.0) == "Avoid"

    def test_boundary_80(self):
        assert get_recommendation(80.0) == "Strong Buy"

    def test_boundary_60(self):
        assert get_recommendation(60.0) == "Buy"

    def test_boundary_40(self):
        assert get_recommendation(40.0) == "Hold"

    def test_zero(self):
        assert get_recommendation(0.0) == "Avoid"

    def test_custom_thresholds(self):
        thresholds = [(90, "Must Buy"), (50, "Consider"), (0, "Skip")]
        assert get_recommendation(95.0, thresholds=thresholds) == "Must Buy"
        assert get_recommendation(60.0, thresholds=thresholds) == "Consider"
        assert get_recommendation(30.0, thresholds=thresholds) == "Skip"


class TestAnalyzeAndRecommend:
    def test_strong_buy_scenario(self):
        score, rec = analyze_and_recommend(90.0, 85.0, 80.0)
        assert score >= 80
        assert rec == "Strong Buy"

    def test_avoid_scenario(self):
        score, rec = analyze_and_recommend(20.0, 15.0, 25.0)
        assert score < 40
        assert rec == "Avoid"

    def test_hold_scenario(self):
        score, rec = analyze_and_recommend(50.0, 50.0, 50.0)
        assert score == pytest.approx(50.0)
        assert rec == "Hold"

    def test_returns_tuple(self):
        result = analyze_and_recommend(70.0, 60.0, 50.0)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], str)
