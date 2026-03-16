# AI Market Analyst: System Overview

## What It Does

An AI-powered platform that analyses Indian stocks and provides investment recommendations. Users submit a stock ticker, a portfolio, or a comparison request, and the system returns a scored recommendation backed by three types of analysis.

## How It Works

```
User Input                    Analysis Pipeline                   Output
-----------                   -----------------                   ------

"RELIANCE.NS"          -->    Fundamental Agent    -->    Score: 72/100
                              Technical Agent      -->    Recommendation: Buy
                              Sentiment Agent      -->    Risk Level: Low
                                    |
                              Scoring Engine
                                    |
                              Final Recommendation
```

### Three Analyst Agents

| Agent | What It Analyses | Data Source | Key Metrics |
|---|---|---|---|
| Fundamental | Company financial health | Yahoo Finance | PE, D/E, ROE, margins, growth, PEG |
| Technical | Price trends and momentum | Yahoo Finance (historical) | RSI, MACD, moving averages, volume |
| Sentiment | Market news sentiment | DuckDuckGo | News headlines, keyword sentiment |

### Scoring System

Each agent produces a score from 0 to 100. These are combined with configurable weights:

- Fundamental: 40%
- Technical: 40%
- Sentiment: 20%

The final score maps to a recommendation: **Strong Buy** (80+), **Buy** (60+), **Hold** (40+), or **Avoid** (below 40).

## Three Query Types

| Type | Example Input | What You Get |
|---|---|---|
| Single Stock | `RELIANCE.NS` | Full analysis with scores, verdicts, and recommendation |
| Portfolio | `TATAMOTORS.NS, INFY.NS, M&M.NS` | Per-stock analysis + portfolio risk profile, diversification score, rebalance advice |
| Comparison | `TATAMOTORS.NS vs M&M.NS` | Side-by-side analysis with ranking |

## Architecture

```
Streamlit UI  -->  FastAPI API  -->  Master Agent  -->  3 Analyst Agents
                                                              |
                                                    Scoring Engine
                                                              |
                                                    Recommendation
```

- **Frontend**: Streamlit with 3 tabs (stock, portfolio, comparison)
- **Backend**: FastAPI with 5 endpoints, correlation IDs, live metrics
- **Pipeline**: LangGraph sequential execution with per-agent error isolation
- **Data**: Yahoo Finance (financials + OHLCV) + DuckDuckGo (news)

## Key Numbers

| Metric | Value |
|---|---|
| Total tests | 297 |
| Code coverage | 97% |
| Source files | 24 |
| Config options | 17 (all env-configurable) |
| API endpoints | 5 |
| Agent metrics scored | 13 (6 fundamental + 4 technical + 3 sentiment) |

## Deployment

Available as Docker Compose (recommended), individual containers, or local Python. See `doc/deployment.md` for full instructions.

```bash
cp .env.example .env   # Set GEMINI_API_KEY
docker compose up -d   # API on :8000, UI on :8501
```
