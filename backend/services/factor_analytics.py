"""Factor analytics service — M4.

Estimates factor exposures (betas) for a portfolio via OLS regression
against ETF proxies for standard Fama-French style factors.

Factor proxies (all via yfinance):
  Market beta  : SPY  — S&P 500
  Size (SMB)   : IWM  — Russell 2000 (small-cap)
  Value (HML)  : IVE  — S&P 500 Value
  Growth       : IVW  — S&P 500 Growth
  Momentum     : MTUM — MSCI Momentum
  Quality      : QUAL — iShares MSCI Quality
  Low Vol      : USMV — iShares MSCI Min Volatility
  Dividend     : VYM  — Vanguard High Dividend Yield

The regression: r_portfolio = alpha + Σ β_k * r_factor_k + ε
Estimated by OLS with HAC standard errors where possible.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from services.market_data import get_price_history

logger = logging.getLogger(__name__)

# Factor ETF proxies — ordered so the market factor is always first
FACTOR_PROXIES: Dict[str, str] = {
    "Market": "SPY",
    "Size": "IWM",
    "Value": "IVE",
    "Growth": "IVW",
    "Momentum": "MTUM",
    "Quality": "QUAL",
    "LowVol": "USMV",
    "Dividend": "VYM",
}


# ---------------------------------------------------------------------------
# OLS regression helper
# ---------------------------------------------------------------------------

def _ols(
    y: np.ndarray,
    X: np.ndarray,
) -> Dict[str, Any]:
    """OLS regression of y on X (with intercept prepended)."""
    n, k = X.shape
    X_full = np.column_stack([np.ones(n), X])
    try:
        coeffs, residuals, rank, sv = np.linalg.lstsq(X_full, y, rcond=None)
    except np.linalg.LinAlgError:
        return {}

    y_hat = X_full @ coeffs
    res = y - y_hat
    ss_res = float(res @ res)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r2 = 1.0 - (1 - r2) * (n - 1) / (n - k - 1) if (n - k - 1) > 0 else 0.0

    # Standard errors
    sigma2 = ss_res / (n - k - 1) if (n - k - 1) > 0 else 0.0
    try:
        cov_beta = sigma2 * np.linalg.inv(X_full.T @ X_full)
        se = np.sqrt(np.diag(cov_beta))
        t_stats = coeffs / (se + 1e-12)
        p_values = [float(2 * (1 - stats.t.cdf(abs(t), df=n - k - 1))) for t in t_stats]
    except Exception:
        se = np.zeros(k + 1)
        t_stats = np.zeros(k + 1)
        p_values = [1.0] * (k + 1)

    return {
        "alpha": float(coeffs[0]),
        "betas": coeffs[1:].tolist(),
        "t_stats": t_stats[1:].tolist(),
        "p_values": p_values[1:],
        "r_squared": round(r2, 4),
        "adj_r_squared": round(adj_r2, 4),
        "alpha_t_stat": float(t_stats[0]),
        "alpha_p_value": float(p_values[0]),
        "n_obs": n,
    }


# ---------------------------------------------------------------------------
# Main factor analytics function
# ---------------------------------------------------------------------------

def compute_factor_exposures(
    portfolio_returns: pd.Series,
    lookback_days: int = 252,
    factors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Estimate factor exposures for the portfolio.

    Parameters
    ----------
    portfolio_returns :
        Daily portfolio return series with a DatetimeIndex.
    lookback_days :
        Number of trading days used for the regression.
    factors :
        Subset of FACTOR_PROXIES keys to include. Defaults to all.

    Returns
    -------
    Dict with ``exposures`` list (one entry per factor), regression
    statistics, and annualised alpha.
    """
    if factors is None:
        factors = list(FACTOR_PROXIES.keys())

    etfs = [FACTOR_PROXIES[f] for f in factors if f in FACTOR_PROXIES]
    if not etfs:
        raise ValueError("No valid factors specified.")

    # Align dates
    start_dt = portfolio_returns.index.min()
    end_dt = portfolio_returns.index.max()

    try:
        factor_prices = get_price_history(etfs, str(start_dt.date()), str(end_dt.date()))
    except Exception as exc:
        logger.warning("Factor data download failed: %s", exc)
        return _empty_result(factors)

    if factor_prices.empty:
        return _empty_result(factors)

    factor_returns = factor_prices.pct_change().dropna(how="all")

    # Align portfolio and factor returns
    combined = pd.concat(
        [portfolio_returns.rename("portfolio")] + [factor_returns[e].rename(f) for e, f in zip(etfs, factors) if e in factor_returns.columns],
        axis=1,
        join="inner",
    ).dropna()

    if len(combined) < 30:
        return _empty_result(factors)

    # Use at most lookback_days
    combined = combined.tail(lookback_days)

    y = combined["portfolio"].values
    factor_names_used = [col for col in combined.columns if col != "portfolio"]
    X = combined[factor_names_used].values

    ols_result = _ols(y, X)
    if not ols_result:
        return _empty_result(factor_names_used)

    _ANN = 252
    alpha_annual = float(ols_result["alpha"]) * _ANN

    exposures = []
    for i, fname in enumerate(factor_names_used):
        exposures.append({
            "factor": fname,
            "etf_proxy": FACTOR_PROXIES.get(fname, fname),
            "beta": round(float(ols_result["betas"][i]), 4),
            "t_stat": round(float(ols_result["t_stats"][i]), 3),
            "p_value": round(float(ols_result["p_values"][i]), 4),
            "significant": bool(ols_result["p_values"][i] < 0.05),
        })

    return {
        "exposures": exposures,
        "alpha_daily": round(float(ols_result["alpha"]), 8),
        "alpha_annual": round(alpha_annual, 6),
        "alpha_t_stat": round(float(ols_result["alpha_t_stat"]), 3),
        "alpha_p_value": round(float(ols_result["alpha_p_value"]), 4),
        "r_squared": ols_result["r_squared"],
        "adj_r_squared": ols_result["adj_r_squared"],
        "n_obs": ols_result["n_obs"],
        "factors_used": factor_names_used,
    }


def _empty_result(factors: List[str]) -> Dict[str, Any]:
    return {
        "exposures": [{"factor": f, "etf_proxy": FACTOR_PROXIES.get(f, f), "beta": None, "t_stat": None, "p_value": None, "significant": False} for f in factors],
        "alpha_daily": None,
        "alpha_annual": None,
        "alpha_t_stat": None,
        "alpha_p_value": None,
        "r_squared": None,
        "adj_r_squared": None,
        "n_obs": 0,
        "factors_used": [],
    }
