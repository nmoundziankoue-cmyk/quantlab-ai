"""Market Intelligence Platform router (M7) — sector heatmaps, breadth, regime."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter

import services.market_intelligence as svc

router = APIRouter(prefix="/market-intel", tags=["Market Intelligence"])


@router.get("/sector-heatmap", response_model=Dict[str, Any])
def get_sector_heatmap(period: str = "1D"):
    """Return sector performance heatmap. Period: 1D, 1W, 1M, YTD."""
    return svc.get_sector_heatmap(period=period)


@router.get("/breadth", response_model=Dict[str, Any])
def get_market_breadth():
    """Return market breadth indicators: A/D ratio, 52w hi/lo, McClellan."""
    return svc.get_market_breadth()


@router.get("/regime", response_model=Dict[str, Any])
def get_market_regime():
    """Detect and return the current market regime."""
    return svc.get_market_regime()


@router.get("/yield-curve", response_model=Dict[str, Any])
def get_yield_curve():
    """Return synthetic US Treasury yield curve."""
    return svc.get_yield_curve()


@router.get("/macro", response_model=Dict[str, Any])
def get_global_macro():
    """Return global macro indicators: GDP, CPI, PMI, central bank rates."""
    return svc.get_global_macro()


@router.post("/correlation", response_model=Dict[str, Any])
def get_correlation_matrix(body: Dict[str, Any]):
    """Return pairwise correlation matrix for the given tickers."""
    tickers = body.get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
    return svc.get_correlation_matrix(tickers)


@router.get("/liquidity/{ticker}", response_model=Dict[str, Any])
def get_liquidity(ticker: str):
    """Return liquidity metrics for a ticker."""
    return svc.get_liquidity_metrics(ticker.upper())


@router.get("/dashboard", response_model=Dict[str, Any])
def get_market_intelligence_dashboard():
    """Return a consolidated market intelligence dashboard."""
    regime = svc.get_market_regime()
    breadth = svc.get_market_breadth()
    heatmap_1d = svc.get_sector_heatmap("1D")
    macro = svc.get_global_macro()
    yield_curve = svc.get_yield_curve()

    return {
        "regime": regime,
        "breadth": breadth,
        "sector_performance_1d": heatmap_1d["sectors"][:5],
        "macro_snapshot": {
            "us_gdp_growth": macro["us"]["gdp_growth_yoy"],
            "us_cpi": macro["us"]["cpi_yoy"],
            "fed_rate": macro["central_banks"]["fed_rate"],
            "dxy": macro["global"]["dollar_index_dxy"],
        },
        "yield_curve": {
            "spread_2s10s": yield_curve["spread_2s10s"],
            "is_inverted": yield_curve["is_inverted"],
            "curve_shape": yield_curve["curve_shape"],
        },
    }
