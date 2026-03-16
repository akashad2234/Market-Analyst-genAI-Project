# Developer Guide

## Getting Started

### Prerequisites

- Python 3.11 or later
- Git
- (Optional) Docker and Docker Compose

### Setup

```bash
git clone <repo-url>
cd Market-Analyst-genAI-Project

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

make install
```

### Configuration

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY (required)
```

All configuration is centralised in `utils/config.py`. See `.env.example` for the full list of 17 configurable settings.

### Running Locally

```bash
# Terminal 1: API server
make dev-api    # http://localhost:8000

# Terminal 2: Streamlit UI
make dev-ui     # http://localhost:8501
```

---

## Project Layout

```
agents/              Analyst agents (fundamental, technical, sentiment, master)
backend/             FastAPI server, routes, middleware, Pydantic schemas
data_sources/        Yahoo Finance and DuckDuckGo integrations
langgraph/           LangGraph orchestration pipeline
ui/                  Streamlit frontend
utils/               Config, logging, metrics, scoring, portfolio analysis
tests/               Mirrors source layout
doc/                 Architecture, API reference, deployment, guides
```

---

## Development Workflow

### Running Tests

```bash
make test         # all tests, verbose output
make test-cov     # with coverage report (terminal + HTML)
```

Tests use mocked external calls (Yahoo Finance, DuckDuckGo). No real API calls are made.

### Code Quality

```bash
make lint         # ruff check
make format       # ruff format
make type-check   # mypy
make quality      # lint + type-check + test (all in one)
```

### Adding a New Module

1. Create the module in the appropriate directory.
2. Add loguru logging to all public functions.
3. Create a corresponding test file in `tests/` mirroring the path.
4. Mock all external calls in tests.
5. Run `make quality` before committing.

---

## Key Architecture Decisions

### Sequential Agent Execution

Agents run sequentially (not in parallel) for reliability. If one agent fails, the pipeline continues with a neutral score (50/100) for that agent. This is implemented in `langgraph/graph_builder.py`.

### Keyword-Based Sentiment (Not LLM)

Sentiment classification uses keyword matching (30+ positive, 30+ negative keywords) rather than LLM calls. This avoids API costs and rate limits during development. LLM prompt templates are ready in `utils/prompt_templates.py` for future integration.

### Scoring Engine

All agent scores are 0-100. The final score is a weighted combination:
- Fundamental: 40% (configurable via `FUNDAMENTAL_WEIGHT`)
- Technical: 40% (configurable via `TECHNICAL_WEIGHT`)
- Sentiment: 20% (configurable via `SENTIMENT_WEIGHT`)

Recommendation thresholds are configurable via `SCORING_THRESHOLDS`.

### Configuration via Environment

All settings flow through `utils/config.py`. Components use try/except imports so they remain testable and importable even without a `.env` file.

---

## Testing Conventions

- Every module has tests. Test files mirror source paths (e.g. `agents/fundamental_agent.py` has `tests/test_agents/test_fundamental_agent.py`).
- All external API calls are mocked (Yahoo Finance, DuckDuckGo, Gemini).
- Use `@patch` decorators for mocking.
- Test classes group related tests (e.g. `TestScoreRSI`, `TestAnalyzeStock`).
- Edge cases are tested explicitly (None values, empty data, error propagation).

---

## Logging

- **Library**: Loguru
- **Console**: Coloured output to stderr
- **File**: `dump.log` in project root (10 MB rotation, 7-day retention)
- **Level**: Configurable via `LOG_LEVEL` env var (default: `INFO`)
- **Correlation IDs**: Every API request gets a unique ID in the `X-Request-ID` header

---

## Metrics

In-memory metrics are available at `GET /metrics`. Tracked metrics include:
- `pipeline.started`, `pipeline.completed` (counters)
- `agent.fundamental`, `agent.technical`, `agent.sentiment` (latency + count)
- `pipeline.total` (end-to-end latency)
- Error counts per agent
