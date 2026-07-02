"""Stress testing service — M4.

Applies historical or user-defined factor shocks to a portfolio
and returns the expected P&L impact.

Built-in scenarios use actual historical return windows from
real market events, fetched via yfinance.  This gives the most
realistic stress loss for each crisis period.

Custom scenarios accept per-ticker shock percentages in ``shocks``
dict, e.g. ``{"AAPL": -0.35, "_MARKET_": -0.20}``.  The special
key ``_MARKET_`` applies the shock to all tickers not explicitly listed.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from services.market_data import get_price_history

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built-in scenario definitions
# ---------------------------------------------------------------------------
# Each scenario specifies a historical period; we download the actual
# return for each holding over that window to compute the stress P&L.

BUILTIN_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "2008_financial_crisis": {
        "name": "2008 Financial Crisis",
        "description": "Lehman Brothers collapse and the global financial crisis.",
        "start": "2008-09-01",
        "end": "2009-03-09",
    },
    "covid_crash": {
        "name": "COVID-19 Crash",
        "description": "Pandemic-driven market selloff Q1 2020.",
        "start": "2020-02-19",
        "end": "2020-03-23",
    },
    "dotcom_crash": {
        "name": "Dot-com Crash",
        "description": "Tech bubble burst 2000–2002.",
        "start": "2000-03-10",
        "end": "2002-10-09",
    },
    "rate_shock_2022": {
        "name": "Rate Shock 2022",
        "description": "Fed's aggressive rate hike cycle; worst bond/equity decline in decades.",
        "start": "2022-01-03",
        "end": "2022-10-14",
    },
    "inflation_shock_1973": {
        "name": "Oil Embargo / Inflation Shock",
        "description": "OPEC oil embargo and stagflation (proxy: 1973–1974 bear market).",
        "start": "1973-01-11",
        "end": "1974-10-04",
    },
    "oil_shock_2014": {
        "name": "Oil Price Collapse 2014",
        "description": "Crude oil dropped ~60% between mid-2014 and early 2016.",
        "start": "2014-06-20",
        "end": "2016-01-20",
    },
    "russia_ukraine_2022": {
        "name": "Russia-Ukraine Conflict Shock",
        "description": "Initial market shock from the Russian invasion of Ukraine.",
        "start": "2022-02-24",
        "end": "2022-03-08",
    },
}


# ---------------------------------------------------------------------------
# Core stress computation
# ---------------------------------------------------------------------------

def _download_scenario_returns(
    tickers: List[str],
    start: str,
    end: str,
) -> Dict[str, float]:
    """Download cumulative returns for each ticker over [start, end]."""
    try:
        prices = get_price_history(tickers, start, end)
    except Exception as exc:
        logger.warning("Stress test data download failed: %s", exc)
        return {}

    if prices.empty:
        return {}

    result: Dict[str, float] = {}
    for ticker in tickers:
        if ticker not in prices.columns:
            continue
        col = prices[ticker].dropna()
        if len(col) < 2:
            continue
        total_return = (col.iloc[-1] / col.iloc[0]) - 1.0
        result[ticker] = float(total_return)
    return result


def run_builtin_scenario(
    scenario_key: str,
    holdings: Dict[str, float],
) -> Dict[str, Any]:
    """Run a built-in stress scenario against the current portfolio.

    Parameters
    ----------
    scenario_key : key in BUILTIN_SCENARIOS
    holdings : {ticker: market_value} dict

    Returns
    -------
    dict with scenario metadata, per-asset impact, total P&L
    """
    if scenario_key not in BUILTIN_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_key!r}")

    scenario = BUILTIN_SCENARIOS[scenario_key]
    tickers = [t for t in holdings if not t.startswith("_")]

    historical_returns = _download_scenario_returns(
        tickers, scenario["start"], scenario["end"]
    )

    total_value = sum(holdings.values())
    asset_impacts: List[Dict[str, Any]] = []
    total_pnl = 0.0

    for ticker, market_value in holdings.items():
        ret = historical_returns.get(ticker, None)
        pnl = float(market_value) * ret if ret is not None else 0.0
        total_pnl += pnl
        asset_impacts.append({
            "ticker": ticker,
            "market_value": round(float(market_value), 2),
            "return_pct": round(ret * 100, 2) if ret is not None else None,
            "pnl": round(pnl, 2),
            "weight_pct": round(float(market_value) / total_value * 100, 2) if total_value > 0 else 0.0,
        })

    portfolio_return_pct = (total_pnl / total_value * 100) if total_value > 0 else 0.0

    return {
        "scenario_key": scenario_key,
        "scenario_name": scenario["name"],
        "description": scenario["description"],
        "period_start": scenario["start"],
        "period_end": scenario["end"],
        "total_portfolio_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "portfolio_return_pct": round(portfolio_return_pct, 2),
        "asset_impacts": sorted(asset_impacts, key=lambda x: x["pnl"]),
    }


def run_custom_scenario(
    scenario_name: str,
    shocks: Dict[str, float],
    holdings: Dict[str, float],
) -> Dict[str, Any]:
    """Apply user-defined shock percentages to the portfolio.

    Parameters
    ----------
    scenario_name : display name for the scenario
    shocks : {ticker: shock_fraction} e.g. {"AAPL": -0.30, "_MARKET_": -0.20}
              ``_MARKET_`` applies to any ticker not explicitly listed.
    holdings : {ticker: market_value}
    """
    total_value = sum(holdings.values())
    asset_impacts: List[Dict[str, Any]] = []
    total_pnl = 0.0
    market_shock = shocks.get("_MARKET_", 0.0)

    for ticker, market_value in holdings.items():
        shock = shocks.get(ticker, market_shock)
        pnl = float(market_value) * shock
        total_pnl += pnl
        asset_impacts.append({
            "ticker": ticker,
            "market_value": round(float(market_value), 2),
            "return_pct": round(shock * 100, 2),
            "pnl": round(pnl, 2),
            "weight_pct": round(float(market_value) / total_value * 100, 2) if total_value > 0 else 0.0,
        })

    portfolio_return_pct = (total_pnl / total_value * 100) if total_value > 0 else 0.0

    return {
        "scenario_key": "custom",
        "scenario_name": scenario_name,
        "description": "User-defined shock scenario",
        "period_start": None,
        "period_end": None,
        "total_portfolio_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "portfolio_return_pct": round(portfolio_return_pct, 2),
        "asset_impacts": sorted(asset_impacts, key=lambda x: x["pnl"]),
    }


def run_all_builtin_scenarios(
    holdings: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Run all built-in scenarios and return a summary list."""
    results = []
    for key in BUILTIN_SCENARIOS:
        try:
            result = run_builtin_scenario(key, holdings)
            results.append({
                "scenario_key": key,
                "scenario_name": result["scenario_name"],
                "portfolio_return_pct": result["portfolio_return_pct"],
                "total_pnl": result["total_pnl"],
            })
        except Exception as exc:
            logger.warning("Scenario %s failed: %s", key, exc)
            results.append({
                "scenario_key": key,
                "scenario_name": BUILTIN_SCENARIOS[key]["name"],
                "portfolio_return_pct": None,
                "total_pnl": None,
            })
    return results
