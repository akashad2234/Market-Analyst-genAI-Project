import os
from importlib import reload
from unittest.mock import patch

import pytest

_BASE_ENV = {"GEMINI_API_KEY": "test-key-123"}


def _reload_config(**extra_env):
    env = {**_BASE_ENV, **extra_env}
    with patch.dict(os.environ, env, clear=True):
        import utils.config as cfg

        reload(cfg)
        return cfg


class TestRequiredKeys:
    def test_gemini_api_key_loaded(self):
        cfg = _reload_config()
        assert cfg.GEMINI_API_KEY == "test-key-123"

    def test_missing_gemini_key_raises(self):
        env = os.environ.copy()
        env.pop("GEMINI_API_KEY", None)
        with patch.dict(os.environ, env, clear=True), patch(
            "dotenv.load_dotenv", return_value=None
        ):
            import utils.config as cfg

            with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
                reload(cfg)


class TestScoringWeights:
    def test_default_scoring_weights(self):
        cfg = _reload_config()
        assert cfg.FUNDAMENTAL_WEIGHT == pytest.approx(0.4)
        assert cfg.TECHNICAL_WEIGHT == pytest.approx(0.4)
        assert cfg.SENTIMENT_WEIGHT == pytest.approx(0.2)

    def test_custom_scoring_weights(self):
        cfg = _reload_config(
            FUNDAMENTAL_WEIGHT="0.5",
            TECHNICAL_WEIGHT="0.3",
            SENTIMENT_WEIGHT="0.2",
        )
        assert cfg.FUNDAMENTAL_WEIGHT == pytest.approx(0.5)
        assert cfg.TECHNICAL_WEIGHT == pytest.approx(0.3)
        assert cfg.SCORING_WEIGHTS["fundamental"] == pytest.approx(0.5)

    def test_scoring_weights_dict_matches_individual(self):
        cfg = _reload_config()
        assert cfg.SCORING_WEIGHTS["fundamental"] == cfg.FUNDAMENTAL_WEIGHT
        assert cfg.SCORING_WEIGHTS["technical"] == cfg.TECHNICAL_WEIGHT
        assert cfg.SCORING_WEIGHTS["sentiment"] == cfg.SENTIMENT_WEIGHT


class TestScoringThresholds:
    def test_default_thresholds(self):
        cfg = _reload_config()
        assert len(cfg.SCORING_THRESHOLDS) == 4
        assert cfg.SCORING_THRESHOLDS[0] == (80.0, "Strong Buy")
        assert cfg.SCORING_THRESHOLDS[-1] == (0.0, "Avoid")

    def test_custom_thresholds(self):
        custom = '[[90,"Strong Buy"],[70,"Buy"],[50,"Hold"],[0,"Sell"]]'
        cfg = _reload_config(SCORING_THRESHOLDS=custom)
        assert cfg.SCORING_THRESHOLDS[0] == (90.0, "Strong Buy")
        assert cfg.SCORING_THRESHOLDS[-1] == (0.0, "Sell")
        assert len(cfg.SCORING_THRESHOLDS) == 4


class TestLLMSettings:
    def test_llm_disabled_by_default(self):
        cfg = _reload_config()
        assert cfg.LLM_ENABLED is False

    def test_llm_enabled_true(self):
        cfg = _reload_config(LLM_ENABLED="true")
        assert cfg.LLM_ENABLED is True

    def test_llm_enabled_yes(self):
        cfg = _reload_config(LLM_ENABLED="yes")
        assert cfg.LLM_ENABLED is True

    def test_llm_enabled_one(self):
        cfg = _reload_config(LLM_ENABLED="1")
        assert cfg.LLM_ENABLED is True

    def test_llm_enabled_false_string(self):
        cfg = _reload_config(LLM_ENABLED="false")
        assert cfg.LLM_ENABLED is False

    def test_default_llm_provider(self):
        cfg = _reload_config()
        assert cfg.LLM_PROVIDER == "google"

    def test_default_llm_model(self):
        cfg = _reload_config()
        assert cfg.LLM_MODEL == "gemini-2.0-flash"

    def test_default_llm_temperature(self):
        cfg = _reload_config()
        assert cfg.LLM_TEMPERATURE == pytest.approx(0.3)

    def test_custom_llm_settings(self):
        cfg = _reload_config(
            LLM_PROVIDER="openai",
            LLM_MODEL="gpt-4o",
            LLM_TEMPERATURE="0.7",
        )
        assert cfg.LLM_PROVIDER == "openai"
        assert cfg.LLM_MODEL == "gpt-4o"
        assert cfg.LLM_TEMPERATURE == pytest.approx(0.7)


class TestDataSourceSettings:
    def test_default_yahoo_settings(self):
        cfg = _reload_config()
        assert cfg.YAHOO_HISTORY_PERIOD_DAYS == 365
        assert cfg.YAHOO_HISTORY_INTERVAL == "1d"

    def test_custom_yahoo_settings(self):
        cfg = _reload_config(YAHOO_HISTORY_PERIOD_DAYS="180", YAHOO_HISTORY_INTERVAL="1wk")
        assert cfg.YAHOO_HISTORY_PERIOD_DAYS == 180
        assert cfg.YAHOO_HISTORY_INTERVAL == "1wk"

    def test_default_ddg_settings(self):
        cfg = _reload_config()
        assert cfg.DDG_MAX_RESULTS == 10
        assert cfg.DDG_RATE_LIMIT_SECONDS == pytest.approx(1.5)
        assert cfg.DDG_CACHE_SIZE == 128

    def test_custom_ddg_settings(self):
        cfg = _reload_config(
            DDG_MAX_RESULTS="20",
            DDG_RATE_LIMIT_SECONDS="2.0",
            DDG_CACHE_SIZE="256",
        )
        assert cfg.DDG_MAX_RESULTS == 20
        assert cfg.DDG_RATE_LIMIT_SECONDS == pytest.approx(2.0)
        assert cfg.DDG_CACHE_SIZE == 256


class TestServerSettings:
    def test_default_server_settings(self):
        cfg = _reload_config()
        assert cfg.API_HOST == "0.0.0.0"
        assert cfg.API_PORT == 8000

    def test_custom_server_settings(self):
        cfg = _reload_config(API_HOST="127.0.0.1", API_PORT="9000")
        assert cfg.API_HOST == "127.0.0.1"
        assert cfg.API_PORT == 9000

    def test_default_cors_origins(self):
        cfg = _reload_config()
        assert cfg.CORS_ORIGINS == ["*"]

    def test_custom_cors_origins(self):
        cfg = _reload_config(CORS_ORIGINS="http://localhost:3000,http://localhost:8501")
        assert cfg.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8501"]

    def test_default_log_level(self):
        cfg = _reload_config()
        assert cfg.LOG_LEVEL == "INFO"

    def test_custom_log_level(self):
        cfg = _reload_config(LOG_LEVEL="DEBUG")
        assert cfg.LOG_LEVEL == "DEBUG"
