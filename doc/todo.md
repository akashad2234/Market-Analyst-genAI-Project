# AI Market Analyst – Build TODO

---

## A. Foundations and Repo Setup ✅

- [x] Define final project name and rename `market-analyst-ai` folder if needed.
- [x] Initialize proper Python env (Poetry or `venv`) and create `requirements.txt` that matches `architecture.md` stack.
- [x] Create initial folder structure from section 11 (`backend`, `agents`, `data_sources`, `langgraph`, `ui`, `utils`, `tests`).
- [x] Add `README.md` with short system overview and how to run backend and UI.
- [x] Configure basic `.env` handling for API keys and secrets.
- [x] Add `.gitignore` for Python project.
- [x] Add `Makefile` with `install`, `dev-api`, `dev-ui`, `test`, `test-cov`, `lint`, `format`, `docker-build` commands (per `rules.md`).
- [x] Add `pyproject.toml` with pytest, ruff, and coverage config.
- [x] Add `utils/config.py` with dotenv loading, required/optional env vars, scoring weights, server settings.
- [x] Add `utils/logger.py` with loguru setup writing to `dump.log` (per `rules.md`).
- [x] Add tests for config and logger modules (8 tests, all passing).

---

## B. Data Layer: Market and News Data ✅

- [x] Implement `data_sources/yahoo_finance.py`:
  - [x] `get_quote()`: current price, company metadata, sector, market cap.
  - [x] `get_historical()`: OHLCV DataFrame with configurable period and interval.
  - [x] `get_financials()`: PE, D/E, ROE, profit margin, revenue growth, beta, 52-week range.
  - [x] Error handling: `YahooFinanceError` for invalid tickers, empty data, and API failures.
  - [x] Loguru logging on every call.
- [x] Implement `data_sources/duckduckgo_search.py`:
  - [x] `search_news()`: search by ticker + optional company name.
  - [x] Normalize results into consistent structure (title, snippet, url, date, source).
  - [x] Rate limiting (1.5s minimum between requests).
  - [x] LRU cache (128 entries) with `clear_cache()` helper.
  - [x] `DuckDuckGoSearchError` for failures.
- [x] Unit tests: 15 yahoo_finance tests + 13 duckduckgo tests, all mocked, no real API calls (28 total).

---

## C. Fundamental Analyst Agent ✅

- [x] Input/output schema: `FundamentalResult` dataclass (ticker, score, verdict, metrics, metric_scores, explanation).
- [x] Implement `agents/fundamental_agent.py`:
  - [x] Calls `get_financials()` from Yahoo Finance data layer.
  - [x] 6 individual metric scorers (PE, D/E, ROE, profit margin, revenue growth, PEG), each 0-100.
  - [x] Weighted composite score (PE 20%, D/E 20%, ROE 20%, margin 15%, growth 15%, PEG 10%).
  - [x] Verdict mapping: Strong (>=75), Moderate (>=55), Weak (>=35), Very Weak (<35).
  - [x] `_build_explanation()` generates human-readable text summary.
  - [x] None/missing values handled gracefully (neutral score 50).
- [x] Created `utils/prompt_templates.py` with LLM prompt templates for fundamental, technical, and sentiment agents.
- [x] Tests: 53 tests for fundamental agent (7 PE, 5 D/E, 5 ROE, 5 margin, 6 growth, 5 PEG, 7 verdict, 5 composite, 7 integration + error), all mocked.

---

## D. Technical Analyst Agent ✅

- [x] Input/output schema: `TechnicalResult` dataclass (ticker, score, verdict, indicators, interpretations, indicator_scores, explanation).
- [x] Implement `agents/technical_agent.py`:
  - [x] `compute_indicators()`: RSI (14), MACD (12/26/9), 50-day SMA, 200-day SMA, volume change % using `ta` library.
  - [x] 4 indicator scorers (RSI, MACD crossover+histogram, MA golden/death cross, volume trend), each 0-100.
  - [x] Weighted composite score (RSI 25%, MACD 25%, Moving Averages 30%, Volume 20%).
  - [x] Verdict mapping: Bullish (>=75), Moderately Bullish (>=60), Neutral (>=40), Moderately Bearish (>=25), Bearish (<25).
  - [x] `_build_explanation()` generates human-readable text summary.
  - [x] None/missing data and short datasets handled gracefully.
  - [x] Fixed edge case: both MAs missing now returns neutral instead of false bearish.
- [x] Tests: 52 tests (8 RSI, 5 MACD, 8 MA, 6 volume, 9 verdict, 4 compute_indicators, 4 compute_scores, 8 integration), all mocked with synthetic OHLCV data.

---

## E. Sentiment Analyst Agent ✅

- [x] Input/output schema: `SentimentResult` dataclass (ticker, score, verdict, positive/negative/neutral counts, articles, explanation).
- [x] Implement `agents/sentiment_agent.py`:
  - [x] Fetches news via DuckDuckGo data layer.
  - [x] Keyword-based sentiment classification (30+ positive keywords, 30+ negative keywords).
  - [x] Per-article scoring with confidence scaling based on keyword hit count.
  - [x] Aggregation: average score + ratio bias, clamped 0-100.
  - [x] Verdict mapping: Positive (>=70), Moderately Positive (>=55), Neutral (>=45), Moderately Negative (>=30), Negative (<30).
  - [x] No news fallback returns neutral 50 with explanation.
- [x] Tests: 28 tests (6 classification, 5 aggregation, 9 verdict, 8 integration), all mocked.

---

## F. Master Agent and LangGraph Flow ✅

- [x] Common contract: all agents return dataclass with `ticker`, `score` (0-100), `verdict`, `explanation` fields.
- [x] Implement `langgraph/graph_builder.py`:
  - [x] `AnalysisState` dataclass carries state through the pipeline.
  - [x] Node functions: `run_fundamental`, `run_technical`, `run_sentiment`, `aggregate_and_recommend`.
  - [x] Each node isolates errors (failed agent = neutral 50, pipeline continues).
  - [x] `run_analysis_graph(ticker)` executes the full pipeline.
- [x] Implement `agents/master_agent.py`:
  - [x] `parse_intent()`: detects single stock, portfolio (comma-separated), comparison ("vs" keyword).
  - [x] `run_analysis(request)`: iterates tickers, calls graph per stock, builds summary.
  - [x] `analyze_query(raw_query)`: end-to-end convenience from raw string to `AnalysisResponse`.
  - [x] `AnalysisRequest`, `StockAnalysis`, `AnalysisResponse` dataclasses.
  - [x] Portfolio summary with best performing and most risky; comparison ranking.
- [x] Tests: 14 graph_builder tests (node success/error, aggregation, full pipeline, partial failure, all-fail) + 16 master_agent tests (intent parsing, routing, end-to-end), all mocked.

---

## G. Recommendation and Scoring Engine ✅

- [x] Implement `utils/scoring_engine.py`:
  - [x] `compute_final_score()`: weighted combination (default 0.4/0.4/0.2), clamped 0-100.
  - [x] `get_recommendation()`: maps score to buckets (Strong Buy >=80, Buy >=60, Hold >=40, Avoid <40).
  - [x] `analyze_and_recommend()`: convenience combining both in one call.
  - [x] Fully parameterizable weights and thresholds.
- [x] Tests: 21 tests (8 score computation, 9 recommendation mapping, 4 combined), all passing.

---

## H. Backend API (FastAPI) ✅

- [x] Implement `backend/main.py`:
  - [x] FastAPI app with title, description, version.
  - [x] CORS middleware (allow all origins for dev).
  - [x] Loguru logging init on startup.
  - [x] `GET /health` endpoint.
- [x] Implement `backend/routes/stock_routes.py`:
  - [x] `POST /analyze_stock`: validates ticker, calls master agent, returns structured response.
  - [x] 404 for empty results, 500 for internal errors.
- [x] Implement `backend/routes/portfolio_routes.py`:
  - [x] `POST /portfolio_analysis`: accepts list of tickers, returns per-stock analysis + summary.
  - [x] `POST /compare_stocks`: accepts stock1/stock2, returns comparison + summary.
- [x] `backend/schemas.py`: Pydantic models for all request/response types (AnalyzeStockRequest, PortfolioAnalysisRequest, CompareStocksRequest, StockAnalysisResponse, etc.).
- [x] Tests: 12 integration tests using FastAPI TestClient with mocked agents (health, success, 404, 422 validation, 500 errors).

---

## I. Streamlit UI ✅

- [x] Implement `ui/streamlit_app.py`:
  - [x] 3 tabs: Stock Analysis, Portfolio Analysis, Compare Stocks.
  - [x] Input controls: text input for single ticker, text area for portfolio, two inputs for comparison.
  - [x] Calls FastAPI endpoints (`/analyze_stock`, `/portfolio_analysis`, `/compare_stocks`).
  - [x] Visual display: `st.metric` for score/recommendation/ticker, `st.progress` bars for each agent score, `st.expander` for portfolio items and errors.
  - [x] Recommendation emoji badges (green/yellow/orange/red).
  - [x] Error handling: connection errors, timeouts, validation warnings, API error details.
  - [x] Spinner during analysis, success/error messages.

---

## J. Portfolio Analyzer Logic ✅

- [x] Implement `utils/portfolio_analyzer.py`:
  - [x] `RiskLevel` enum (Low, Medium, High) and `StockRiskProfile` dataclass.
  - [x] `assess_stock_risk()`: categorises each stock by final score + sub-score analysis (weak fundamentals, bearish technicals, negative sentiment, high analyst divergence).
  - [x] `compute_diversification_score()`: measures portfolio spread via score standard deviation, normalised 0-100.
  - [x] `generate_rebalance_suggestion()`: human-readable rebalance advice based on risk distribution and average score.
  - [x] `analyze_portfolio()`: main entry point producing `PortfolioInsight` (average score, overall risk, best/worst performer, diversification, risk profiles, rebalance text, summary).
- [x] Wired into `agents/master_agent.py`: portfolio queries now produce `PortfolioInsight` attached to `AnalysisResponse.portfolio_insight`.
- [x] Updated `backend/schemas.py` with `StockRiskProfileResponse` and `PortfolioInsightResponse` Pydantic models.
- [x] Updated `backend/routes/portfolio_routes.py` to serialize and return portfolio insights in the API response.
- [x] Updated `ui/streamlit_app.py` Portfolio tab: displays average score, overall risk, best performer, diversification, rebalance advice, and per-stock risk profiles with emoji badges.
- [x] Tests: 33 tests in `test_portfolio_analyzer.py` (10 risk assessment, 7 diversification, 7 rebalance, 9 integration), all passing. 265 total tests across project.

---

## K. Configuration, Security, and Secrets ✅

- [x] Expanded `utils/config.py` with all centralised settings:
  - [x] API keys: `GEMINI_API_KEY` (required).
  - [x] LLM provider/model: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TEMPERATURE` (default: google / gemini-2.0-flash / 0.3).
  - [x] Scoring weights: `FUNDAMENTAL_WEIGHT`, `TECHNICAL_WEIGHT`, `SENTIMENT_WEIGHT` + pre-built `SCORING_WEIGHTS` dict.
  - [x] Scoring thresholds: `SCORING_THRESHOLDS` as env-configurable JSON (default: Strong Buy/Buy/Hold/Avoid).
  - [x] Yahoo Finance: `YAHOO_HISTORY_PERIOD_DAYS`, `YAHOO_HISTORY_INTERVAL`.
  - [x] DuckDuckGo: `DDG_MAX_RESULTS`, `DDG_RATE_LIMIT_SECONDS`, `DDG_CACHE_SIZE`.
  - [x] Server: `API_HOST`, `API_PORT`, `CORS_ORIGINS` (comma-separated list).
  - [x] Logging: `LOG_LEVEL`.
- [x] Wired config into all components:
  - [x] `langgraph/graph_builder.py`: passes `SCORING_WEIGHTS` and `SCORING_THRESHOLDS` to scoring engine.
  - [x] `data_sources/yahoo_finance.py`: defaults `period_days` and `interval` from config.
  - [x] `data_sources/duckduckgo_search.py`: defaults `max_results`, rate limit, and cache size from config.
  - [x] `backend/main.py`: reads `CORS_ORIGINS` from config for CORS middleware.
- [x] Secrets secured: `.env` excluded via `.gitignore`, `.env.example` documents all 16 config options.
- [x] Tests: 21 config tests (2 required keys, 3 scoring weights, 2 thresholds, 4 LLM, 4 data source, 6 server/CORS/logging). 280 total tests passing.

---

## L. Testing and Quality Checks ✅

- [x] `tests/` tree mirrors main package: `test_agents/`, `test_data_sources/`, `test_utils/`, `test_backend/`, `test_langgraph/`.
- [x] Unit tests for all modules:
  - [x] Data sources: 28 tests (15 yahoo_finance + 13 duckduckgo).
  - [x] Agents: 149 tests (53 fundamental + 52 technical + 28 sentiment + 16 master).
  - [x] Scoring engine: 21 tests.
  - [x] Portfolio analyzer: 33 tests.
  - [x] Config: 21 tests.
  - [x] Logger: 2 tests.
- [x] Integration tests: 14 LangGraph graph_builder + 12 FastAPI endpoint tests.
- [x] Coverage: 97% across 1,072 statements (34 misses total). `make test-cov` generates HTML report.
- [x] Ruff linter: all checks pass (import sorting, unused imports, line length enforced at 120 chars).
- [x] Ruff formatter: applied across entire codebase.
- [x] Mypy type checking: 0 errors across 22 source files. Configured in `pyproject.toml`.
- [x] `make quality` command runs lint + type-check + test in one step.
- [x] Total: 280 tests, all passing.

---

## M. Observability and Logging ✅

- [x] Structured logging already present (prior phases) in:
  - [x] Data access layer (`yahoo_finance.py`, `duckduckgo_search.py`).
  - [x] All agents and LangGraph nodes.
  - [x] FastAPI routes.
- [x] **Correlation IDs** (`backend/middleware.py`):
  - [x] `CorrelationIdMiddleware`: generates 12-char hex ID per request (or reads `X-Request-ID` header).
  - [x] Stores ID in `ContextVar` for access anywhere in the request cycle.
  - [x] Logs request start/end with method, path, status code, and latency.
  - [x] Returns `X-Request-ID` in response headers.
- [x] **Metrics collection** (`utils/metrics.py`):
  - [x] Thread-safe `MetricsCollector` with counters, latency records, and error counts.
  - [x] `track()` context manager auto-records latency + increments counter + catches errors.
  - [x] `_LatencyRecord` tracks count, avg/min/max/total milliseconds.
  - [x] `snapshot()` returns point-in-time metrics dict.
- [x] **Metrics wired into pipeline** (`langgraph/graph_builder.py`):
  - [x] Per-agent latency: `agent.fundamental`, `agent.technical`, `agent.sentiment`.
  - [x] Pipeline totals: `pipeline.started`, `pipeline.completed`, `pipeline.total` latency.
  - [x] Error counts per agent on failure.
- [x] **`GET /metrics` endpoint** in `backend/main.py`: returns live counters, latencies, and errors.
- [x] Tests: 13 metrics tests (latency record, collector, context manager, reset) + 4 middleware tests (correlation ID generation, echo, metrics endpoint). 297 total tests passing.

---

## N. Deployment and Operations ✅

- [x] `Dockerfile`: multi-stage build for backend API (Python 3.11-slim, copies source, exposes 8000, runs uvicorn).
- [x] `Dockerfile.ui`: Streamlit container (exposes 8501, headless mode, health check).
- [x] `docker-compose.yml`: orchestrates both services:
  - [x] `api` service: builds from `Dockerfile`, reads `.env`, health check on `/health`, port 8000.
  - [x] `ui` service: builds from `Dockerfile.ui`, depends on healthy API, `API_BASE=http://api:8000`, port 8501.
- [x] `.dockerignore`: excludes .git, tests, docs, logs, IDE files for lean images.
- [x] `ui/streamlit_app.py` updated to read `API_BASE` from environment (Docker override support).
- [x] `doc/deployment.md`: comprehensive deployment guide covering:
  - [x] Full environment variables reference table (17 variables).
  - [x] Option 1: Local development setup.
  - [x] Option 2: Docker Compose (recommended).
  - [x] Option 3: Individual Docker containers.
  - [x] Deployment targets: Render, Railway, VM (with step-by-step).
  - [x] API endpoints reference.
  - [x] Logging and observability info.
- [x] `README.md` updated with Docker section, fixed tech stack (ta, mypy, Docker), updated project structure.

---

## O. Documentation and Alignment with `architecture.md` ✅

- [x] Updated `architecture.md` to reflect actual implementation:
  - [x] Sequential execution (not parallel) with error isolation.
  - [x] Keyword-based sentiment (not LLM classification).
  - [x] Expanded tech stack table (Loguru, metrics, Ruff, Mypy, Docker).
  - [x] Updated folder structure (24 source files, middleware, schemas, metrics, portfolio analyzer).
  - [x] Added "Implemented Beyond Original Spec" section (portfolio risk, observability, Docker).
  - [x] Updated "Future Improvements" with remaining items.
- [x] Created `doc/developer-guide.md`:
  - [x] Setup, prerequisites, running locally.
  - [x] Project layout and development workflow.
  - [x] Key architecture decisions with rationale.
  - [x] Testing conventions, logging, and metrics reference.
- [x] Created `doc/api-reference.md`:
  - [x] All 5 endpoints documented with request/response examples.
  - [x] Error response tables (422, 404, 500).
  - [x] Response headers (X-Request-ID).
  - [x] Pydantic model listing.
- [x] Created `doc/agent-scoring-rules.md`:
  - [x] Detailed scoring logic for all 13 metrics across 3 agents.
  - [x] Verdict mapping tables for each agent.
  - [x] Scoring engine formula and threshold table.
  - [x] Portfolio analyzer rules (risk assessment, diversification, rebalance).
  - [x] Error handling behavior.
- [x] Created `doc/system-overview.md`:
  - [x] PM-friendly system overview with architecture diagram.
  - [x] Three query types explained.
  - [x] Key numbers table (297 tests, 97% coverage, 24 source files, 17 config options).
  - [x] Deployment quick-start.

---

## P. LLM-Powered Narrative Generation ✅

- [x] Added `LLM_ENABLED` config option (default `false`) so LLM is opt-in and preserves free tier.
- [x] Created `utils/llm_client.py`:
  - [x] Uses modern `google.genai` SDK (replaces deprecated `google.generativeai`).
  - [x] Lazy singleton client initialization with API key from config.
  - [x] `generate(prompt)` returns `str | None`: returns text on success, `None` on any failure.
  - [x] Graceful fallback: disabled, SDK missing, API error, or empty response all return `None`.
- [x] Updated `agents/fundamental_agent.py`:
  - [x] Split `_build_explanation` into `_build_rule_explanation` (existing logic) + LLM-enhanced wrapper.
  - [x] When `LLM_ENABLED=true`, appends "AI Narrative" paragraph from Gemini using `FUNDAMENTAL_ANALYSIS_PROMPT`.
  - [x] Falls back to rule-only output if LLM fails or is disabled.
- [x] Updated `agents/technical_agent.py`:
  - [x] Same pattern: rule-based + optional LLM narrative using `TECHNICAL_ANALYSIS_PROMPT`.
- [x] Updated `agents/sentiment_agent.py`:
  - [x] Same pattern: rule-based + optional LLM narrative using `SENTIMENT_ANALYSIS_PROMPT`.
  - [x] Headlines passed to prompt for richer context.
- [x] Updated `requirements.txt`: added `google-genai`, replaced deprecated `google-generativeai`.
- [x] Updated `.env.example` with `LLM_ENABLED` documentation.
- [x] Tests (all mocked, no real API calls):
  - [x] `tests/test_utils/test_llm_client.py`: 10 tests covering generate, disabled, enabled, errors, SDK missing, client creation.
  - [x] `tests/test_agents/test_fundamental_agent.py`: 3 LLM narrative tests.
  - [x] `tests/test_agents/test_technical_agent.py`: 3 LLM narrative tests.
  - [x] `tests/test_agents/test_sentiment_agent.py`: 4 LLM narrative tests (including headline verification).
  - [x] `tests/test_utils/test_config.py`: 4 tests for LLM_ENABLED (true/false/yes/1).
  - [x] Total: 322 tests passing, 0 lint errors, 0 type errors.

---

## Q. SQLite MCP Server & Caching Layer ✅

- [x] Config: added `DB_PATH`, `CACHE_TTL_ANALYSIS` to `utils/config.py`.
- [x] Updated `.gitignore` to exclude `data/` and `*.db` files.
- [x] Added `mcp` to `requirements.txt`.
- [x] Created `utils/database.py`:
  - [x] Thread-safe connection manager with lazy initialization.
  - [x] WAL journal mode + busy timeout for concurrent access.
  - [x] Schema: `analysis_cache`, `analysis_history`, `metrics_snapshot` tables with indexes.
  - [x] CRUD: `cache_get/set/clear/stats`, `history_save/get`, `metrics_save/latest`, `purge_expired_cache`.
- [x] Created `utils/cache.py` (analysis-level, NOT data-source-level):
  - [x] Single `get/set_cached_analysis` pair keyed by ticker.
  - [x] Ticker case-insensitive (uppercased before cache key).
  - [x] Single configurable TTL (`CACHE_TTL_ANALYSIS`, default 15 min).
- [x] Cache integrated at `master_agent.py` level (after scoring, before LLM):
  - [x] Cache key = just the ticker (simple).
  - [x] Cached data = scores, verdicts, recommendation, errors (no explanation/narrative).
  - [x] On cache hit: skip full pipeline (no Yahoo/DDG calls), call LLM for fresh narrative.
  - [x] On cache miss: run full pipeline, cache the scores, return full response.
  - [x] Guarantees at least 1 LLM call per request.
- [x] Data sources (`yahoo_finance.py`, `duckduckgo_search.py`) are cache-free (clean API callers).
- [x] Added `SUMMARY_ANALYSIS_PROMPT` to `utils/prompt_templates.py` for cache-hit narratives.
- [x] Added analysis history saving to API routes:
  - [x] `stock_routes.py`: saves after single-stock analysis.
  - [x] `portfolio_routes.py`: saves per-stock after portfolio and comparison analysis.
  - [x] Failures logged as warnings, never block the response.
- [x] Added API endpoints: `GET /history`, `GET /cache/stats`, `POST /cache/purge`.
- [x] Created `mcp_servers/sqlite_server.py` (FastMCP-based):
  - [x] 12 tools: `get_cached_analysis`, `store_cached_analysis`, `clear_cache`, `get_cache_stats`, `purge_expired`, `get_analysis_history`, `save_analysis`, `save_metrics_snapshot`, `get_latest_metrics`, `list_tables`, `describe_table`, `run_read_query`.
  - [x] Read-only SQL guard: only SELECT queries allowed via `run_read_query`.
  - [x] Cursor MCP config: `.cursor/mcp.json`.
- [x] Updated `.env.example` with database/cache config documentation.
- [x] Tests (51 new, all mocked with in-memory SQLite):
  - [x] `tests/test_utils/test_database.py`: 22 tests (connection, cache CRUD, history, metrics, purge).
  - [x] `tests/test_utils/test_cache.py`: 6 tests (round-trip, case insensitive, overwrite, clear).
  - [x] `tests/test_mcp_servers/test_sqlite_server.py`: 14 tests (all 12 tools + error cases).
  - [x] `tests/test_agents/test_master_agent.py`: 9 new tests (cache helpers, narrative gen, cache integration).
  - [x] Total: 382 tests passing, 0 lint errors.
