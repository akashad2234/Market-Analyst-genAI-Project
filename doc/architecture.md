You are essentially building an **AI Market Analyst Platform** with **multi-agent collaboration**. Since you want to give this architecture to another agent or developer, the design should be **clear, modular, and production-ready**.

Below is a **high-level architecture** you can directly give to your building agent.

---

# AI Market Analyst – High Level Architecture

## 1. System Overview

The system is a **Multi-Agent AI Financial Analyst** that analyzes Indian stocks using:

* **Fundamental Analysis**
* **Technical Analysis**
* **Market Sentiment Analysis**

A **Master Agent (Orchestrator)** coordinates these agents using **LangGraph** and aggregates their results to produce a final recommendation.

Data sources include:

* **Yahoo Finance API** → Stock data
* **DuckDuckGo Search** → News & sentiment signals

Users interact through:

* **Streamlit UI**
* **FastAPI backend**

---

# 2. High Level Architecture Diagram (Conceptual)

```
                +----------------------+
                |      Streamlit UI    |
                | (User Stock Queries) |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |      FastAPI API     |
                |  /analyze_stock      |
                |  /portfolio_analysis |
                +----------+-----------+
                           |
                           v
                 +--------------------+
                 |   Master Agent     |
                 | (LangGraph Router) |
                 +----+-----+----+----+
                      |     |    |
       ----------------     |     ----------------
       |                    |                    |
       v                    v                    v

+--------------+   +----------------+   +----------------+
| Fundamental  |   | Technical      |   | Sentiment      |
| Analyst      |   | Analyst        |   | Analyst        |
+--------------+   +----------------+   +----------------+
| Financials   |   | Indicators     |   | News Search    |
| PE Ratio     |   | RSI            |   | Social Sentiment|
| Revenue      |   | Moving Avg     |   | Market Mood    |
+--------------+   +----------------+   +----------------+
       |                    |                    |
       ------------------------------------------
                           |
                           v
                +-----------------------+
                | Aggregation Engine    |
                | Final Investment View |
                +-----------+-----------+
                            |
                            v
                    Streamlit Dashboard
```

---

# 3. Core Components

## 3.1 Frontend Layer

### Streamlit UI

User can ask queries like:

* How is Reliance doing?
* How is my portfolio doing?
* Compare Tata Motors vs M&M

Features:

Dashboard sections

* Stock Overview
* Portfolio Performance
* Buy/Sell Signals
* News Sentiment

Example UI inputs

```
Stock Ticker: RELIANCE.NS

Portfolio:
- TATAMOTORS.NS
- M&M.NS
- INFY.NS

Comparison:
TATAMOTORS.NS vs M&M.NS
```

---

# 4. Backend Layer

## FastAPI Server

Handles API calls.

Endpoints:

### Stock Analysis

```
POST /analyze_stock
{
 "ticker": "RELIANCE.NS"
}
```

### Portfolio Analysis

```
POST /portfolio_analysis
{
 "stocks": ["TATAMOTORS.NS","M&M.NS","INFY.NS"]
}
```

### Compare Stocks

```
POST /compare_stocks
{
 "stock1": "TATAMOTORS.NS",
 "stock2": "M&M.NS"
}
```

FastAPI sends request to **LangGraph Master Agent**.

---

# 5. Multi Agent System (LangGraph)

The system contains **4 main agents**.

## 5.1 Master Agent (Orchestrator)

Responsibilities:

* Understand user query (single stock, portfolio, comparison)
* Decide which agents to call
* Execute them **sequentially** (for reliability, with per-agent error isolation)
* Aggregate outputs via weighted scoring engine
* Generate final recommendation

Example Flow:

```
User Query → Master Agent

Step 1: Parse Intent
Step 2: Call Agents
        Fundamental
        Technical
        Sentiment

Step 3: Collect Results
Step 4: Generate Final Recommendation
```

Output example:

```
Stock: Tata Motors

Fundamental Score: Strong
Technical Score: Bullish
Sentiment Score: Positive

Final Recommendation:
Moderate Buy
```

---

# 6. Agents Design

---

# 6.1 Fundamental Analyst Agent

Purpose:

Analyze **company financial health**

Data Source:

* Yahoo Finance

Metrics:

* Revenue growth
* Profit margin
* PE Ratio
* Debt to equity
* ROE
* Market Cap

Example Output

```
Fundamental Analysis

PE Ratio: 18 (Industry Avg: 22)
Revenue Growth: 14%
Debt to Equity: 0.45

Verdict:
Strong Fundamentals
```

---

# 6.2 Technical Analyst Agent

Purpose:

Analyze **price trends and momentum**

Data Source:

* Yahoo Finance Historical Data

Indicators:

* RSI
* MACD
* 50 Day Moving Average
* 200 Day Moving Average
* Volume Trend

Example Output

```
Technical Analysis

RSI: 62 (Bullish)
50MA > 200MA (Golden Cross)
Volume Increasing

Verdict:
Bullish Momentum
```

---

# 6.3 Sentiment Analyst Agent

Purpose:

Analyze **market sentiment**

Tools:

* DuckDuckGo Search
* Keyword-based sentiment classification (30+ positive, 30+ negative keywords)
* Per-article confidence scoring with ratio-bias aggregation

Sources:

* News articles via DuckDuckGo

Example Output

```
Top News

"Tata Motors sales jump 18%"

Sentiment Score:
Positive (0.72)
```

---

# 7. Data Layer

## Market Data

Using

Yahoo Finance Python Library

```
yfinance
```

Data Collected:

* Stock price
* Historical data
* Financial statements
* Company fundamentals

---

## News Data

Using:

DuckDuckGo Search API

Example:

```
Tata Motors stock news
Mahindra & Mahindra stock outlook
```

Then LLM summarizes sentiment.

---

# 8. LangGraph Orchestration Flow

Graph structure (implemented as sequential pipeline with per-node error isolation)

```
User Query
     |
     v
Intent Parser (parse_intent)
     |
     v
Sequential Execution (each node wrapped in try/except)
     |
     v
Fundamental Agent  --> state.fundamental
     |
     v
Technical Agent    --> state.technical
     |
     v
Sentiment Agent    --> state.sentiment
     |
     v
Aggregate & Recommend (weighted scoring)
     |
     v
Final Recommendation
```

Implementation notes:

* Sequential execution chosen for reliability (failed agent = neutral 50, pipeline continues)
* Per-agent metrics tracking (latency, error counts) via `utils/metrics.py`
* Pipeline-level counters: `pipeline.started`, `pipeline.completed`
* Deterministic workflow with explicit error isolation

---

# 9. Portfolio Analyzer

When user submits portfolio:

Example

```
[TATAMOTORS, INFY, M&M]
```

System performs:

For each stock:

```
Fundamental Analysis
Technical Analysis
Sentiment Analysis
```

Then returns:

```
Portfolio Summary

Best Performing: INFY
Most Risky: M&M

Recommendation:
Rebalance portfolio
```

---

# 10. Recommendation Engine

Final scoring:

```
Final Score =
0.4 * Fundamental
0.4 * Technical
0.2 * Sentiment
```

Decision:

| Score | Recommendation |
| ----- | -------------- |
| >80   | Strong Buy     |
| 60-80 | Buy            |
| 40-60 | Hold           |
| <40   | Avoid          |

---

# 11. Project Folder Structure

```
Market-Analyst-genAI-Project/
│
├── backend/
│   ├── main.py              # FastAPI app, CORS, middleware, /health, /metrics
│   ├── middleware.py         # Correlation ID middleware
│   ├── schemas.py            # Pydantic request/response models
│   └── routes/
│       ├── stock_routes.py   # POST /analyze_stock
│       └── portfolio_routes.py  # POST /portfolio_analysis, /compare_stocks
│
├── agents/
│   ├── master_agent.py       # Query parsing, orchestration, response building
│   ├── fundamental_agent.py  # 6-metric fundamental scoring
│   ├── technical_agent.py    # 4-indicator technical scoring
│   └── sentiment_agent.py    # Keyword-based sentiment scoring
│
├── data_sources/
│   ├── yahoo_finance.py      # get_quote, get_historical, get_financials
│   └── duckduckgo_search.py  # search_news with rate limiting and caching
│
├── langgraph/
│   └── graph_builder.py      # Sequential pipeline with error isolation
│
├── ui/
│   └── streamlit_app.py      # 3-tab UI (stock, portfolio, comparison)
│
├── utils/
│   ├── config.py             # Centralised env var configuration (17 settings)
│   ├── logger.py             # Loguru setup (stderr + dump.log)
│   ├── metrics.py            # In-memory metrics collector
│   ├── scoring_engine.py     # Weighted scoring + recommendation mapping
│   ├── portfolio_analyzer.py # Risk profiling, diversification, rebalance
│   └── prompt_templates.py   # LLM prompt templates
│
├── tests/                    # 297 tests mirroring source layout
├── doc/                      # Architecture, deployment, API reference, guides
├── Dockerfile                # Backend API container
├── Dockerfile.ui             # Streamlit UI container
├── docker-compose.yml        # Run API + UI together
├── requirements.txt
├── pyproject.toml            # pytest, ruff, mypy, coverage config
├── Makefile                  # install, dev-api, dev-ui, test, lint, quality
└── .env.example              # Environment variable template
```

---

# 12. Technology Stack

| Layer           | Tech                            |
| --------------- | ------------------------------- |
| UI              | Streamlit                       |
| API             | FastAPI                         |
| Agent Framework | LangGraph                       |
| LLM             | Google Gemini (configurable)    |
| Market Data     | Yahoo Finance (yfinance)        |
| Web Search      | DuckDuckGo (duckduckgo-search)  |
| Data Processing | Pandas                          |
| Indicators      | ta (Technical Analysis library) |
| Observability   | Loguru, custom metrics, correlation IDs |
| Testing         | Pytest (297 tests, 97% coverage)|
| Quality         | Ruff (lint), Mypy (types)       |
| Deployment      | Docker, Docker Compose          |

---

# 13. Example End-to-End Flow

User Query:

```
Compare Tata Motors vs Mahindra
Which should I buy?
```

System Flow:

```
1 User submits query
2 FastAPI receives request
3 Master Agent parses intent

4 Parallel Agents run

Fundamental Agent → Company financials
Technical Agent → Chart indicators
Sentiment Agent → News sentiment

5 Results aggregated

6 Final answer generated
```

Example Output:

```
Comparison

Tata Motors
Fundamental: Strong
Technical: Bullish
Sentiment: Positive

Mahindra
Fundamental: Stable
Technical: Neutral
Sentiment: Neutral

Recommendation
Tata Motors shows stronger momentum and sentiment.
Short-term buy candidate.
```

---

# 14. Implemented Beyond Original Spec

The following items from "Future Improvements" have been implemented:

* **Portfolio risk analysis**: `utils/portfolio_analyzer.py` provides per-stock risk profiling (Low/Medium/High), diversification scoring, and rebalance recommendations.
* **Observability**: Request correlation IDs, per-agent latency tracking, in-memory metrics exposed via `GET /metrics`.
* **Deployment**: Dockerfiles for API and UI, Docker Compose orchestration, deployment guide for Render/Railway/VM.

# 15. Remaining Future Improvements

* Sector comparison
* Earnings prediction
* Insider trading signals
* LLM-powered narrative generation (prompt templates ready, LLM calls not yet wired)
* Parallel agent execution (currently sequential for reliability)
* Persistent metrics storage (currently in-memory, resets on restart)
