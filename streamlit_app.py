"""
Standalone Streamlit app for deployment (Streamlit Cloud).

Runs analysis locally without requiring a separate FastAPI backend.
"""

import streamlit as st

from agents.master_agent import (
    AnalysisRequest,
    AnalysisResponse,
    QueryType,
    StockAnalysis,
    run_analysis,
)
from data_sources.yahoo_finance import normalize_ticker

st.set_page_config(page_title="AI Market Analyst", page_icon="📊", layout="wide")

st.title("AI Market Analyst")
st.caption("Multi-agent stock analysis: Fundamental, Technical, and Sentiment")


def _score_color(score: float | None) -> str:
    if score is None:
        return "gray"
    if score >= 75:
        return "green"
    if score >= 55:
        return "orange"
    return "red"


def _recommendation_emoji(rec: str) -> str:
    mapping = {"Strong Buy": "🟢", "Buy": "🟡", "Hold": "🟠", "Avoid": "🔴"}
    return mapping.get(rec, "⚪")


def _stock_to_dict(sa: StockAnalysis) -> dict:
    return {
        "ticker": sa.ticker,
        "fundamental_score": sa.fundamental_score,
        "fundamental_verdict": sa.fundamental_verdict,
        "technical_score": sa.technical_score,
        "technical_verdict": sa.technical_verdict,
        "sentiment_score": sa.sentiment_score,
        "sentiment_verdict": sa.sentiment_verdict,
        "final_score": sa.final_score,
        "recommendation": sa.recommendation,
        "explanation": sa.explanation,
        "errors": sa.errors,
    }


def _response_to_api_format(response: AnalysisResponse) -> dict:
    stocks = [_stock_to_dict(s) for s in response.stocks]
    data = {"stocks": stocks, "summary": response.summary}

    if response.query_type == QueryType.SINGLE_STOCK and stocks:
        data["stock"] = stocks[0]

    if response.portfolio_insight:
        pi = response.portfolio_insight
        data["portfolio_insight"] = {
            "average_score": pi.average_score,
            "overall_risk": pi.overall_risk.value,
            "best_performer": pi.best_performer,
            "worst_performer": pi.worst_performer,
            "diversification_score": pi.diversification_score,
            "risk_profiles": [
                {
                    "ticker": rp.ticker,
                    "risk_level": rp.risk_level.value,
                    "risk_factors": rp.risk_factors,
                }
                for rp in pi.risk_profiles
            ],
            "rebalance_suggestion": pi.rebalance_suggestion,
        }

    return data


def _display_stock(stock: dict) -> None:
    ticker = stock.get("ticker", "Unknown")
    final_score = stock.get("final_score")
    rec = stock.get("recommendation", "N/A")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Final Score", f"{final_score:.1f}/100" if final_score else "N/A")
    with col2:
        st.metric("Recommendation", f"{_recommendation_emoji(rec)} {rec}")
    with col3:
        st.metric("Ticker", ticker)

    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        fund_score = stock.get("fundamental_score")
        fund_verdict = stock.get("fundamental_verdict", "N/A")
        st.markdown(f"**Fundamental**: {fund_score:.1f}/100" if fund_score else "**Fundamental**: N/A")
        st.caption(fund_verdict)
        if fund_score:
            st.progress(fund_score / 100)

    with c2:
        tech_score = stock.get("technical_score")
        tech_verdict = stock.get("technical_verdict", "N/A")
        st.markdown(f"**Technical**: {tech_score:.1f}/100" if tech_score else "**Technical**: N/A")
        st.caption(tech_verdict)
        if tech_score:
            st.progress(tech_score / 100)

    with c3:
        sent_score = stock.get("sentiment_score")
        sent_verdict = stock.get("sentiment_verdict", "N/A")
        st.markdown(f"**Sentiment**: {sent_score:.1f}/100" if sent_score else "**Sentiment**: N/A")
        st.caption(sent_verdict)
        if sent_score:
            st.progress(sent_score / 100)

    errors = stock.get("errors", {})
    if errors:
        with st.expander("Agent Errors"):
            for agent, err in errors.items():
                st.error(f"{agent}: {err}")


def _run_analysis(analysis_type: str, tickers: list[str]) -> dict | None:
    try:
        if analysis_type == "single":
            request = AnalysisRequest(
                query_type=QueryType.SINGLE_STOCK,
                tickers=tickers,
            )
        elif analysis_type == "portfolio":
            request = AnalysisRequest(
                query_type=QueryType.PORTFOLIO,
                tickers=tickers,
            )
        else:
            request = AnalysisRequest(
                query_type=QueryType.COMPARISON,
                tickers=tickers,
            )
        response = run_analysis(request)
        return _response_to_api_format(response)
    except ValueError as e:
        st.error(str(e))
        return None
    except Exception as e:
        st.error(f"Analysis failed: {e}")
        return None


tab1, tab2, tab3 = st.tabs(["Stock Analysis", "Portfolio Analysis", "Compare Stocks"])


with tab1:
    st.subheader("Analyze a Single Stock")
    ticker = st.text_input("Stock Ticker", placeholder="e.g. RELIANCE.NS", key="single_ticker")

    if st.button("Analyze", key="btn_analyze", type="primary"):
        if not ticker.strip():
            st.warning("Please enter a ticker symbol.")
        else:
            with st.spinner(f"Analyzing {ticker.strip().upper()}..."):
                normalized = normalize_ticker(ticker.strip())
                data = _run_analysis("single", [normalized])
            if data:
                st.success(data.get("summary", ""))
                _display_stock(data["stock"])


with tab2:
    st.subheader("Portfolio Analysis")
    stocks_input = st.text_area(
        "Enter tickers (comma-separated)",
        placeholder="e.g. TATAMOTORS.NS, INFY.NS, M&M.NS",
        key="portfolio_input",
    )

    if st.button("Analyze Portfolio", key="btn_portfolio", type="primary"):
        tickers = [normalize_ticker(t.strip()) for t in stocks_input.split(",") if t.strip()]
        if len(tickers) < 2:
            st.warning("Please enter at least 2 ticker symbols, comma-separated.")
        else:
            with st.spinner(f"Analyzing portfolio: {', '.join(tickers)}..."):
                data = _run_analysis("portfolio", tickers)
            if data:
                st.success(data.get("summary", "").replace("\n", "  \n"))

                insight = data.get("portfolio_insight")
                if insight:
                    st.markdown("### Portfolio Overview")
                    oc1, oc2, oc3, oc4 = st.columns(4)
                    with oc1:
                        st.metric("Average Score", f"{insight['average_score']:.1f}/100")
                    with oc2:
                        st.metric("Overall Risk", insight.get("overall_risk", "N/A"))
                    with oc3:
                        st.metric("Best Performer", insight.get("best_performer", "N/A"))
                    with oc4:
                        st.metric("Diversification", f"{insight['diversification_score']:.1f}/100")

                    rebalance = insight.get("rebalance_suggestion", "")
                    if rebalance:
                        st.info(f"**Rebalance Advice**: {rebalance}")

                    risk_profiles = insight.get("risk_profiles", [])
                    if risk_profiles:
                        with st.expander("Risk Profiles"):
                            for rp in risk_profiles:
                                risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(
                                    rp["risk_level"], "⚪"
                                )
                                factors = ", ".join(rp.get("risk_factors", [])) or "None"
                                st.markdown(
                                    f"- **{rp['ticker']}**: {risk_emoji} "
                                    f"{rp['risk_level']} risk. Factors: {factors}"
                                )

                st.markdown("### Individual Holdings")
                for stock in data.get("stocks", []):
                    with st.expander(f"{stock['ticker']} - {stock.get('recommendation', 'N/A')}"):
                        _display_stock(stock)


with tab3:
    st.subheader("Compare Two Stocks")
    col_a, col_b = st.columns(2)
    with col_a:
        stock1 = st.text_input("Stock 1", placeholder="e.g. TATAMOTORS.NS", key="compare_stock1")
    with col_b:
        stock2 = st.text_input("Stock 2", placeholder="e.g. M&M.NS", key="compare_stock2")

    if st.button("Compare", key="btn_compare", type="primary"):
        if not stock1.strip() or not stock2.strip():
            st.warning("Please enter both ticker symbols.")
        else:
            with st.spinner(f"Comparing {stock1.strip().upper()} vs {stock2.strip().upper()}..."):
                tickers = [normalize_ticker(stock1.strip()), normalize_ticker(stock2.strip())]
                data = _run_analysis("comparison", tickers)
            if data:
                st.success(data.get("summary", "").replace("\n", "  \n"))
                cols = st.columns(2)
                for i, stock in enumerate(data.get("stocks", [])):
                    with cols[i % 2]:
                        st.markdown(f"### {stock['ticker']}")
                        _display_stock(stock)


st.divider()
st.caption("Powered by LangGraph multi-agent orchestration | Data: Yahoo Finance, DuckDuckGo")
