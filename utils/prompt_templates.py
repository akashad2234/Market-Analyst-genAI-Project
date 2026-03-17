"""Prompt templates for LLM-powered narrative generation across all agents."""

FUNDAMENTAL_ANALYSIS_PROMPT = """\
You are a senior equity research analyst. Given the following fundamental metrics \
for {ticker}, write a concise investment analysis paragraph (3-5 sentences).

Metrics:
- PE Ratio: {pe_ratio}
- Debt to Equity: {debt_to_equity}
- Return on Equity (ROE): {return_on_equity}
- Profit Margin: {profit_margin}
- Revenue Growth: {revenue_growth}
- PEG Ratio: {peg_ratio}
- Market Cap: {market_cap}

Fundamental Score: {score}/100 ({verdict})

Focus on: what the numbers say about the company's valuation, financial health, \
and growth trajectory. Be specific with the numbers. Do not use em dashes.\
"""

TECHNICAL_ANALYSIS_PROMPT = """\
You are a senior technical analyst. Given the following indicators for {ticker}, \
write a concise technical analysis paragraph (3-5 sentences).

Indicators:
- RSI (14): {rsi}
- MACD: {macd}
- MACD Signal: {macd_signal}
- 50-Day MA: {ma_50}
- 200-Day MA: {ma_200}
- Volume Trend: {volume_trend}
- Current Price: {current_price}

Technical Score: {score}/100 ({verdict})

Focus on: momentum direction, key support/resistance levels, and whether the \
trend favours entry or caution. Do not use em dashes.\
"""

SENTIMENT_ANALYSIS_PROMPT = """\
You are a market sentiment analyst. Given the following recent news headlines and \
sentiment data for {ticker}, write a concise sentiment summary (3-5 sentences).

Headlines:
{headlines}

Overall Sentiment Score: {score}/100 ({verdict})
Positive articles: {positive_count}
Negative articles: {negative_count}
Neutral articles: {neutral_count}

Focus on: the dominant narrative in the market, any catalysts or risks, and \
overall investor sentiment direction. Do not use em dashes.\
"""

SUMMARY_ANALYSIS_PROMPT = """\
You are a senior equity research analyst. Given the following analysis scores \
for {ticker}, write a concise investment summary (4-6 sentences) that a \
portfolio manager can act on.

Analysis Results:
- Fundamental Score: {fundamental_score}/100 ({fundamental_verdict})
- Technical Score: {technical_score}/100 ({technical_verdict})
- Sentiment Score: {sentiment_score}/100 ({sentiment_verdict})
- Final Weighted Score: {final_score}/100
- Recommendation: {recommendation}

Synthesise the three dimensions into a coherent narrative. Explain where the \
stock is strong or weak, and what the recommendation means in practical terms. \
Do not use em dashes.\
"""
