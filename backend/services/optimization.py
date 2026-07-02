"""Portfolio optimization service — M4.

Implements multiple optimization strategies using SciPy.  All methods
return a dict with ``weights``, ``expected_return``, ``expected_volatility``,
and ``sharpe_ratio`` so callers get a uniform interface.

Methods implemented:
- equal_weight
- min_variance
- max_sharpe
- risk_parity
- hierarchical_risk_parity (HRP)
- max_diversification
- efficient_frontier (returns a list of points)

Black-Litterman view-mixing is exposed as a separate helper that
transforms the prior return vector before running MVO.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from config import settings

logger = logging.getLogger(__name__)

_ANN = 252
_RFR = settings.risk_free_rate_annual
_EPS = 1e-8


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _port_stats(
    weights: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
) -> Tuple[float, float, float]:
    """Return (expected_return_annual, volatility_annual, sharpe)."""
    ret = float(weights @ mu) * _ANN
    var = float(weights @ cov @ weights) * _ANN
    vol = np.sqrt(max(var, 0.0))
    sharpe = (ret - _RFR) / vol if vol > _EPS else 0.0
    return ret, vol, sharpe


def _default_constraints(n: int) -> List[Dict]:
    return [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]


def _default_bounds(n: int) -> List[Tuple]:
    return [(0.0, 1.0)] * n


def _w0(n: int) -> np.ndarray:
    return np.full(n, 1.0 / n)


# ---------------------------------------------------------------------------
# Equal weight
# ---------------------------------------------------------------------------

def equal_weight(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
) -> Dict[str, Any]:
    """Equal-weight portfolio (1/N)."""
    n = len(tickers)
    w = _w0(n)
    ret, vol, sharpe = _port_stats(w, mu, cov)
    return {
        "method": "equal_weight",
        "weights": dict(zip(tickers, w.tolist())),
        "expected_return": round(ret, 6),
        "expected_volatility": round(vol, 6),
        "sharpe_ratio": round(sharpe, 4),
    }


# ---------------------------------------------------------------------------
# Minimum variance
# ---------------------------------------------------------------------------

def min_variance(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    long_only: bool = True,
) -> Dict[str, Any]:
    """Minimum variance portfolio."""
    n = len(tickers)
    bounds = _default_bounds(n) if long_only else [(-1.0, 1.0)] * n

    def portfolio_vol(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    result = minimize(
        portfolio_vol,
        _w0(n),
        method="SLSQP",
        bounds=bounds,
        constraints=_default_constraints(n),
        options={"ftol": 1e-12, "maxiter": 500},
    )
    w = result.x
    ret, vol, sharpe = _port_stats(w, mu, cov)
    return {
        "method": "min_variance",
        "weights": dict(zip(tickers, w.tolist())),
        "expected_return": round(ret, 6),
        "expected_volatility": round(vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "converged": bool(result.success),
    }


# ---------------------------------------------------------------------------
# Maximum Sharpe (Tangency portfolio)
# ---------------------------------------------------------------------------

def max_sharpe(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    risk_free: float = _RFR,
    long_only: bool = True,
) -> Dict[str, Any]:
    """Maximum Sharpe ratio portfolio."""
    n = len(tickers)
    bounds = _default_bounds(n) if long_only else [(-1.0, 1.0)] * n
    daily_rf = risk_free / _ANN

    def neg_sharpe(w: np.ndarray) -> float:
        ret = float(w @ mu)
        var = float(w @ cov @ w)
        vol = np.sqrt(max(var, 0.0))
        if vol < _EPS:
            return 0.0
        return -(ret - daily_rf) / vol

    result = minimize(
        neg_sharpe,
        _w0(n),
        method="SLSQP",
        bounds=bounds,
        constraints=_default_constraints(n),
        options={"ftol": 1e-12, "maxiter": 500},
    )
    w = result.x
    ret, vol, sharpe = _port_stats(w, mu, cov)
    return {
        "method": "max_sharpe",
        "weights": dict(zip(tickers, w.tolist())),
        "expected_return": round(ret, 6),
        "expected_volatility": round(vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "converged": bool(result.success),
    }


# ---------------------------------------------------------------------------
# Risk Parity
# ---------------------------------------------------------------------------

def risk_parity(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
) -> Dict[str, Any]:
    """Equal risk contribution (Risk Parity) portfolio."""
    n = len(tickers)
    target = np.ones(n) / n  # each asset contributes equally to total risk

    def risk_budget_objective(w: np.ndarray) -> float:
        port_var = float(w @ cov @ w)
        if port_var <= 0:
            return 1e10
        mrc = cov @ w / np.sqrt(port_var)
        crc = w * mrc
        total_risk = crc.sum()
        pct_crc = crc / total_risk
        return float(np.sum((pct_crc - target) ** 2))

    result = minimize(
        risk_budget_objective,
        _w0(n),
        method="SLSQP",
        bounds=_default_bounds(n),
        constraints=_default_constraints(n),
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    w = np.abs(result.x)
    w /= w.sum()
    ret, vol, sharpe = _port_stats(w, mu, cov)
    return {
        "method": "risk_parity",
        "weights": dict(zip(tickers, w.tolist())),
        "expected_return": round(ret, 6),
        "expected_volatility": round(vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "converged": bool(result.success),
    }


# ---------------------------------------------------------------------------
# Maximum Diversification
# ---------------------------------------------------------------------------

def max_diversification(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
) -> Dict[str, Any]:
    """Maximum Diversification Ratio portfolio."""
    n = len(tickers)
    vols = np.sqrt(np.diag(cov))

    def neg_dr(w: np.ndarray) -> float:
        weighted_avg_vol = float(w @ vols)
        port_vol = float(np.sqrt(w @ cov @ w))
        if port_vol < _EPS:
            return 0.0
        return -(weighted_avg_vol / port_vol)

    result = minimize(
        neg_dr,
        _w0(n),
        method="SLSQP",
        bounds=_default_bounds(n),
        constraints=_default_constraints(n),
        options={"ftol": 1e-12, "maxiter": 500},
    )
    w = result.x
    ret, vol, sharpe = _port_stats(w, mu, cov)
    return {
        "method": "max_diversification",
        "weights": dict(zip(tickers, w.tolist())),
        "expected_return": round(ret, 6),
        "expected_volatility": round(vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "converged": bool(result.success),
    }


# ---------------------------------------------------------------------------
# Hierarchical Risk Parity (HRP)
# ---------------------------------------------------------------------------

def _hrp_get_quasi_diag(link: np.ndarray) -> List[int]:
    """Reconstruct leaf ordering from linkage matrix."""
    n_leaves = link.shape[0] + 1
    sorted_items = [int(link[-1, 0]), int(link[-1, 1])]
    result = []
    while sorted_items:
        item = sorted_items.pop(0)
        if item < n_leaves:
            result.append(item)
        else:
            idx = item - n_leaves
            sorted_items = [int(link[idx, 0]), int(link[idx, 1])] + sorted_items
    return result


def _hrp_recursive_bisection(
    cov: np.ndarray,
    sort_ix: List[int],
) -> np.ndarray:
    """Recursive bisection of clusters to assign weights."""
    n = len(sort_ix)
    w = np.ones(n)

    def _bisect(items: List[int]) -> None:
        if len(items) <= 1:
            return
        mid = len(items) // 2
        left = items[:mid]
        right = items[mid:]

        def _cluster_var(cluster: List[int]) -> float:
            sub_cov = cov[np.ix_(cluster, cluster)]
            inv_diag = 1.0 / np.diag(sub_cov)
            w_cluster = inv_diag / inv_diag.sum()
            return float(w_cluster @ sub_cov @ w_cluster)

        var_l = _cluster_var(left)
        var_r = _cluster_var(right)
        total = var_l + var_r
        alpha = 1.0 - var_l / total if total > 0 else 0.5
        w[left] *= 1.0 - alpha
        w[right] *= alpha
        _bisect(left)
        _bisect(right)

    _bisect(sort_ix)
    return w / w.sum()


def hierarchical_risk_parity(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
) -> Dict[str, Any]:
    """Hierarchical Risk Parity (López de Prado, 2016)."""
    n = len(tickers)
    cov_arr = np.asarray(cov, dtype=float)

    # Correlation-based distance matrix
    std = np.sqrt(np.diag(cov_arr))
    corr = cov_arr / np.outer(std, std)
    corr = np.clip(corr, -1.0, 1.0)
    dist = np.sqrt((1.0 - corr) / 2.0)
    condensed = squareform(dist, checks=False)

    link = linkage(condensed, method="single")
    sort_ix = _hrp_get_quasi_diag(link)

    w_sorted = _hrp_recursive_bisection(cov_arr, sort_ix)
    w = np.zeros(n)
    for rank, orig_idx in enumerate(sort_ix):
        w[orig_idx] = w_sorted[rank]

    ret, vol, sharpe = _port_stats(w, mu, cov_arr)
    return {
        "method": "hrp",
        "weights": dict(zip(tickers, w.tolist())),
        "expected_return": round(ret, 6),
        "expected_volatility": round(vol, 6),
        "sharpe_ratio": round(sharpe, 4),
    }


# ---------------------------------------------------------------------------
# Black-Litterman view integration
# ---------------------------------------------------------------------------

def black_litterman_mu(
    market_weights: np.ndarray,
    cov: np.ndarray,
    views_P: np.ndarray,
    views_q: np.ndarray,
    tau: float = 0.05,
    omega: Optional[np.ndarray] = None,
    risk_aversion: float = 2.5,
) -> np.ndarray:
    """Return the Black-Litterman posterior expected return vector.

    Parameters
    ----------
    market_weights : market-cap weights (prior portfolio)
    cov : covariance matrix of daily returns
    views_P : picking matrix (k × n)  k=number of views, n=assets
    views_q : view returns vector (k,)  in daily returns
    tau : uncertainty scalar for prior
    omega : view uncertainty matrix (k × k); defaults to diag(P * tau*cov * P')
    risk_aversion : implied risk-aversion coefficient
    """
    pi = risk_aversion * cov @ market_weights  # implied equilibrium excess returns
    tau_cov = tau * cov
    P = np.asarray(views_P, dtype=float)
    q = np.asarray(views_q, dtype=float)

    if omega is None:
        omega = np.diag(np.diag(P @ tau_cov @ P.T))

    # BL master formula
    M = np.linalg.inv(np.linalg.inv(tau_cov) + P.T @ np.linalg.inv(omega) @ P)
    mu_bl = M @ (np.linalg.inv(tau_cov) @ pi + P.T @ np.linalg.inv(omega) @ q)
    return mu_bl


# ---------------------------------------------------------------------------
# Efficient Frontier
# ---------------------------------------------------------------------------

def efficient_frontier(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    n_points: int = 50,
) -> List[Dict[str, Any]]:
    """Compute the mean-variance efficient frontier.

    Returns a list of (volatility, return, sharpe, weights) dicts
    spanning the range from min-variance to max-return portfolio.
    """
    n = len(tickers)
    min_ret = float(mu.min()) * _ANN
    max_ret = float(mu.max()) * _ANN
    targets = np.linspace(min_ret, max_ret, n_points)

    points = []
    for target in targets:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, t=target: float(w @ mu) * _ANN - t},
        ]

        def portfolio_var(w: np.ndarray) -> float:
            return float(w @ cov @ w) * _ANN

        result = minimize(
            portfolio_var,
            _w0(n),
            method="SLSQP",
            bounds=_default_bounds(n),
            constraints=constraints,
            options={"ftol": 1e-10, "maxiter": 500},
        )
        if not result.success:
            continue
        w = result.x
        ret, vol, sharpe = _port_stats(w, mu, cov)
        points.append({
            "expected_return": round(ret, 6),
            "expected_volatility": round(vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "weights": dict(zip(tickers, w.tolist())),
        })

    return points


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_METHODS = {
    "equal_weight": equal_weight,
    "min_variance": min_variance,
    "max_sharpe": max_sharpe,
    "risk_parity": risk_parity,
    "max_diversification": max_diversification,
    "hrp": hierarchical_risk_parity,
}

AVAILABLE_METHODS = list(_METHODS.keys())


def run_optimization(
    method: str,
    tickers: List[str],
    returns_df: pd.DataFrame,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Main entry point for the analytics router.

    Parameters
    ----------
    method : one of AVAILABLE_METHODS
    tickers : list of ticker symbols (must be columns in returns_df)
    returns_df : daily returns DataFrame with tickers as columns
    extra_params : optional method-specific overrides
    """
    if method not in _METHODS:
        raise ValueError(f"Unknown optimization method: {method!r}. Choose from {AVAILABLE_METHODS}.")

    asset_cols = [t for t in tickers if t in returns_df.columns]
    if len(asset_cols) < 2:
        raise ValueError("Need at least 2 assets with return data to optimize.")

    rets = returns_df[asset_cols].dropna(how="all").ffill()

    mu = rets.mean().values
    cov = rets.cov().values

    fn = _METHODS[method]
    return fn(asset_cols, mu, cov)
