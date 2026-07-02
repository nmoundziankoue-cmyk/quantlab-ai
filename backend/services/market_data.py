"""Market data service: live price fetching with an in-memory TTL cache.

This module is the single point of contact for all yfinance calls inside the
backend.  A simple TTL cache avoids hammering Yahoo Finance on every request;
Redis will replace this in Milestone 2.
"""
from __future__ import annotations

import time
from typing import Optional

import pandas as pd
import yfinance as yf

from config import settings

# ---------------------------------------------------------------------------
# In-memory caches
# ---------------------------------------------------------------------------

# ticker -> (price, fetched_at_unix)
_price_cache: dict[str, tuple[float, float]] = {}

# ticker -> (sector, fetched_at_unix)
_sector_cache: dict[str, tuple[str, float]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_prices(tickers: list[str]) -> dict[str, float]:
    """Return the latest closing price for each ticker.

    Prices younger than ``price_cache_ttl_seconds`` are served from the cache.
    All stale tickers are fetched in a single yfinance batch call.

    Args:
        tickers: List of uppercase ticker symbols.

    Returns:
        Mapping of ticker → latest closing price.  Tickers for which no data
        was available are absent from the result.
    """
    if not tickers:
        return {}

    now = time.monotonic()
    ttl = settings.price_cache_ttl_seconds

    result: dict[str, float] = {}
    stale: list[str] = []

    for ticker in tickers:
        cached = _price_cache.get(ticker)
        if cached and (now - cached[1]) < ttl:
            result[ticker] = cached[0]
        else:
            stale.append(ticker)

    if not stale:
        return result

    try:
        raw = yf.download(
            stale if len(stale) > 1 else stale[0],
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )

        if raw.empty:
            return result

        # Flatten MultiIndex columns returned by yfinance ≥ 0.2
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"]
        else:
            # Single ticker returns flat columns
            closes = raw[["Close"]]
            closes.columns = stale

        for ticker in stale:
            if ticker not in closes.columns:
                continue
            series = closes[ticker].dropna()
            if series.empty:
                continue
            price = float(series.iloc[-1])
            _price_cache[ticker] = (price, now)
            result[ticker] = price

    except Exception:
        # Degrade gracefully: return whatever was already in the cache
        pass

    return result


def get_price_history(
    tickers: list[str],
    start: "date",  # noqa: F821  (date imported only when needed)
    end: "date",
) -> pd.DataFrame:
    """Return daily close prices for each ticker over the requested range.

    Args:
        tickers: List of uppercase ticker symbols.
        start:   Inclusive start date.
        end:     Inclusive end date.

    Returns:
        DataFrame indexed by date, with one column per ticker containing the
        adjusted closing price.  Missing values are forward-filled.

    Raises:
        RuntimeError: If yfinance fails entirely.
    """
    if not tickers:
        return pd.DataFrame()

    from datetime import timedelta

    try:
        raw = yf.download(
            tickers if len(tickers) > 1 else tickers[0],
            start=start,
            end=end + timedelta(days=1),
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        raise RuntimeError(f"yfinance download failed: {exc}") from exc

    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"].copy()
    else:
        prices = raw[["Close"]].copy()
        prices.columns = tickers

    return prices.ffill()


def get_sector(ticker: str) -> str:
    """Return the GICS sector for a ticker, cached for 24 hours.

    Args:
        ticker: Uppercase ticker symbol.

    Returns:
        Sector string (e.g. ``"Technology"``), or ``"Unknown"`` on failure.
    """
    now = time.monotonic()
    ttl = settings.sector_cache_ttl_seconds

    cached = _sector_cache.get(ticker)
    if cached and (now - cached[1]) < ttl:
        return cached[0]

    try:
        info = yf.Ticker(ticker).info
        sector: str = info.get("sector") or "Unknown"
    except Exception:
        sector = "Unknown"

    _sector_cache[ticker] = (sector, now)
    return sector


def get_day_change_pct(ticker: str) -> Optional[float]:
    """Return today's intraday percentage change for a ticker.

    Args:
        ticker: Uppercase ticker symbol.

    Returns:
        Percentage change (e.g. ``1.23`` for +1.23 %) or ``None`` on failure.
    """
    try:
        info = yf.Ticker(ticker).fast_info
        prev_close: float = info.previous_close
        current: float = info.last_price
        if prev_close and prev_close > 0:
            return round((current - prev_close) / prev_close * 100, 2)
    except Exception:
        pass
    return None
