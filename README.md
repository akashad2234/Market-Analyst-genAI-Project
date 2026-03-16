# AI Market Analyst

A multi-agent AI platform that analyses Indian stocks using **fundamental analysis**, **technical analysis**, and **market sentiment analysis**. A Master Agent (orchestrator) coordinates specialised analyst agents via **LangGraph** and produces actionable investment recommendations.

## Architecture

See [`doc/architecture.md`](doc/architecture.md) for the full system design.

```
User (Streamlit) ─> FastAPI ─> Master Agent (LangGraph)
                                   ├── Fundamental Analyst  (Yahoo Finance)
                                   ├── Technical Analyst    (Yahoo Finance + ta)
                                   └── Sentiment Analyst    (DuckDuckGo + LLM)
                                         │
                                   Aggregation & Scoring ─> Recommendation
```

## Quick Start

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd Market-Analyst-genAI-Project

# Create virtual env
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
make install
```

### 2. Configure secrets

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Run the API server

```bash
make dev-api
# Starts FastAPI on http://localhost:8000
```

### 4. Run the Streamlit UI

```bash
make dev-ui
# Opens Streamlit on http://localhost:8501
```

### 5. Run tests

```bash
make test        # run all tests
make test-cov    # run with coverage report
```

### 6. Lint, format, and type-check

```bash
make lint          # ruff lint
make format        # ruff auto-format
make type-check    # mypy
make quality       # lint + type-check + test (all in one)
```

### 7. Docker deployment

```bash
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

docker compose up -d --build
# API: http://localhost:8000
# UI:  http://localhost:8501
```

See [`doc/deployment.md`](doc/deployment.md) for full deployment options (Render, Railway, VM).

## Project Structure

```
Market-Analyst-genAI-Project/
├── backend/            # FastAPI server, routes, middleware, schemas
│   ├── main.py
│   ├── middleware.py   # Correlation ID middleware
│   ├── schemas.py      # Pydantic request/response models
│   └── routes/
├── agents/             # Analyst agents (fundamental, technical, sentiment, master)
├── data_sources/       # Yahoo Finance and DuckDuckGo integrations
├── langgraph/          # LangGraph orchestration graph
├── ui/                 # Streamlit frontend
├── utils/              # Config, logging, scoring engine, metrics, portfolio analyzer
├── tests/              # Mirrors source layout (297 tests)
├── doc/                # Architecture, deployment, todo, rules
├── Dockerfile          # Backend API container
├── Dockerfile.ui       # Streamlit UI container
├── docker-compose.yml  # Run API + UI together
├── requirements.txt
├── Makefile
└── .env.example
```

## Tech Stack

| Layer           | Technology             |
|-----------------|------------------------|
| UI              | Streamlit              |
| API             | FastAPI                |
| Agent Framework | LangGraph              |
| LLM             | Google Gemini          |
| Market Data     | Yahoo Finance          |
| Web Search      | DuckDuckGo             |
| Data Processing | Pandas, ta             |
| Logging         | Loguru                 |
| Observability   | Custom metrics, correlation IDs |
| Testing         | Pytest (297 tests, 97% coverage) |
| Quality         | Ruff, Mypy             |
| Deployment      | Docker, Docker Compose |
