"""Market Intelligence Platform — sector heatmaps, breadth, regime detection (M7).

All data is synthetic/deterministic. Uses hash-based seeding so results are
stable across calls without requiring live market data.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Sector universe
# ---------------------------------------------------------------------------

SECTORS = [
    {"name": "Technology", "etf": "XLK", "weight": 0.28},
    {"name": "Healthcare", "etf": "XLV", "weight": 0.13},
    {"name": "Financials", "etf": "XLF", "weight": 0.13},
    {"name": "Consumer Discretionary", "etf": "XLY", "weight": 0.10},
    {"name": "Industrials", "etf": "XLI", "weight": 0.09},
    {"name": "Communication Services", "etf": "XLC", "weight": 0.09},
    {"name": "Consumer Staples", "etf": "XLP", "weight": 0.07},
    {"name": "Energy", "etf": "XLE", "weight": 0.05},
    {"name": "Utilities", "etf": "XLU", "weight": 0.03},
    {"name": "Real Estate", "etf": "XLRE", "weight": 0.03},
    {"name": "Materials", "etf": "XLB", "weight": 0.03},
]

SECTOR_TICKERS: Dict[str, List[str]] = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ADBE", "CRM", "AMD", "INTC", "ORCL", "QCOM"],
    "Healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "AMGN", "ISRG", "DHR"],
    "Financials": ["BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "C"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TJX", "BKNG", "LOW", "MAR"],
    "Industrials": ["CAT", "UNP", "RTX", "HON", "LMT", "DE", "BA", "MMM", "GE", "FDX"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "EA", "ATVI"],
    "Consumer Staples": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "MDLZ", "GIS", "KHC"],
    "Energy": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "OXY", "DVN", "HES"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PCG", "ES"],
    "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "DLR", "O", "SBAC", "EQR", "AVB"],
    "Materials": ["LIN", "APD", "SHW", "FCX", "NEM", "ECL", "DOW", "PPG", "NUE", "CF"],
}


def _det_float(seed: str, lo: float, hi: float) -> float:
    """Deterministic float in [lo, hi] based on a string seed."""
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    return lo + (h % 10000) / 10000 * (hi - lo)


# ---------------------------------------------------------------------------
# Sector heatmap
# ---------------------------------------------------------------------------

def get_sector_heatmap(period: str = "1D") -> Dict[str, Any]:
    """Return sector performance heatmap."""
    periods = {"1D": (-3.0, 3.0), "1W": (-8.0, 8.0), "1M": (-20.0, 20.0), "YTD": (-40.0, 40.0)}
    lo, hi = periods.get(period, (-3.0, 3.0))

    sectors_out = []
    for s in SECTORS:
        perf = round(_det_float(f"{s['name']}_{period}", lo, hi), 2)
        tickers_out = []
        for t in SECTOR_TICKERS.get(s["name"], [])[:5]:
            t_perf = round(_det_float(f"{t}_{period}", lo * 1.5, hi * 1.5), 2)
            tickers_out.append({"ticker": t, "performance": t_perf})
        sectors_out.append({
            "sector": s["name"],
            "etf": s["etf"],
            "weight": s["weight"],
            "performance": perf,
            "top_tickers": tickers_out,
        })

    sorted_sectors = sorted(sectors_out, key=lambda x: x["performance"], reverse=True)
    return {
        "period": period,
        "sectors": sorted_sectors,
        "best_sector": sorted_sectors[0]["sector"] if sorted_sectors else None,
        "worst_sector": sorted_sectors[-1]["sector"] if sorted_sectors else None,
        "market_breadth": sum(1 for s in sorted_sectors if s["performance"] > 0) / len(sorted_sectors),
    }


# ---------------------------------------------------------------------------
# Market breadth
# ---------------------------------------------------------------------------

def get_market_breadth() -> Dict[str, Any]:
    """Return advance/decline, 52-week hi/lo, and % above key MAs."""
    total = 500  # S&P 500
    advancing = int(_det_float("breadth_adv", 150, 400))
    declining = total - advancing
    new_highs = int(_det_float("breadth_52h", 10, 80))
    new_lows = int(_det_float("breadth_52l", 5, 40))

    pct_above_50ma = round(_det_float("breadth_50ma", 40.0, 80.0), 1)
    pct_above_200ma = round(_det_float("breadth_200ma", 35.0, 75.0), 1)

    ad_ratio = advancing / max(declining, 1)
    mcclellan_osc = round(_det_float("breadth_mcclellan", -100.0, 100.0), 2)

    return {
        "universe": total,
        "advancing": advancing,
        "declining": declining,
        "unchanged": total - advancing - declining,
        "ad_ratio": round(ad_ratio, 3),
        "ad_line": round(_det_float("breadth_adline", 5000.0, 15000.0), 0),
        "new_52w_highs": new_highs,
        "new_52w_lows": new_lows,
        "pct_above_50ma": pct_above_50ma,
        "pct_above_200ma": pct_above_200ma,
        "mcclellan_oscillator": mcclellan_osc,
        "breadth_thrust": round(_det_float("breadth_thrust", 40.0, 70.0), 1),
    }


# ---------------------------------------------------------------------------
# Market regime detection
# ---------------------------------------------------------------------------

def get_market_regime() -> Dict[str, Any]:
    """Detect current market regime using synthetic indicator data."""
    breadth = get_market_breadth()
    vix = round(_det_float("regime_vix", 12.0, 35.0), 2)
    spy_return_20d = round(_det_float("regime_spy_20d", -10.0, 10.0), 2)

    # Regime classification rules
    if vix < 15 and breadth["pct_above_200ma"] > 65 and spy_return_20d > 2:
        regime = "BULL_TRENDING"
        regime_label = "Bull Market — Risk-On Trending"
    elif vix < 20 and breadth["pct_above_200ma"] > 55:
        regime = "BULL_CONSOLIDATING"
        regime_label = "Bull Market — Consolidating"
    elif vix > 30 and breadth["pct_above_200ma"] < 40 and spy_return_20d < -5:
        regime = "BEAR_TRENDING"
        regime_label = "Bear Market — Risk-Off Trending"
    elif vix > 25 and breadth["pct_above_200ma"] < 50:
        regime = "HIGH_VOLATILITY"
        regime_label = "High Volatility — Elevated Risk"
    else:
        regime = "NEUTRAL"
        regime_label = "Neutral — Sideways / Mixed Signals"

    # Volatility regime
    if vix < 15:
        vol_regime = "LOW_VOL"
    elif vix < 25:
        vol_regime = "NORMAL_VOL"
    elif vix < 35:
        vol_regime = "HIGH_VOL"
    else:
        vol_regime = "EXTREME_VOL"

    return {
        "regime": regime,
        "regime_label": regime_label,
        "vol_regime": vol_regime,
        "vix": vix,
        "spy_return_20d": spy_return_20d,
        "trend_strength": round(_det_float("regime_trend_str", 0.0, 1.0), 3),
        "momentum_score": round(_det_float("regime_momentum", -1.0, 1.0), 3),
        "risk_on_score": round(_det_float("regime_risk_on", 0.0, 100.0), 1),
        "signals": {
            "breadth_pct_above_200ma": breadth["pct_above_200ma"],
            "ad_ratio": breadth["ad_ratio"],
            "mcclellan_oscillator": breadth["mcclellan_oscillator"],
        },
    }


# ---------------------------------------------------------------------------
# Yield curve
# ---------------------------------------------------------------------------

def get_yield_curve() -> Dict[str, Any]:
    """Return synthetic US Treasury yield curve data."""
    maturities = [
        ("1M", 0.083), ("3M", 0.25), ("6M", 0.5), ("1Y", 1),
        ("2Y", 2), ("3Y", 3), ("5Y", 5), ("7Y", 7),
        ("10Y", 10), ("20Y", 20), ("30Y", 30),
    ]

    base_rate = _det_float("yc_base", 4.0, 5.5)
    points = []
    for label, years in maturities:
        # Simplified Nelson-Siegel style curve
        spread = 0.5 * (1 - math.exp(-years / 2)) + 0.3 * ((years / 2) * math.exp(-years / 2))
        rate = round(base_rate + spread * _det_float(f"yc_{label}", -0.3, 0.3), 3)
        points.append({"maturity": label, "years": years, "yield": rate})

    spread_2s10s = round(
        next(p["yield"] for p in points if p["maturity"] == "10Y") -
        next(p["yield"] for p in points if p["maturity"] == "2Y"),
        3,
    )
    spread_3m10y = round(
        next(p["yield"] for p in points if p["maturity"] == "10Y") -
        next(p["yield"] for p in points if p["maturity"] == "3M"),
        3,
    )
    inverted = spread_2s10s < 0

    return {
        "curve": points,
        "spread_2s10s": spread_2s10s,
        "spread_3m10y": spread_3m10y,
        "is_inverted": inverted,
        "curve_shape": "inverted" if inverted else "normal" if spread_2s10s > 0.5 else "flat",
        "fed_funds_rate": round(base_rate, 3),
    }


# ---------------------------------------------------------------------------
# Global macro indicators
# ---------------------------------------------------------------------------

def get_global_macro() -> Dict[str, Any]:
    """Return synthetic global macro indicators."""
    return {
        "us": {
            "gdp_growth_yoy": round(_det_float("macro_us_gdp", 1.0, 3.5), 2),
            "cpi_yoy": round(_det_float("macro_us_cpi", 2.0, 5.0), 2),
            "unemployment": round(_det_float("macro_us_ue", 3.5, 5.0), 2),
            "pmi_manufacturing": round(_det_float("macro_us_pmi_m", 48.0, 58.0), 1),
            "pmi_services": round(_det_float("macro_us_pmi_s", 50.0, 60.0), 1),
            "consumer_confidence": round(_det_float("macro_us_cc", 95.0, 115.0), 1),
        },
        "global": {
            "world_gdp_growth": round(_det_float("macro_wld_gdp", 2.5, 4.0), 2),
            "global_pmi": round(_det_float("macro_wld_pmi", 49.0, 55.0), 1),
            "trade_balance_usd_bn": round(_det_float("macro_wld_trade", -70.0, -20.0), 1),
            "dollar_index_dxy": round(_det_float("macro_dxy", 98.0, 108.0), 2),
            "gold_price": round(_det_float("macro_gold", 1900.0, 2500.0), 2),
            "oil_brent": round(_det_float("macro_oil", 70.0, 100.0), 2),
        },
        "central_banks": {
            "fed_rate": round(_det_float("macro_fed", 4.25, 5.50), 2),
            "ecb_rate": round(_det_float("macro_ecb", 3.0, 4.5), 2),
            "boe_rate": round(_det_float("macro_boe", 4.5, 5.5), 2),
            "boj_rate": round(_det_float("macro_boj", -0.1, 0.5), 2),
        },
    }


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

def get_correlation_matrix(tickers: List[str]) -> Dict[str, Any]:
    """Return deterministic pairwise correlation matrix for the given tickers."""
    n = len(tickers)
    matrix: List[List[float]] = []
    for i, t1 in enumerate(tickers):
        row = []
        for j, t2 in enumerate(tickers):
            if i == j:
                row.append(1.0)
            else:
                key = f"corr_{min(t1, t2)}_{max(t1, t2)}"
                corr = round(_det_float(key, -0.3, 0.95), 3)
                row.append(corr)
        matrix.append(row)

    return {
        "tickers": tickers,
        "matrix": matrix,
        "n": n,
    }


# ---------------------------------------------------------------------------
# Liquidity metrics
# ---------------------------------------------------------------------------

def get_liquidity_metrics(ticker: str) -> Dict[str, Any]:
    """Return synthetic liquidity metrics for a ticker."""
    return {
        "ticker": ticker,
        "avg_daily_volume": int(_det_float(f"liq_{ticker}_vol", 1e6, 100e6)),
        "bid_ask_spread_bps": round(_det_float(f"liq_{ticker}_spread", 1.0, 20.0), 2),
        "market_depth_1pct": round(_det_float(f"liq_{ticker}_depth", 0.5e6, 10e6), 0),
        "turnover_ratio": round(_det_float(f"liq_{ticker}_turnover", 0.5, 5.0), 3),
        "amihud_illiquidity": round(_det_float(f"liq_{ticker}_amihud", 0.0, 0.1), 6),
        "liquidity_score": round(_det_float(f"liq_{ticker}_score", 40.0, 95.0), 1),
        "liquidity_category": "HIGH" if _det_float(f"liq_{ticker}_cat", 0, 1) > 0.6 else "MEDIUM",
    }
