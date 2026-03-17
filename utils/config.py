import json
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_env_candidates = [
    _PROJECT_ROOT / ".env",
    _PROJECT_ROOT / "doc" / ".env",
]

_loaded = False
for _candidate in _env_candidates:
    if _candidate.exists():
        load_dotenv(_candidate)
        logger.info("Loaded env from {}", _candidate)
        _loaded = True
        break

if not _loaded:
    logger.warning("No .env file found. Relying on system environment variables.")


def _get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value


def _get_optional(key: str, default: str) -> str:
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = _get_required("GEMINI_API_KEY")

# ---------------------------------------------------------------------------
# LLM Provider / Model
# ---------------------------------------------------------------------------
LLM_ENABLED: bool = _get_optional("LLM_ENABLED", "false").lower() in ("true", "1", "yes")
LLM_PROVIDER: str = _get_optional("LLM_PROVIDER", "google")
LLM_MODEL: str = _get_optional("LLM_MODEL", "gemini-2.0-flash")
LLM_TEMPERATURE: float = float(_get_optional("LLM_TEMPERATURE", "0.3"))

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------
FUNDAMENTAL_WEIGHT: float = float(_get_optional("FUNDAMENTAL_WEIGHT", "0.4"))
TECHNICAL_WEIGHT: float = float(_get_optional("TECHNICAL_WEIGHT", "0.4"))
SENTIMENT_WEIGHT: float = float(_get_optional("SENTIMENT_WEIGHT", "0.2"))

SCORING_WEIGHTS: dict[str, float] = {
    "fundamental": FUNDAMENTAL_WEIGHT,
    "technical": TECHNICAL_WEIGHT,
    "sentiment": SENTIMENT_WEIGHT,
}

# ---------------------------------------------------------------------------
# Scoring thresholds: JSON string like '[[80,"Strong Buy"],[60,"Buy"],[40,"Hold"],[0,"Avoid"]]'
# ---------------------------------------------------------------------------
_raw_thresholds = _get_optional(
    "SCORING_THRESHOLDS",
    '[[80,"Strong Buy"],[60,"Buy"],[40,"Hold"],[0,"Avoid"]]',
)
SCORING_THRESHOLDS: list[tuple[float, str]] = [
    (float(pair[0]), str(pair[1])) for pair in json.loads(_raw_thresholds)
]

# ---------------------------------------------------------------------------
# Data source: Yahoo Finance
# ---------------------------------------------------------------------------
YAHOO_HISTORY_PERIOD_DAYS: int = int(_get_optional("YAHOO_HISTORY_PERIOD_DAYS", "365"))
YAHOO_HISTORY_INTERVAL: str = _get_optional("YAHOO_HISTORY_INTERVAL", "1d")

# ---------------------------------------------------------------------------
# Data source: DuckDuckGo
# ---------------------------------------------------------------------------
DDG_MAX_RESULTS: int = int(_get_optional("DDG_MAX_RESULTS", "10"))
DDG_RATE_LIMIT_SECONDS: float = float(_get_optional("DDG_RATE_LIMIT_SECONDS", "1.5"))
DDG_CACHE_SIZE: int = int(_get_optional("DDG_CACHE_SIZE", "128"))

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
API_HOST: str = _get_optional("API_HOST", "0.0.0.0")
API_PORT: int = int(_get_optional("API_PORT", "8000"))
CORS_ORIGINS: list[str] = _get_optional("CORS_ORIGINS", "*").split(",")

# ---------------------------------------------------------------------------
# Database / Cache
# ---------------------------------------------------------------------------
DB_PATH: str = _get_optional("DB_PATH", str(_PROJECT_ROOT / "data" / "market_analyst.db"))
CACHE_TTL_ANALYSIS: int = int(_get_optional("CACHE_TTL_ANALYSIS", "900"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = _get_optional("LOG_LEVEL", "INFO")
