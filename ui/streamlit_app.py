import os

import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

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


def _api_call(endpoint: str, payload: dict) -> dict | None:
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        st.error(f"API error ({resp.status_code}): {resp.json().get('detail', resp.text)}")
        return None
    except requests.ConnectionError:
        st.error("Cannot connect to the API server. Make sure it is running on http://localhost:8000")
        return None
    except requests.Timeout:
        st.error("Request timed out. The analysis may be taking too long.")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
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
                data = _api_call("/analyze_stock", {"ticker": ticker.strip()})
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
        tickers = [t.strip() for t in stocks_input.split(",") if t.strip()]
        if len(tickers) < 2:
            st.warning("Please enter at least 2 ticker symbols, comma-separated.")
        else:
            with st.spinner(f"Analyzing portfolio: {', '.join(tickers)}..."):
                data = _api_call("/portfolio_analysis", {"stocks": tickers})
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
                                risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(rp["risk_level"], "⚪")
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
                data = _api_call("/compare_stocks", {"stock1": stock1.strip(), "stock2": stock2.strip()})
            if data:
                st.success(data.get("summary", "").replace("\n", "  \n"))
                cols = st.columns(2)
                for i, stock in enumerate(data.get("stocks", [])):
                    with cols[i % 2]:
                        st.markdown(f"### {stock['ticker']}")
                        _display_stock(stock)


st.divider()
st.caption("Powered by LangGraph multi-agent orchestration | Data: Yahoo Finance, DuckDuckGo")
