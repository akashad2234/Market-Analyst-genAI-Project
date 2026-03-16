# Agent Behavior and Scoring Rules

This document describes how each agent analyses stocks and produces scores.

All scores are on a **0-100 scale** where higher is better. A score of 50 represents neutral/insufficient data.

---

## 1. Fundamental Analyst Agent

**Source:** `agents/fundamental_agent.py`
**Data:** Yahoo Finance (`get_financials`)

### Metrics Scored

| Metric | Weight | Scoring Logic |
|---|---|---|
| PE Ratio | 20% | Lower is better. PE <= 10: 95, PE <= 15: 85, PE <= 20: 70, PE <= 30: 55, PE <= 50: 35, PE > 50: 15, negative PE: 10 |
| Debt/Equity | 20% | Lower is better. Raw value is percentage, converted to ratio internally. D/E <= 0.3: 95, D/E <= 0.6: 80, D/E <= 1.0: 65, D/E <= 1.5: 45, D/E <= 2.0: 30, D/E > 2.0: 15 |
| ROE | 20% | Higher is better. ROE >= 25%: 95, >= 20%: 85, >= 15%: 70, >= 10%: 55, >= 5%: 40, < 5%: 20, negative: 10 |
| Profit Margin | 15% | Higher is better. >= 25%: 95, >= 15%: 80, >= 10%: 65, >= 5%: 50, >= 0%: 35, negative: 15 |
| Revenue Growth | 15% | Higher is better. >= 30%: 95, >= 20%: 85, >= 10%: 70, >= 5%: 55, >= 0%: 40, negative: 20 |
| PEG Ratio | 10% | Lower is better (growth at reasonable price). PEG <= 0.5: 95, <= 1.0: 85, <= 1.5: 70, <= 2.0: 55, <= 3.0: 35, > 3.0: 15, negative: 10 |

### Verdict Mapping

| Score Range | Verdict |
|---|---|
| >= 75 | Strong |
| >= 55 | Moderate |
| >= 35 | Weak |
| < 35 | Very Weak |

### Edge Cases

- Any `None` metric value receives a neutral score of 50 (insufficient data).
- All scorers handle negative values explicitly.

---

## 2. Technical Analyst Agent

**Source:** `agents/technical_agent.py`
**Data:** Yahoo Finance (`get_historical`, 365 days, 1d interval)
**Library:** `ta` (Technical Analysis)

### Indicators Computed

| Indicator | Parameters | Weight |
|---|---|---|
| RSI | 14-period | 25% |
| MACD | 12/26/9 (fast/slow/signal) | 25% |
| Moving Averages | 50-day SMA, 200-day SMA | 30% |
| Volume Trend | % change in recent vs prior volume | 20% |

### Scoring Logic

**RSI (0-100):**
- RSI <= 20 (deeply oversold): 90
- RSI <= 30 (oversold): 80
- RSI 30-45: 65
- RSI 45-55 (neutral): 50
- RSI 55-70: 40
- RSI >= 70 (overbought): 25
- RSI >= 80 (deeply overbought): 15

**MACD:**
- MACD above signal + positive histogram: 85
- MACD above signal: 70
- MACD below signal: 30
- MACD below signal + negative histogram: 15

**Moving Averages:**
- Price above both 50 and 200 SMA (golden cross): 90
- Price above 50 SMA only: 65
- Price above 200 SMA only: 55
- Price below both: 20
- Both MAs missing: neutral 50

**Volume Trend:**
- Volume increase > 20%: 80
- Volume increase > 5%: 65
- Flat volume: 50
- Volume decrease > 5%: 35
- Volume decrease > 20%: 20

### Verdict Mapping

| Score Range | Verdict |
|---|---|
| >= 75 | Bullish |
| >= 60 | Moderately Bullish |
| >= 40 | Neutral |
| >= 25 | Moderately Bearish |
| < 25 | Bearish |

---

## 3. Sentiment Analyst Agent

**Source:** `agents/sentiment_agent.py`
**Data:** DuckDuckGo news search (up to 10 articles by default)

### Classification Method

Keyword-based classification using two keyword sets:
- **Positive keywords** (30+): surge, rally, gain, profit, bullish, growth, beat, breakout, etc.
- **Negative keywords** (30+): crash, fall, plunge, loss, bearish, debt, fraud, layoff, etc.

Each article is classified as positive, negative, or neutral based on keyword hit count in the title and snippet. Confidence scales with the number of matching keywords.

### Aggregation

1. Each classified article gets a score (positive: 60-85, negative: 15-40, neutral: 50).
2. Overall score = average of all article scores + ratio bias (dominant sentiment gets a boost).
3. Final score clamped to 0-100.

### Verdict Mapping

| Score Range | Verdict |
|---|---|
| >= 70 | Positive |
| >= 55 | Moderately Positive |
| >= 45 | Neutral |
| >= 30 | Moderately Negative |
| < 30 | Negative |

### No News Fallback

If no articles are found, returns neutral score of 50 with an explanation.

---

## 4. Scoring Engine (Aggregation)

**Source:** `utils/scoring_engine.py`

### Final Score Calculation

```
Final Score = (Fundamental * 0.4) + (Technical * 0.4) + (Sentiment * 0.2)
```

Weights are configurable via environment variables.

### Recommendation Thresholds

| Min Score | Recommendation |
|---|---|
| 80 | Strong Buy |
| 60 | Buy |
| 40 | Hold |
| 0 | Avoid |

Thresholds are configurable via `SCORING_THRESHOLDS` environment variable.

---

## 5. Portfolio Analyzer

**Source:** `utils/portfolio_analyzer.py`

### Per-Stock Risk Assessment

Each stock is categorised as Low, Medium, or High risk based on:
- Final score below 40: risk factor
- Fundamental score below 40: "Weak fundamentals"
- Technical score below 40: "Bearish technicals"
- Sentiment score below 40: "Negative sentiment"
- Spread between sub-scores > 40 points: "High divergence between analysts"

**Risk Level Assignment:**
- **High**: final score < 40, OR 2+ risk factors
- **Low**: final score >= 70, AND 0 risk factors
- **Medium**: everything else

### Diversification Score

Standard deviation of portfolio stock scores, normalised to 0-100:
- 0 = all stocks scored identically (or single stock)
- 100 = maximum spread (std dev >= 50)

### Rebalance Suggestions

Generated based on:
- Proportion of high-risk holdings (> 50% triggers "heavily weighted" warning)
- Absence of low-risk holdings (triggers "add defensive positions" advice)
- Overall portfolio health (strong >= 70, moderate >= 50, weak < 50)

---

## 6. LLM-Powered Narrative Generation

Each agent can optionally produce an AI-generated narrative paragraph in addition to the rule-based explanation.

**Activation:** Set `LLM_ENABLED=true` in `.env` (disabled by default).

**Behaviour:**
- When enabled, each agent formats its data into a prompt template (see `utils/prompt_templates.py`) and sends it to Google Gemini via `utils/llm_client.py`.
- The LLM response is appended after the rule-based output under an "AI Narrative:" heading.
- If the LLM call fails (network error, rate limit, empty response, SDK missing), the agent silently falls back to rule-only output. No exception is raised.

**Prompt Templates:**
| Agent | Template | Focus |
|-------|----------|-------|
| Fundamental | `FUNDAMENTAL_ANALYSIS_PROMPT` | Valuation, financial health, growth trajectory |
| Technical | `TECHNICAL_ANALYSIS_PROMPT` | Momentum, support/resistance, trend direction |
| Sentiment | `SENTIMENT_ANALYSIS_PROMPT` | Market narrative, catalysts, investor sentiment |

**Configuration:**
| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_ENABLED` | `false` | Master switch for narrative generation |
| `LLM_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `LLM_TEMPERATURE` | `0.3` | Generation temperature (lower = more deterministic) |

---

## 7. Error Handling

- If an agent fails during the pipeline, its error is logged and stored in `state.errors`.
- The failed agent's score defaults to neutral (50).
- The pipeline continues with remaining agents.
- Error details are included in the API response under `errors` for each stock.
