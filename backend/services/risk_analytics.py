"""Risk analytics service — M4.

Computes institutional-grade risk metrics from a portfolio's return series.
All computation is pure NumPy/SciPy — no external data calls inside the
core functions (callers must pass prepared DataFrames).

Key metrics implemented:
- VaR: Historical, Parametric (Normal), Monte Carlo
- CVaR / Expected Shortfall
- Volatility (annual), Downside Deviation, Semi-Variance
- Sharpe, Sortino, Treynor, Calmar, Information Ratio, Ulcer Index
- Max Drawdown, Ulcer Index
- Beta, Alpha, R² vs benchmark
- HHI (Herfindahl-Hirschman Concentration Index)
- Diversification Ratio
- Marginal / Component / Percentage Risk Contributions
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy.orm import Session

from config import settings
from services.market_data import get_price_history

logger = logging.getLogger(__name__)

# Annualisation factor (trading days per year)
_ANN = 252
_RFR = settings.risk_free_rate_annual


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_returns(series: pd.Series) -> pd.Series:
    """Drop NaN/Inf and convert to float64."""
    return series.replace([np.inf, -np.inf], np.nan).dropna().astype(float)


def _portfolio_returns(
    weights: np.ndarray,
    returns_df: pd.DataFrame,
) -> pd.Series:
    """Weighted sum of asset returns → portfolio daily return series."""
    return returns_df.dot(weights)


# ---------------------------------------------------------------------------
# VaR / CVaR
# ---------------------------------------------------------------------------

def var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    """Historical VaR at *confidence* level (negative number = loss).

    Returns a positive number representing the loss threshold as a fraction
    of portfolio value.  e.g. 0.025 means 2.5% of portfolio at risk.
    """
    r = _clean_returns(returns)
    if len(r) == 0:
        return 0.0
    return float(-np.percentile(r, (1 - confidence) * 100))


def var_parametric(returns: pd.Series, confidence: float = 0.95) -> float:
    """Parametric (Normal) VaR at *confidence* level."""
    r = _clean_returns(returns)
    if len(r) < 2:
        return 0.0
    mu = r.mean()
    sigma = r.std(ddof=1)
    z = stats.norm.ppf(1 - confidence)
    return float(-(mu + z * sigma))


def var_monte_carlo(
    returns: pd.Series,
    confidence: float = 0.95,
    n_sims: int = 10_000,
    horizon: int = 1,
) -> float:
    """Monte Carlo VaR via GBM.

    Simulates ``n_sims`` paths of ``horizon`` days using the empirical
    mean and std of ``returns``.  Returns 1-day VaR by default.
    """
    r = _clean_returns(returns)
    if len(r) < 2:
        return 0.0
    mu = r.mean()
    sigma = r.std(ddof=1)
    rng = np.random.default_rng(seed=42)
    sim = rng.normal(mu, sigma, (n_sims, horizon)).sum(axis=1)
    return float(-np.percentile(sim, (1 - confidence) * 100))


def cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """Conditional VaR (Expected Shortfall) — mean of returns below VaR."""
    r = _clean_returns(returns)
    if len(r) == 0:
        return 0.0
    threshold = np.percentile(r, (1 - confidence) * 100)
    tail = r[r <= threshold]
    return float(-tail.mean()) if len(tail) > 0 else 0.0


# ---------------------------------------------------------------------------
# Volatility & downside risk
# ---------------------------------------------------------------------------

def annual_volatility(returns: pd.Series) -> float:
    """Annualised standard deviation of daily returns."""
    r = _clean_returns(returns)
    return float(r.std(ddof=1) * np.sqrt(_ANN)) if len(r) > 1 else 0.0


def downside_deviation(returns: pd.Series, mar: float = 0.0) -> float:
    """Annualised downside deviation below *mar* (minimum acceptable return).

    Uses daily MAR (annual_mar / 252).
    """
    r = _clean_returns(returns)
    daily_mar = mar / _ANN
    downside = r[r < daily_mar] - daily_mar
    if len(downside) == 0:
        return 0.0
    return float(np.sqrt((downside ** 2).mean()) * np.sqrt(_ANN))


def semi_variance(returns: pd.Series) -> float:
    """Annualised semi-variance (variance of negative returns only)."""
    r = _clean_returns(returns)
    neg = r[r < 0]
    if len(neg) == 0:
        return 0.0
    return float((neg ** 2).mean() * _ANN)


def ulcer_index(nav: pd.Series) -> float:
    """Ulcer Index — quadratic drawdown depth measure.

    ``nav`` should be a price/NAV series (not returns).
    """
    if len(nav) < 2:
        return 0.0
    peak = nav.cummax()
    drawdown_pct = ((nav - peak) / peak) * 100.0
    return float(np.sqrt((drawdown_pct ** 2).mean()))


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------

def max_drawdown(nav: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a positive fraction (0–1)."""
    if len(nav) < 2:
        return 0.0
    peak = nav.cummax()
    dd = (nav - peak) / peak
    return float(-dd.min())


# ---------------------------------------------------------------------------
# Risk-adjusted return ratios
# ---------------------------------------------------------------------------

def sharpe_ratio(returns: pd.Series, risk_free_annual: float = _RFR) -> float:
    """Annualised Sharpe ratio."""
    r = _clean_returns(returns)
    if len(r) < 2:
        return 0.0
    daily_rf = risk_free_annual / _ANN
    excess = r - daily_rf
    vol = excess.std(ddof=1)
    if vol < 1e-12:
        return 0.0
    return float((excess.mean() / vol) * np.sqrt(_ANN))


def sortino_ratio(returns: pd.Series, risk_free_annual: float = _RFR) -> float:
    """Annualised Sortino ratio using downside deviation as denominator."""
    r = _clean_returns(returns)
    if len(r) < 2:
        return 0.0
    daily_rf = risk_free_annual / _ANN
    excess_mean = (r - daily_rf).mean() * _ANN
    dd = downside_deviation(r, mar=risk_free_annual)
    if dd == 0:
        return 0.0
    return float(excess_mean / dd)


def calmar_ratio(returns: pd.Series, nav: pd.Series) -> float:
    """Calmar ratio: annualised return / max drawdown."""
    r = _clean_returns(returns)
    if len(r) < 2:
        return 0.0
    ann_ret = (1 + r.mean()) ** _ANN - 1
    mdd = max_drawdown(nav)
    if mdd == 0:
        return 0.0
    return float(ann_ret / mdd)


def treynor_ratio(returns: pd.Series, benchmark_returns: pd.Series, risk_free_annual: float = _RFR) -> float:
    """Treynor ratio: excess return per unit of beta."""
    r = _clean_returns(returns)
    b = _clean_returns(benchmark_returns)
    if len(r) < 2 or len(b) < 2:
        return 0.0
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return 0.0
    beta_val = _beta(aligned.iloc[:, 0], aligned.iloc[:, 1])
    if beta_val == 0:
        return 0.0
    daily_rf = risk_free_annual / _ANN
    ann_ret = (1 + aligned.iloc[:, 0].mean()) ** _ANN - 1
    ann_rf = risk_free_annual
    return float((ann_ret - ann_rf) / beta_val)


def information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Annualised Information Ratio: active return / tracking error."""
    r = _clean_returns(returns)
    b = _clean_returns(benchmark_returns)
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return 0.0
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    te = active.std(ddof=1) * np.sqrt(_ANN)
    if te == 0:
        return 0.0
    return float(active.mean() * _ANN / te)


# ---------------------------------------------------------------------------
# Benchmark statistics
# ---------------------------------------------------------------------------

def _beta(portfolio_r: pd.Series, benchmark_r: pd.Series) -> float:
    """OLS beta of portfolio vs benchmark."""
    cov_mat = np.cov(portfolio_r, benchmark_r)
    bench_var = cov_mat[1, 1]
    if bench_var == 0:
        return 0.0
    return float(cov_mat[0, 1] / bench_var)


def beta_alpha(returns: pd.Series, benchmark_returns: pd.Series, risk_free_annual: float = _RFR) -> Tuple[float, float]:
    """Returns (beta, annualised alpha)."""
    r = _clean_returns(returns)
    b = _clean_returns(benchmark_returns)
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return 0.0, 0.0
    pr = aligned.iloc[:, 0]
    br = aligned.iloc[:, 1]
    beta_val = _beta(pr, br)
    daily_rf = risk_free_annual / _ANN
    alpha_daily = pr.mean() - (daily_rf + beta_val * (br.mean() - daily_rf))
    alpha_annual = float(alpha_daily * _ANN)
    return float(beta_val), alpha_annual


def r_squared(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Coefficient of determination (R²) vs benchmark."""
    r = _clean_returns(returns)
    b = _clean_returns(benchmark_returns)
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return 0.0
    corr = np.corrcoef(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1]
    return float(corr ** 2)


def tracking_error(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Annualised tracking error (std of active returns)."""
    r = _clean_returns(returns)
    b = _clean_returns(benchmark_returns)
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return 0.0
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return float(active.std(ddof=1) * np.sqrt(_ANN))


# ---------------------------------------------------------------------------
# Concentration & diversification
# ---------------------------------------------------------------------------

def herfindahl_hirschman_index(weights: np.ndarray) -> float:
    """HHI concentration index.  0 = perfectly diversified, 1 = fully concentrated."""
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    return float(np.sum(w ** 2))


def diversification_ratio(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """Diversification Ratio: weighted sum of individual vols / portfolio vol."""
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(cov_matrix, dtype=float)
    vols = np.sqrt(np.diag(cov))
    weighted_vol = float(w @ vols)
    port_var = float(w @ cov @ w)
    if port_var <= 0:
        return 1.0
    port_vol = np.sqrt(port_var)
    return float(weighted_vol / port_vol)


# ---------------------------------------------------------------------------
# Risk contributions
# ---------------------------------------------------------------------------

def marginal_risk_contributions(weights: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
    """Marginal contribution to portfolio volatility per unit of weight."""
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(cov_matrix, dtype=float)
    port_var = float(w @ cov @ w)
    if port_var <= 0:
        return np.zeros_like(w)
    port_vol = np.sqrt(port_var)
    return (cov @ w) / port_vol


def component_risk_contributions(weights: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
    """Absolute component risk contribution (weight × marginal contribution)."""
    w = np.asarray(weights, dtype=float)
    mrc = marginal_risk_contributions(w, cov_matrix)
    return w * mrc


def pct_risk_contributions(weights: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
    """Percentage contribution to total portfolio risk (sums to 1)."""
    crc = component_risk_contributions(weights, cov_matrix)
    total = crc.sum()
    if total == 0:
        return np.zeros_like(weights)
    return crc / total


# ---------------------------------------------------------------------------
# Full analytics pipeline
# ---------------------------------------------------------------------------

def compute_full_risk_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    nav: pd.Series,
    weights: Optional[np.ndarray] = None,
    cov_matrix: Optional[np.ndarray] = None,
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute the full suite of risk metrics and return as a dict.

    Parameters
    ----------
    portfolio_returns:
        Daily portfolio return series (decimal, not percentage).
    benchmark_returns:
        Daily benchmark return series aligned to portfolio dates.
    nav:
        Portfolio NAV series (absolute values, not returns).
    weights:
        Current portfolio weights array (must match ``tickers`` order).
    cov_matrix:
        Daily covariance matrix of individual asset returns.
    tickers:
        Ticker symbols corresponding to weights/cov columns.
    """
    pr = _clean_returns(portfolio_returns)
    br = _clean_returns(benchmark_returns)

    beta_val, alpha_val = beta_alpha(pr, br)
    mdd = max_drawdown(nav)

    result: Dict[str, Any] = {
        # VaR
        "var_historical_95": round(var_historical(pr, 0.95), 6),
        "var_historical_99": round(var_historical(pr, 0.99), 6),
        "var_parametric_95": round(var_parametric(pr, 0.95), 6),
        "var_parametric_99": round(var_parametric(pr, 0.99), 6),
        "var_monte_carlo_95": round(var_monte_carlo(pr, 0.95), 6),
        "cvar_95": round(cvar(pr, 0.95), 6),
        "cvar_99": round(cvar(pr, 0.99), 6),
        # Volatility
        "volatility_annual": round(annual_volatility(pr), 6),
        "downside_deviation": round(downside_deviation(pr), 6),
        "semi_variance": round(semi_variance(pr), 8),
        "ulcer_index": round(ulcer_index(nav), 4),
        # Drawdown
        "max_drawdown_pct": round(mdd * 100, 4),
        # Ratios
        "sharpe_ratio": round(sharpe_ratio(pr), 4),
        "sortino_ratio": round(sortino_ratio(pr), 4),
        "calmar_ratio": round(calmar_ratio(pr, nav), 4),
        "treynor_ratio": round(treynor_ratio(pr, br), 4),
        "information_ratio": round(information_ratio(pr, br), 4),
        # Benchmark stats
        "beta": round(beta_val, 4),
        "alpha_annual": round(alpha_val, 6),
        "r_squared": round(r_squared(pr, br), 4),
        "tracking_error": round(tracking_error(pr, br), 6),
    }

    # Concentration metrics — only when weights are provided
    if weights is not None and cov_matrix is not None and tickers is not None:
        w = np.asarray(weights, dtype=float)
        cov = np.asarray(cov_matrix, dtype=float)
        prc = pct_risk_contributions(w, cov)
        crc = component_risk_contributions(w, cov)
        result["hhi"] = round(herfindahl_hirschman_index(w), 6)
        result["diversification_ratio"] = round(diversification_ratio(w, cov), 4)
        result["risk_contributions"] = {
            t: {
                "weight": round(float(w[i]), 6),
                "component_risk": round(float(crc[i]), 6),
                "pct_risk": round(float(prc[i]), 6),
            }
            for i, t in enumerate(tickers)
        }

    return result


# ---------------------------------------------------------------------------
# Data-fetching wrapper (called from the router)
# ---------------------------------------------------------------------------

def fetch_portfolio_data(
    holdings: Dict[str, float],
    lookback_days: int = 252,
    benchmark: str = "SPY",
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Download price history for holdings + benchmark.

    Returns
    -------
    returns_df : pd.DataFrame
        Daily returns for each ticker (columns = tickers).
    portfolio_returns : pd.Series
        Value-weighted daily portfolio return series.
    benchmark_returns : pd.Series
        Daily benchmark return series.
    """
    from datetime import date, timedelta
    import pandas_datareader as _  # noqa — not used, but yfinance import guard

    tickers = list(holdings.keys())
    total_value = sum(holdings.values())
    if total_value == 0:
        raise ValueError("Portfolio has no market value.")

    weights = {t: v / total_value for t, v in holdings.items()}
    all_tickers = tickers + ([benchmark] if benchmark not in tickers else [])

    end = date.today()
    start = end - timedelta(days=lookback_days + 30)

    prices = get_price_history(all_tickers, start.isoformat(), end.isoformat())
    if prices.empty:
        raise ValueError("No price data returned.")

    prices = prices.ffill().dropna(how="all")
    rets = prices.pct_change().dropna(how="all")

    bench_col = benchmark if benchmark in rets.columns else rets.columns[-1]
    benchmark_rets = rets[bench_col]

    asset_cols = [t for t in tickers if t in rets.columns]
    rets_assets = rets[asset_cols]

    w_array = np.array([weights.get(t, 0.0) for t in asset_cols])
    w_array /= w_array.sum()  # renormalise after any missing tickers

    port_rets = _portfolio_returns(w_array, rets_assets)

    return rets_assets, port_rets, benchmark_rets
