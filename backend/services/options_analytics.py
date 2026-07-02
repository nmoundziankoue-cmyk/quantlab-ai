"""Options analytics engine — Black-Scholes, Greeks, IV surface, max pain (M7).

All computations are pure math with no external market data dependencies.
Uses scipy.stats for the normal distribution (already installed from M4).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from scipy.stats import norm

# Default risk-free rate (annualised)
_RF = 0.05


# ---------------------------------------------------------------------------
# Core Black-Scholes implementation
# ---------------------------------------------------------------------------

def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
    """Return (d1, d2) for Black-Scholes. T in years."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0, 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def black_scholes_price(
    S: float, K: float, T: float, sigma: float, option_type: str = "CALL", r: float = _RF
) -> float:
    """Return theoretical option price using Black-Scholes formula."""
    if T <= 0:
        if option_type.upper() == "CALL":
            return max(0.0, S - K)
        return max(0.0, K - S)
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    disc = math.exp(-r * T)
    if option_type.upper() == "CALL":
        return S * norm.cdf(d1) - K * disc * norm.cdf(d2)
    # PUT
    return K * disc * norm.cdf(-d2) - S * norm.cdf(-d1)


def calculate_greeks(
    S: float, K: float, T: float, sigma: float, option_type: str = "CALL", r: float = _RF
) -> Dict[str, float]:
    """Return all five option Greeks."""
    if T <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    d1, d2 = _d1_d2(S, K, T, r, sigma)
    pdf_d1 = norm.pdf(d1)
    disc = math.exp(-r * T)
    sqrt_T = math.sqrt(T)

    gamma = pdf_d1 / (S * sigma * sqrt_T)
    vega = S * pdf_d1 * sqrt_T / 100  # per 1% change in vol

    if option_type.upper() == "CALL":
        delta = norm.cdf(d1)
        theta = (
            -(S * pdf_d1 * sigma) / (2 * sqrt_T)
            - r * K * disc * norm.cdf(d2)
        ) / 365
        rho = K * T * disc * norm.cdf(d2) / 100
    else:
        delta = norm.cdf(d1) - 1
        theta = (
            -(S * pdf_d1 * sigma) / (2 * sqrt_T)
            + r * K * disc * norm.cdf(-d2)
        ) / 365
        rho = -K * T * disc * norm.cdf(-d2) / 100

    return {
        "delta": round(delta, 6),
        "gamma": round(gamma, 6),
        "theta": round(theta, 6),
        "vega": round(vega, 6),
        "rho": round(rho, 6),
    }


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    option_type: str = "CALL",
    r: float = _RF,
    tol: float = 1e-6,
    max_iter: int = 200,
) -> Optional[float]:
    """Return implied volatility via Newton-Raphson bisection.

    Returns None if no valid IV can be found.
    """
    if T <= 0 or market_price <= 0:
        return None

    sigma = 0.3  # initial guess
    for _ in range(max_iter):
        price = black_scholes_price(S, K, T, sigma, option_type, r)
        d1, _ = _d1_d2(S, K, T, r, sigma)
        vega_raw = S * norm.pdf(d1) * math.sqrt(T)
        if abs(vega_raw) < 1e-10:
            break
        diff = market_price - price
        sigma += diff / vega_raw
        sigma = max(0.001, min(sigma, 20.0))
        if abs(diff) < tol:
            return round(sigma, 6)
    return None


# ---------------------------------------------------------------------------
# Options chain
# ---------------------------------------------------------------------------

def options_chain(
    ticker: str,
    underlying_price: float,
    strikes: Optional[List[float]] = None,
    expiry_days_list: Optional[List[int]] = None,
    r: float = _RF,
) -> Dict[str, Any]:
    """Return a full options chain for the given ticker and parameters."""
    if strikes is None:
        # ATM ± 10% in 5% increments
        strikes = [
            round(underlying_price * m, 2)
            for m in [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
        ]
    if expiry_days_list is None:
        expiry_days_list = [7, 14, 30, 60, 90, 180]

    chain: List[Dict[str, Any]] = []
    for exp_days in expiry_days_list:
        T = exp_days / 365.0
        # Base IV: ATM ~25%, skew towards OTM puts
        atm_iv = 0.25
        for strike in strikes:
            moneyness = strike / underlying_price
            # Skew: OTM puts get higher IV, OTM calls get lower
            iv_adjustment = 0.05 * (1.0 - moneyness)
            iv = max(0.05, atm_iv + iv_adjustment)

            for opt_type in ("CALL", "PUT"):
                price = black_scholes_price(underlying_price, strike, T, iv, opt_type, r)
                greeks = calculate_greeks(underlying_price, strike, T, iv, opt_type, r)
                # Synthetic open interest (deterministic)
                oi = int(1000 * math.exp(-0.5 * ((moneyness - 1.0) / 0.1) ** 2) * (1 + exp_days / 30))
                chain.append({
                    "ticker": ticker,
                    "option_type": opt_type,
                    "strike": strike,
                    "expiry_days": exp_days,
                    "expiry_label": f"{exp_days}D",
                    "implied_vol": round(iv, 4),
                    "theoretical_price": round(price, 4),
                    "open_interest": oi,
                    **greeks,
                })
    return {
        "ticker": ticker,
        "underlying_price": underlying_price,
        "risk_free_rate": r,
        "chain": chain,
        "total_contracts": len(chain),
    }


# ---------------------------------------------------------------------------
# IV Surface
# ---------------------------------------------------------------------------

def iv_surface(
    ticker: str,
    underlying_price: float,
    strike_pcts: Optional[List[float]] = None,
    expiry_days_list: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Return a volatility surface as a 2D grid."""
    if strike_pcts is None:
        strike_pcts = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
    if expiry_days_list is None:
        expiry_days_list = [7, 14, 30, 60, 90, 180, 365]

    strikes = [round(underlying_price * p, 2) for p in strike_pcts]
    atm_iv = 0.25
    surface: List[List[float]] = []
    for exp_days in expiry_days_list:
        # Term structure: shorter expiry → higher IV (vol term structure)
        term_adj = 0.05 * math.exp(-exp_days / 90)
        row = []
        for p in strike_pcts:
            skew_adj = 0.05 * (1.0 - p)  # put skew
            iv = round(max(0.05, atm_iv + term_adj + skew_adj), 4)
            row.append(iv)
        surface.append(row)

    return {
        "ticker": ticker,
        "underlying_price": underlying_price,
        "strikes": strikes,
        "strike_pcts": strike_pcts,
        "expiry_days": expiry_days_list,
        "surface": surface,
        "atm_iv": atm_iv,
    }


# ---------------------------------------------------------------------------
# Max Pain
# ---------------------------------------------------------------------------

def max_pain(
    strikes: List[float],
    calls_oi: List[int],
    puts_oi: List[int],
) -> Dict[str, Any]:
    """Calculate max pain — the strike at which total option loss is minimised."""
    if not strikes or len(strikes) != len(calls_oi) or len(strikes) != len(puts_oi):
        return {"max_pain_strike": None, "pain_by_strike": []}

    pain_by_strike = []
    for expiry_strike in strikes:
        total_pain = 0.0
        for i, s in enumerate(strikes):
            call_pain = calls_oi[i] * max(0.0, expiry_strike - s)
            put_pain = puts_oi[i] * max(0.0, s - expiry_strike)
            total_pain += call_pain + put_pain
        pain_by_strike.append({"strike": expiry_strike, "total_pain": round(total_pain, 2)})

    min_pain = min(pain_by_strike, key=lambda x: x["total_pain"])
    return {
        "max_pain_strike": min_pain["strike"],
        "min_pain_value": min_pain["total_pain"],
        "pain_by_strike": pain_by_strike,
    }


# ---------------------------------------------------------------------------
# Expected Move
# ---------------------------------------------------------------------------

def expected_move(
    underlying_price: float,
    atm_iv: float,
    expiry_days: int,
) -> Dict[str, float]:
    """Return expected move (1σ) for the given expiry."""
    T = expiry_days / 365.0
    one_sigma = underlying_price * atm_iv * math.sqrt(T)
    return {
        "underlying_price": underlying_price,
        "atm_iv": atm_iv,
        "expiry_days": expiry_days,
        "expected_move_1sigma": round(one_sigma, 4),
        "upper_bound_1sigma": round(underlying_price + one_sigma, 4),
        "lower_bound_1sigma": round(underlying_price - one_sigma, 4),
        "expected_move_2sigma": round(2 * one_sigma, 4),
        "upper_bound_2sigma": round(underlying_price + 2 * one_sigma, 4),
        "lower_bound_2sigma": round(underlying_price - 2 * one_sigma, 4),
        "pct_move_1sigma": round(one_sigma / underlying_price * 100, 4),
    }


# ---------------------------------------------------------------------------
# Gamma Exposure (GEX)
# ---------------------------------------------------------------------------

def gamma_exposure(
    chain_items: List[Dict[str, Any]],
    underlying_price: float,
) -> Dict[str, Any]:
    """Aggregate gamma exposure across the options chain."""
    gex_by_strike: Dict[float, float] = {}
    for item in chain_items:
        strike = item.get("strike", 0.0)
        gamma = item.get("gamma", 0.0)
        oi = item.get("open_interest", 0)
        sign = 1.0 if item.get("option_type") == "CALL" else -1.0
        # GEX = gamma * OI * 100 (contract multiplier) * underlying^2 / 100
        gex = sign * gamma * oi * 100 * underlying_price ** 2 / 100
        gex_by_strike[strike] = gex_by_strike.get(strike, 0.0) + gex

    sorted_gex = sorted(gex_by_strike.items())
    total_gex = sum(gex_by_strike.values())
    zero_gamma_strike = None
    for i in range(len(sorted_gex) - 1):
        s1, g1 = sorted_gex[i]
        s2, g2 = sorted_gex[i + 1]
        if g1 * g2 < 0:
            zero_gamma_strike = round(s1 + (s2 - s1) * abs(g1) / (abs(g1) + abs(g2)), 2)
            break

    return {
        "total_gex": round(total_gex, 2),
        "zero_gamma_strike": zero_gamma_strike,
        "gex_by_strike": [{"strike": s, "gex": round(g, 2)} for s, g in sorted_gex],
    }


# ---------------------------------------------------------------------------
# Volatility skew
# ---------------------------------------------------------------------------

def volatility_skew(
    underlying_price: float,
    atm_iv: float = 0.25,
    expiry_days: int = 30,
    r: float = _RF,
) -> Dict[str, Any]:
    """Return volatility skew metrics: 25Δ put/call skew and risk reversal."""
    T = expiry_days / 365.0

    def find_delta_strike(target_delta: float, opt_type: str) -> Tuple[float, float]:
        lo, hi = underlying_price * 0.5, underlying_price * 1.5
        for _ in range(100):
            mid = (lo + hi) / 2
            skew_adj = 0.05 * (1.0 - mid / underlying_price)
            iv = max(0.05, atm_iv + skew_adj)
            greeks = calculate_greeks(underlying_price, mid, T, iv, opt_type, r)
            delta = abs(greeks["delta"])
            if abs(delta - target_delta) < 0.001:
                return mid, iv
            if opt_type == "CALL":
                if delta > target_delta:
                    lo = mid
                else:
                    hi = mid
            else:
                if delta < target_delta:
                    lo = mid
                else:
                    hi = mid
        return mid, atm_iv

    put_25d_strike, put_25d_iv = find_delta_strike(0.25, "PUT")
    call_25d_strike, call_25d_iv = find_delta_strike(0.25, "CALL")

    return {
        "atm_iv": atm_iv,
        "put_25d_strike": round(put_25d_strike, 2),
        "put_25d_iv": round(put_25d_iv, 4),
        "call_25d_strike": round(call_25d_strike, 2),
        "call_25d_iv": round(call_25d_iv, 4),
        "risk_reversal_25d": round(call_25d_iv - put_25d_iv, 4),
        "skew_slope": round((put_25d_iv - atm_iv) / (underlying_price - put_25d_strike + 1e-10), 6),
    }
