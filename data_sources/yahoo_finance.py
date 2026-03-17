from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf
from loguru import logger

try:
    from utils.config import YAHOO_HISTORY_INTERVAL, YAHOO_HISTORY_PERIOD_DAYS
except Exception:
    YAHOO_HISTORY_PERIOD_DAYS = 365
    YAHOO_HISTORY_INTERVAL = "1d"


class YahooFinanceError(Exception):
    """Raised when Yahoo Finance data retrieval fails."""


def normalize_ticker(ticker: str) -> str:
    """Normalize a user-supplied ticker into Yahoo Finance format.

    - Strips whitespace, uppercases
    - Removes internal spaces ("ADANI POWER" -> "ADANIPOWER")
    - Appends ".NS" (NSE India) when no exchange suffix is present
    """
    ticker = ticker.strip().upper().replace(" ", "")
    if not ticker:
        raise YahooFinanceError("Ticker symbol cannot be empty.")
    if "." not in ticker:
        ticker = f"{ticker}.NS"
    return ticker


def _validate_ticker(ticker: str) -> str:
    return normalize_ticker(ticker)


def get_quote(ticker: str) -> dict[str, Any]:
    """Fetch current quote and company metadata for a single ticker.

    Returns a dict with keys: ticker, name, sector, industry, market_cap,
    current_price, previous_close, currency, exchange.
    """
    ticker = _validate_ticker(ticker)
    logger.info("Fetching quote for {}", ticker)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            raise YahooFinanceError(f"No data returned for ticker '{ticker}'. It may be invalid.")

        quote = {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap"),
            "current_price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "previous_close": info.get("previousClose"),
            "currency": info.get("currency", "INR"),
            "exchange": info.get("exchange", ""),
        }
        logger.debug("Quote for {}: price={}, cap={}", ticker, quote["current_price"], quote["market_cap"])
        return quote

    except YahooFinanceError:
        raise
    except Exception as exc:
        logger.error("Failed to fetch quote for {}: {}", ticker, exc)
        raise YahooFinanceError(f"Failed to fetch quote for '{ticker}': {exc}") from exc


def get_historical(
    ticker: str,
    period_days: int | None = None,
    interval: str | None = None,
) -> pd.DataFrame:
    """Fetch historical OHLCV data for a ticker.

    Args:
        ticker: Stock symbol (e.g. "RELIANCE.NS").
        period_days: Number of calendar days of history to fetch.
        interval: Candle interval ("1d", "1wk", "1mo").

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume.
    """
    if period_days is None:
        period_days = YAHOO_HISTORY_PERIOD_DAYS
    if interval is None:
        interval = YAHOO_HISTORY_INTERVAL
    ticker = _validate_ticker(ticker)
    logger.info("Fetching {} days of historical data for {} (interval={})", period_days, ticker, interval)

    try:
        end = datetime.now()
        start = end - timedelta(days=period_days)

        stock = yf.Ticker(ticker)
        df = stock.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval=interval)

        if df is None or df.empty:
            raise YahooFinanceError(f"No historical data returned for '{ticker}'.")

        df = df.reset_index()
        keep_cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[keep_cols]

        logger.debug(
            "Historical data for {}: {} rows, range {} to {}",
            ticker, len(df), df["Date"].iloc[0], df["Date"].iloc[-1],
        )
        return df

    except YahooFinanceError:
        raise
    except Exception as exc:
        logger.error("Failed to fetch historical data for {}: {}", ticker, exc)
        raise YahooFinanceError(f"Failed to fetch historical data for '{ticker}': {exc}") from exc


def get_financials(ticker: str) -> dict[str, Any]:
    """Fetch key financial ratios and fundamentals for a ticker.

    Returns a dict with keys: ticker, pe_ratio, forward_pe, peg_ratio,
    price_to_book, debt_to_equity, return_on_equity, profit_margin,
    revenue_growth, market_cap, dividend_yield, beta, fifty_two_week_high,
    fifty_two_week_low.
    """
    ticker = _validate_ticker(ticker)
    logger.info("Fetching financials for {}", ticker)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info:
            raise YahooFinanceError(f"No financial data returned for '{ticker}'.")

        financials = {
            "ticker": ticker,
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "market_cap": info.get("marketCap"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        }

        logger.debug(
            "Financials for {}: PE={}, D/E={}, ROE={}",
            ticker,
            financials["pe_ratio"],
            financials["debt_to_equity"],
            financials["return_on_equity"],
        )

        return financials

    except YahooFinanceError:
        raise
    except Exception as exc:
        logger.error("Failed to fetch financials for {}: {}", ticker, exc)
        raise YahooFinanceError(f"Failed to fetch financials for '{ticker}': {exc}") from exc
