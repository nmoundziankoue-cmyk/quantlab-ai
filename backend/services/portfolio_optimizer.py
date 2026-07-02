"""M12 — Institutional Portfolio Optimization & Risk Engine.

Wraps existing optimization.py methods and adds:
  - 8 new optimization methods (inverse_vol, mean_variance, target_return,
    target_volatility, kelly, CVaR, long/short constrained, Black-Litterman full)
  - Clean dataclasses for structured I/O
  - Covariance estimation (sample, EW, Ledoit-Wolf, nearest-PD repair)
  - Risk attribution (marginal / component / pct contributions to risk)
  - Deterministic stress scenarios (no network calls)
  - Efficient frontier with annotations
  - Covariance diagnostics

Design principles:
  - Zero network calls; all algorithms accept pre-computed matrices.
  - Degrade gracefully on ill-conditioned inputs (warn + fallback).
  - Re-export all objects needed by the router so the router imports
    from this module alone.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.linalg import eigh
from scipy.optimize import minimize, linprog
from scipy.spatial.distance import squareform

from config import settings

_ANN = 252
_RFR_ANNUAL = settings.risk_free_rate_annual
_EPS = 1e-10


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class OptimizationConstraints:
    """Defines feasibility constraints for portfolio optimization."""

    long_only: bool = True
    max_weight: float = 1.0           # maximum weight per asset (fraction)
    min_weight: float = 0.0           # minimum weight per asset (ignored for L/S)
    leverage_cap: float = 1.0         # gross_exposure / initial_capital cap
    gross_exposure_cap: float = 1.0   # sum(|w|) cap
    net_exposure_min: float = 0.0     # sum(w) floor
    net_exposure_max: float = 1.0     # sum(w) ceiling
    sector_max: Optional[Dict[str, float]] = None   # sector_label -> max fraction
    max_turnover: Optional[float] = None            # vs current_weights
    transaction_costs: Optional[Dict[str, float]] = None  # ticker -> fraction


@dataclass
class AssetAssumption:
    """Per-asset return / risk / sector assumptions."""

    ticker: str
    expected_annual_return: float
    annual_volatility: float
    sector: str = "Unknown"
    country: str = "US"
    currency: str = "USD"


@dataclass
class PortfolioOptimizationConfig:
    """Complete specification for a portfolio optimization run.

    ``mu`` and ``cov`` are expressed in **daily** units (consistent with
    using daily returns DataFrames).  They are annualised internally.
    """

    tickers: List[str]
    mu: List[float]              # daily expected returns
    cov: List[List[float]]       # daily covariance matrix
    risk_free_rate: float = _RFR_ANNUAL
    constraints: OptimizationConstraints = field(
        default_factory=OptimizationConstraints
    )
    # Optional method-specific parameters
    target_return: Optional[float] = None      # annual target (used by target_return method)
    target_volatility: Optional[float] = None  # annual target (used by target_vol method)
    gamma: float = 1.0                         # risk-aversion for mean-variance
    kelly_fraction: float = 0.5                # fraction of full Kelly leverage to use
    # Black-Litterman views
    views_P: Optional[List[List[float]]] = None   # picking matrix (k × n), daily
    views_q: Optional[List[float]] = None         # view returns vector (k,), daily
    market_weights: Optional[List[float]] = None  # market-cap weights for BL prior
    # Efficient frontier
    n_frontier_points: int = 50
    # Turnover / transaction cost baseline
    current_weights: Optional[List[float]] = None
    # Historical returns (required for CVaR optimisation and covariance estimation)
    returns_matrix: Optional[List[List[float]]] = None  # T × n daily returns

    def __post_init__(self) -> None:
        n = len(self.tickers)
        if len(self.mu) != n:
            raise ValueError("len(mu) must equal len(tickers)")
        if len(self.cov) != n or any(len(row) != n for row in self.cov):
            raise ValueError("cov must be n × n")
        if n < 1:
            raise ValueError("Must have at least 1 asset")

    @property
    def n(self) -> int:
        return len(self.tickers)

    @property
    def mu_arr(self) -> np.ndarray:
        return np.array(self.mu, dtype=float)

    @property
    def cov_arr(self) -> np.ndarray:
        return np.array(self.cov, dtype=float)

    @property
    def returns_arr(self) -> Optional[np.ndarray]:
        if self.returns_matrix is None:
            return None
        return np.array(self.returns_matrix, dtype=float)


@dataclass
class OptimizationResult:
    """Complete output from a single optimization method."""

    method: str
    tickers: List[str]
    weights: Dict[str, float]
    expected_return: float          # annualised
    expected_volatility: float      # annualised
    sharpe_ratio: float
    diversification_ratio: float
    concentration_score: float      # Herfindahl-Hirschman Index (0–1)
    effective_n: float              # 1/HHI — effective number of assets
    gross_exposure: float           # sum(|w|)
    net_exposure: float             # sum(w)
    leverage: float                 # gross / net if net > 0 else gross
    risk_contributions: Dict[str, float]   # pct contribution to portfolio variance
    warnings: List[str]
    converged: bool


@dataclass
class EfficientFrontierPoint:
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]
    feasible: bool = True


@dataclass
class EfficientFrontierResult:
    points: List[EfficientFrontierPoint]
    max_sharpe_idx: int             # index into ``points``
    min_vol_idx: int
    equal_weight_point: EfficientFrontierPoint
    n_feasible: int
    n_infeasible: int
    warnings: List[str]


@dataclass
class RiskAttributionResult:
    tickers: List[str]
    weights: Dict[str, float]
    marginal_contributions: Dict[str, float]
    component_contributions: Dict[str, float]
    pct_contributions: Dict[str, float]
    portfolio_volatility: float
    diversification_benefit: float   # 1 - port_vol / weighted_avg_vol
    hhi: float
    effective_n: float


@dataclass
class StressScenarioConfig:
    """Defines a stress scenario as percentage shocks to assets."""

    name: str
    description: str
    asset_shocks: Dict[str, float]    # ticker -> fractional shock (e.g. -0.30)
    market_shock: float = 0.0         # applied to all assets not in asset_shocks
    volatility_multiplier: float = 1.0


@dataclass
class StressScenarioResult:
    scenario_name: str
    portfolio_impact_pct: float          # total portfolio % return under shock
    asset_impacts: Dict[str, float]      # ticker -> contribution to portfolio impact
    worst_contributor: str
    best_contributor: str
    severity_score: float                # 0–10 scale
    post_stress_weights: Dict[str, float]
    warnings: List[str]


@dataclass
class CovarianceDiagnostics:
    n_assets: int
    n_observations: int
    method: str
    condition_number: float
    is_positive_definite: bool
    min_eigenvalue: float
    max_eigenvalue: float
    effective_rank: float        # number of eigenvalues that explain 95% variance
    highly_correlated_pairs: List[Tuple[str, str, float]]   # (t1, t2, corr)
    shrinkage_intensity: float   # 0 for sample, >0 for Ledoit-Wolf
    repaired: bool               # True if nearest-PD was applied
    warnings: List[str]


@dataclass
class DrawdownAnalysis:
    max_drawdown: float
    avg_drawdown: float
    max_drawdown_duration_days: int
    avg_drawdown_duration_days: float
    recovery_time_days: Optional[int]
    ulcer_index: float
    pain_index: float


# ===========================================================================
# Internal helpers
# ===========================================================================

def _w0(n: int) -> np.ndarray:
    return np.full(n, 1.0 / n)


def _default_bounds(c: OptimizationConstraints, n: int) -> List[Tuple[float, float]]:
    if c.long_only:
        lo = max(c.min_weight, 0.0)
        hi = min(c.max_weight, 1.0)
        return [(lo, hi)] * n
    else:
        return [(-c.max_weight, c.max_weight)] * n


def _sum_constraint(target: float = 1.0) -> Dict:
    return {"type": "eq", "fun": lambda w: np.sum(w) - target}


def _port_stats(
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    rfr: float = _RFR_ANNUAL,
) -> Tuple[float, float, float]:
    """Return (ann_return, ann_vol, sharpe)."""
    ret = float(w @ mu) * _ANN
    var = float(w @ cov @ w) * _ANN
    vol = math.sqrt(max(var, 0.0))
    sharpe = (ret - rfr) / vol if vol > _EPS else 0.0
    return ret, vol, sharpe


def _diversification_ratio(w: np.ndarray, cov: np.ndarray) -> float:
    """DR = (w · σ) / σ_portfolio."""
    vols = np.sqrt(np.maximum(np.diag(cov), 0.0))
    weighted_avg_vol = float(w @ vols)
    port_vol = math.sqrt(max(float(w @ cov @ w), 0.0))
    return weighted_avg_vol / port_vol if port_vol > _EPS else 1.0


def _hhi(w: np.ndarray) -> float:
    """Herfindahl-Hirschman Index of weight concentration."""
    return float(np.sum(w ** 2))


def _pct_risk_contributions(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Percentage risk contributions (sum = 1)."""
    port_var = float(w @ cov @ w)
    if port_var < _EPS:
        return np.full(len(w), 1.0 / len(w))
    mrc = cov @ w / math.sqrt(port_var)
    crc = w * mrc
    total = crc.sum()
    return crc / total if abs(total) > _EPS else np.full(len(w), 1.0 / len(w))


def _make_result(
    method: str,
    tickers: List[str],
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    rfr: float,
    converged: bool,
    warn: List[str],
) -> OptimizationResult:
    ret, vol, sharpe = _port_stats(w, mu, cov, rfr)
    dr = _diversification_ratio(w, cov)
    hhi = _hhi(w)
    eff_n = 1.0 / hhi if hhi > _EPS else float(len(w))
    pct_rc = _pct_risk_contributions(w, cov)
    gross = float(np.sum(np.abs(w)))
    net = float(np.sum(w))
    leverage = gross / net if abs(net) > _EPS else gross
    return OptimizationResult(
        method=method,
        tickers=tickers,
        weights={t: round(float(x), 8) for t, x in zip(tickers, w)},
        expected_return=round(ret, 6),
        expected_volatility=round(vol, 6),
        sharpe_ratio=round(sharpe, 4),
        diversification_ratio=round(dr, 4),
        concentration_score=round(hhi, 6),
        effective_n=round(eff_n, 2),
        gross_exposure=round(gross, 6),
        net_exposure=round(net, 6),
        leverage=round(leverage, 6),
        risk_contributions={t: round(float(x), 6) for t, x in zip(tickers, pct_rc)},
        warnings=warn,
        converged=converged,
    )


def _repair_cov(cov: np.ndarray, warnings_out: List[str]) -> np.ndarray:
    """Return positive-semi-definite covariance; warns if repair applied."""
    eigvals = np.linalg.eigvalsh(cov)
    if eigvals.min() >= 0.0:
        return cov
    warnings_out.append(
        f"Covariance matrix not positive-definite (min eigenvalue {eigvals.min():.4e}). "
        "Applied nearest-PD repair."
    )
    return _nearest_positive_definite(cov)


def _nearest_positive_definite(A: np.ndarray) -> np.ndarray:
    """Higham (1988) nearest positive-definite matrix."""
    B = (A + A.T) / 2.0
    vals, vecs = eigh(B)
    vals = np.maximum(vals, _EPS)
    C = vecs @ np.diag(vals) @ vecs.T
    C = (C + C.T) / 2.0
    return C


# ===========================================================================
# Covariance estimation
# ===========================================================================

def estimate_covariance(
    returns: np.ndarray,
    method: str = "sample",
    halflife: int = 63,
    shrink_target: str = "identity",
) -> Tuple[np.ndarray, float]:
    """Estimate covariance matrix from a T × n returns array.

    Parameters
    ----------
    returns : T × n array of daily returns
    method : "sample" | "ewm" | "ledoit_wolf"
    halflife : EWM halflife in trading days (only for method="ewm")
    shrink_target : "identity" (only used with ledoit_wolf)

    Returns
    -------
    (cov, shrinkage_intensity) — shrinkage=0 for sample/ewm
    """
    T, n = returns.shape
    if method == "ewm":
        alpha = 1.0 - math.exp(-math.log(2.0) / halflife)
        df = pd.DataFrame(returns)
        cov = df.ewm(alpha=alpha, min_periods=2).cov().iloc[-n:].values
        return cov, 0.0
    if method == "ledoit_wolf":
        return _ledoit_wolf_identity(returns)
    # Default: sample
    cov = np.cov(returns.T)
    return cov, 0.0


def _ledoit_wolf_identity(returns: np.ndarray) -> Tuple[np.ndarray, float]:
    """Analytical Ledoit-Wolf shrinkage towards scaled identity (LW 2004)."""
    T, n = returns.shape
    X = returns - returns.mean(axis=0)
    S = (X.T @ X) / (T - 1)
    mu = float(np.trace(S)) / n

    # Vectorised oracle approximation
    outer = X[:, :, np.newaxis] * X[:, np.newaxis, :]   # T × n × n
    deltas = outer - S[np.newaxis, :, :]
    numerator = float(np.sum(deltas ** 2)) / (T * T)
    target_dev = S - mu * np.eye(n)
    denominator = float(np.sum(target_dev ** 2))

    alpha = min(1.0, numerator / denominator) if denominator > _EPS else 0.0
    cov_lw = (1.0 - alpha) * S + alpha * mu * np.eye(n)
    return cov_lw, alpha


def covariance_diagnostics(
    tickers: List[str],
    returns: np.ndarray,
    cov: Optional[np.ndarray] = None,
    method: str = "sample",
) -> CovarianceDiagnostics:
    """Compute diagnostics for a covariance matrix."""
    T, n = returns.shape
    warn: List[str] = []

    if cov is None:
        cov, shrink = estimate_covariance(returns, method)
    else:
        shrink = 0.0

    eigvals = np.linalg.eigvalsh(cov)
    is_pd = bool(eigvals.min() > 0)
    cond = float(eigvals.max() / max(eigvals.min(), _EPS))

    # Effective rank: how many eigenvalues explain 95% of total variance
    total_var = eigvals.sum()
    sorted_vals = np.sort(eigvals)[::-1]
    cumsum = np.cumsum(sorted_vals)
    eff_rank = float(np.searchsorted(cumsum, 0.95 * total_var) + 1)

    # Highly correlated pairs (|corr| > 0.9)
    std = np.sqrt(np.maximum(np.diag(cov), _EPS))
    corr = cov / np.outer(std, std)
    np.fill_diagonal(corr, 0.0)
    high_pairs: List[Tuple[str, str, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            c = float(corr[i, j])
            if abs(c) > 0.9:
                high_pairs.append((tickers[i], tickers[j], round(c, 4)))

    repaired = not is_pd
    if not is_pd:
        warn.append("Covariance matrix is not positive-definite.")
    if cond > 1000:
        warn.append(f"High condition number ({cond:.1f}). Consider shrinkage.")
    if T < 2 * n:
        warn.append(
            f"Observations ({T}) < 2 × assets ({n}). Sample covariance may be unreliable."
        )

    return CovarianceDiagnostics(
        n_assets=n,
        n_observations=T,
        method=method,
        condition_number=round(cond, 2),
        is_positive_definite=is_pd,
        min_eigenvalue=round(float(eigvals.min()), 8),
        max_eigenvalue=round(float(eigvals.max()), 8),
        effective_rank=round(eff_rank, 2),
        highly_correlated_pairs=high_pairs,
        shrinkage_intensity=round(shrink, 6),
        repaired=repaired,
        warnings=warn,
    )


# ===========================================================================
# Optimization methods
# ===========================================================================

def _opt_equal_weight(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    n = len(tickers)
    w = np.full(n, 1.0 / n)
    return _make_result("equal_weight", tickers, w, mu, cov, rfr, True, [])


def _opt_inverse_volatility(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    warn: List[str] = []
    vols = np.sqrt(np.maximum(np.diag(cov), _EPS))
    if np.any(vols < _EPS):
        warn.append("Zero-vol assets detected; using equal weight as fallback.")
        return _make_result("inverse_volatility", tickers, _w0(len(tickers)), mu, cov, rfr, False, warn)
    inv_vol = 1.0 / vols
    w = inv_vol / inv_vol.sum()
    return _make_result("inverse_volatility", tickers, w, mu, cov, rfr, True, warn)


def _opt_min_variance(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    bounds = _default_bounds(c, n)

    def obj(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    res = minimize(obj, _w0(n), method="SLSQP", bounds=bounds,
                   constraints=[_sum_constraint()], options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(f"min_variance did not converge: {res.message}")
    w = np.abs(res.x)
    w /= w.sum() if w.sum() > _EPS else 1.0
    return _make_result("min_variance", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_max_sharpe(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    daily_rf = rfr / _ANN
    bounds = _default_bounds(c, n)

    def neg_sharpe(w: np.ndarray) -> float:
        ret = float(w @ mu)
        vol = math.sqrt(max(float(w @ cov @ w), 0.0))
        if vol < _EPS:
            return 0.0
        return -(ret - daily_rf) / vol

    res = minimize(neg_sharpe, _w0(n), method="SLSQP", bounds=bounds,
                   constraints=[_sum_constraint()], options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(f"max_sharpe did not converge: {res.message}")
    w = res.x
    if c.long_only:
        w = np.maximum(w, 0.0)
    s = w.sum()
    w = w / s if s > _EPS else _w0(n)
    return _make_result("max_sharpe", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_mean_variance(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
    gamma: float = 1.0,
) -> OptimizationResult:
    """Maximize expected utility:  w'μ - (1/2γ) w'Σw."""
    n = len(tickers)
    warn: List[str] = []
    if gamma <= 0:
        warn.append("gamma must be positive; using gamma=1.0")
        gamma = 1.0
    cov = _repair_cov(cov, warn)
    bounds = _default_bounds(c, n)

    def neg_utility(w: np.ndarray) -> float:
        ret = float(w @ mu)
        risk = float(w @ cov @ w)
        return -(ret - 0.5 / gamma * risk)

    res = minimize(neg_utility, _w0(n), method="SLSQP", bounds=bounds,
                   constraints=[_sum_constraint()], options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(f"mean_variance did not converge: {res.message}")
    w = res.x
    if c.long_only:
        w = np.maximum(w, 0.0)
    s = w.sum()
    w = w / s if s > _EPS else _w0(n)
    return _make_result("mean_variance", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_target_return(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
    target_return: float,
) -> OptimizationResult:
    """Minimum variance portfolio achieving ``target_return`` (annualised)."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    daily_target = target_return / _ANN
    bounds = _default_bounds(c, n)
    constraints = [
        _sum_constraint(),
        {"type": "eq", "fun": lambda w: float(w @ mu) - daily_target},
    ]

    def obj(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    res = minimize(obj, _w0(n), method="SLSQP", bounds=bounds,
                   constraints=constraints, options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(f"target_return infeasible ({target_return:.1%}): {res.message}")
        return _make_result("target_return", tickers, _w0(n), mu, cov, rfr, False, warn)
    w = res.x
    if c.long_only:
        w = np.maximum(w, 0.0)
    s = w.sum()
    w = w / s if s > _EPS else _w0(n)
    return _make_result("target_return", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_target_volatility(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
    target_volatility: float,
) -> OptimizationResult:
    """Maximum return portfolio achieving ``target_volatility`` (annualised)."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    daily_target_var = (target_volatility / math.sqrt(_ANN)) ** 2
    bounds = _default_bounds(c, n)
    constraints = [
        _sum_constraint(),
        {"type": "ineq", "fun": lambda w: daily_target_var - float(w @ cov @ w)},
    ]

    def neg_return(w: np.ndarray) -> float:
        return -float(w @ mu)

    res = minimize(neg_return, _w0(n), method="SLSQP", bounds=bounds,
                   constraints=constraints, options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(
            f"target_volatility infeasible ({target_volatility:.1%}): {res.message}"
        )
        return _make_result("target_volatility", tickers, _w0(n), mu, cov, rfr, False, warn)
    w = res.x
    if c.long_only:
        w = np.maximum(w, 0.0)
    s = w.sum()
    w = w / s if s > _EPS else _w0(n)
    return _make_result("target_volatility", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_risk_parity(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    """Equal risk-contribution (Risk Parity) portfolio."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    target = np.ones(n) / n

    def rp_obj(w: np.ndarray) -> float:
        port_var = float(w @ cov @ w)
        if port_var <= _EPS:
            return 1e10
        mrc = cov @ w / math.sqrt(port_var)
        crc = w * mrc
        total_risk = crc.sum()
        if total_risk < _EPS:
            return 1e10
        pct = crc / total_risk
        return float(np.sum((pct - target) ** 2))

    res = minimize(rp_obj, _w0(n), method="SLSQP", bounds=_default_bounds(c, n),
                   constraints=[_sum_constraint()], options={"ftol": 1e-14, "maxiter": 1000})
    w = np.abs(res.x)
    w /= w.sum() if w.sum() > _EPS else 1.0
    if not res.success:
        warn.append(f"risk_parity did not fully converge: {res.message}")
    return _make_result("risk_parity", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_max_diversification(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    """Maximum Diversification Ratio portfolio."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    vols = np.sqrt(np.maximum(np.diag(cov), _EPS))

    def neg_dr(w: np.ndarray) -> float:
        weighted_avg_vol = float(w @ vols)
        port_vol = math.sqrt(max(float(w @ cov @ w), 0.0))
        return -(weighted_avg_vol / port_vol) if port_vol > _EPS else 0.0

    res = minimize(neg_dr, _w0(n), method="SLSQP", bounds=_default_bounds(c, n),
                   constraints=[_sum_constraint()], options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(f"max_diversification did not converge: {res.message}")
    w = np.maximum(res.x, 0.0)
    s = w.sum()
    w = w / s if s > _EPS else _w0(n)
    return _make_result("max_diversification", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_hrp(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    """Hierarchical Risk Parity (López de Prado, 2016)."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)

    std = np.sqrt(np.maximum(np.diag(cov), _EPS))
    corr = cov / np.outer(std, std)
    corr = np.clip(corr, -1.0 + _EPS, 1.0 - _EPS)
    dist = np.sqrt((1.0 - corr) / 2.0)
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")

    sort_ix = _hrp_get_quasi_diag(link, n)
    w_sorted = _hrp_recursive_bisection(cov, sort_ix)
    w = np.zeros(n)
    for rank, orig_idx in enumerate(sort_ix):
        w[orig_idx] = w_sorted[rank]
    w = np.maximum(w, 0.0)
    w /= w.sum()
    return _make_result("hrp", tickers, w, mu, cov, rfr, True, warn)


def _hrp_get_quasi_diag(link: np.ndarray, n_leaves: int) -> List[int]:
    sorted_items = [int(link[-1, 0]), int(link[-1, 1])]
    result: List[int] = []
    while sorted_items:
        item = sorted_items.pop(0)
        if item < n_leaves:
            result.append(item)
        else:
            idx = item - n_leaves
            sorted_items = [int(link[idx, 0]), int(link[idx, 1])] + sorted_items
    return result


def _hrp_recursive_bisection(cov: np.ndarray, sort_ix: List[int]) -> np.ndarray:
    w = np.ones(len(sort_ix))

    def _bisect(items: List[int]) -> None:
        if len(items) <= 1:
            return
        mid = len(items) // 2
        left, right = items[:mid], items[mid:]

        def _cluster_var(cluster: List[int]) -> float:
            sub = cov[np.ix_(cluster, cluster)]
            inv_d = 1.0 / np.maximum(np.diag(sub), _EPS)
            wc = inv_d / inv_d.sum()
            return float(wc @ sub @ wc)

        vl, vr = _cluster_var(left), _cluster_var(right)
        total = vl + vr
        alpha = 1.0 - vl / total if total > _EPS else 0.5
        w[left] *= 1.0 - alpha
        w[right] *= alpha
        _bisect(left)
        _bisect(right)

    _bisect(sort_ix)
    s = w.sum()
    return w / s if s > _EPS else np.full(len(sort_ix), 1.0 / len(sort_ix))


def _opt_black_litterman(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
    views_P: np.ndarray,
    views_q: np.ndarray,
    market_weights: np.ndarray,
    tau: float = 0.05,
    risk_aversion: float = 2.5,
) -> OptimizationResult:
    """Black-Litterman posterior → Maximum Sharpe portfolio."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)

    pi = risk_aversion * cov @ market_weights
    tau_cov = tau * cov
    P = np.asarray(views_P, dtype=float)
    q = np.asarray(views_q, dtype=float)
    omega = np.diag(np.diag(P @ tau_cov @ P.T))

    try:
        M = np.linalg.inv(np.linalg.inv(tau_cov) + P.T @ np.linalg.inv(omega) @ P)
        mu_bl = M @ (np.linalg.inv(tau_cov) @ pi + P.T @ np.linalg.inv(omega) @ q)
    except np.linalg.LinAlgError:
        warn.append("Black-Litterman inversion failed; falling back to max_sharpe.")
        return _opt_max_sharpe(tickers, mu, cov, c, rfr)

    daily_rf = rfr / _ANN
    bounds = _default_bounds(c, n)

    def neg_sharpe(w: np.ndarray) -> float:
        ret = float(w @ mu_bl)
        vol = math.sqrt(max(float(w @ cov @ w), 0.0))
        return -(ret - daily_rf) / vol if vol > _EPS else 0.0

    res = minimize(neg_sharpe, _w0(n), method="SLSQP", bounds=bounds,
                   constraints=[_sum_constraint()], options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(f"BL max_sharpe did not converge: {res.message}")
    w = res.x
    if c.long_only:
        w = np.maximum(w, 0.0)
    s = w.sum()
    w = w / s if s > _EPS else _w0(n)
    return _make_result("black_litterman", tickers, w, mu_bl, cov, rfr, res.success, warn)


def _opt_kelly(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
    kelly_fraction: float = 0.5,
) -> OptimizationResult:
    """Kelly Criterion allocation (fractional Kelly for safety)."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    daily_rf = rfr / _ANN
    excess_mu = mu - daily_rf

    try:
        cov_inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        cov_inv = np.linalg.pinv(cov)
        warn.append("Singular covariance; used pseudo-inverse for Kelly weights.")

    w_kelly = (cov_inv @ excess_mu) * kelly_fraction

    if c.long_only:
        w_kelly = np.maximum(w_kelly, 0.0)

    s = w_kelly.sum()
    if s < _EPS:
        warn.append("Kelly weights sum to zero; falling back to equal weight.")
        w = _w0(n)
    else:
        w = w_kelly / s
    return _make_result("kelly", tickers, w, mu, cov, rfr, True, warn)


def _opt_cvar(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
    hist_returns: np.ndarray,
    alpha: float = 0.95,
) -> OptimizationResult:
    """Minimise CVaR (Expected Shortfall at confidence ``alpha``) using SLSQP."""
    T, n_assets = hist_returns.shape
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    bounds = _default_bounds(c, len(tickers))

    threshold_idx = max(1, int(math.floor(T * (1.0 - alpha))))

    def cvar_obj(w: np.ndarray) -> float:
        port_r = hist_returns @ w
        sorted_r = np.sort(port_r)
        tail = sorted_r[:threshold_idx]
        return -float(tail.mean()) if len(tail) > 0 else 0.0

    res = minimize(cvar_obj, _w0(n_assets), method="SLSQP", bounds=bounds,
                   constraints=[_sum_constraint()], options={"ftol": 1e-10, "maxiter": 1000})
    if not res.success:
        warn.append(f"CVaR optimisation did not converge: {res.message}")
    w = res.x
    if c.long_only:
        w = np.maximum(w, 0.0)
    s = w.sum()
    w = w / s if s > _EPS else _w0(n_assets)
    return _make_result("cvar_optimization", tickers, w, mu, cov, rfr, res.success, warn)


def _opt_long_short(
    tickers: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    c: OptimizationConstraints,
    rfr: float,
) -> OptimizationResult:
    """Constrained long/short portfolio: maximize Sharpe subject to gross/net exposure."""
    n = len(tickers)
    warn: List[str] = []
    cov = _repair_cov(cov, warn)
    daily_rf = rfr / _ANN
    bounds = [(-c.max_weight, c.max_weight)] * n

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "ineq", "fun": lambda w: c.gross_exposure_cap - np.sum(np.abs(w))},
        {"type": "ineq", "fun": lambda w: np.sum(w) - c.net_exposure_min},
        {"type": "ineq", "fun": lambda w: c.net_exposure_max - np.sum(w)},
    ]

    def neg_sharpe(w: np.ndarray) -> float:
        ret = float(w @ mu)
        vol = math.sqrt(max(float(w @ cov @ w), 0.0))
        return -(ret - daily_rf) / vol if vol > _EPS else 0.0

    res = minimize(neg_sharpe, _w0(n), method="SLSQP", bounds=bounds,
                   constraints=constraints, options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        warn.append(f"long_short did not converge: {res.message}")
    return _make_result("long_short_constrained", tickers, res.x, mu, cov, rfr, res.success, warn)


# ===========================================================================
# Dispatch table
# ===========================================================================

_METHODS: Dict[str, str] = {
    "equal_weight": "Equal Weight",
    "inverse_volatility": "Inverse Volatility",
    "min_variance": "Minimum Variance",
    "max_sharpe": "Maximum Sharpe",
    "mean_variance": "Mean-Variance Utility",
    "target_return": "Target Return",
    "target_volatility": "Target Volatility",
    "risk_parity": "Risk Parity",
    "max_diversification": "Maximum Diversification",
    "hrp": "Hierarchical Risk Parity",
    "black_litterman": "Black-Litterman",
    "kelly": "Kelly Criterion",
    "cvar_optimization": "CVaR Optimisation",
    "long_short_constrained": "Long/Short Constrained",
}

AVAILABLE_METHODS: List[str] = list(_METHODS.keys())


def optimize(
    config: PortfolioOptimizationConfig,
    method: str,
) -> OptimizationResult:
    """Run a single optimization method.

    Parameters
    ----------
    config : fully specified optimization configuration
    method : one of AVAILABLE_METHODS

    Returns
    -------
    OptimizationResult
    """
    if method not in _METHODS:
        raise ValueError(f"Unknown method '{method}'. Available: {AVAILABLE_METHODS}")

    n = config.n
    tickers = config.tickers
    mu = config.mu_arr
    cov = config.cov_arr
    c = config.constraints
    rfr = config.risk_free_rate

    if n == 0:
        raise ValueError("No assets specified")

    if n == 1:
        w = np.array([1.0])
        return _make_result(method, tickers, w, mu, cov, rfr, True,
                            ["Single-asset portfolio; only equal-weight is meaningful."])

    if method == "equal_weight":
        return _opt_equal_weight(tickers, mu, cov, c, rfr)
    if method == "inverse_volatility":
        return _opt_inverse_volatility(tickers, mu, cov, c, rfr)
    if method == "min_variance":
        return _opt_min_variance(tickers, mu, cov, c, rfr)
    if method == "max_sharpe":
        return _opt_max_sharpe(tickers, mu, cov, c, rfr)
    if method == "mean_variance":
        return _opt_mean_variance(tickers, mu, cov, c, rfr, config.gamma)
    if method == "target_return":
        if config.target_return is None:
            raise ValueError("target_return method requires config.target_return")
        return _opt_target_return(tickers, mu, cov, c, rfr, config.target_return)
    if method == "target_volatility":
        if config.target_volatility is None:
            raise ValueError("target_volatility method requires config.target_volatility")
        return _opt_target_volatility(tickers, mu, cov, c, rfr, config.target_volatility)
    if method == "risk_parity":
        return _opt_risk_parity(tickers, mu, cov, c, rfr)
    if method == "max_diversification":
        return _opt_max_diversification(tickers, mu, cov, c, rfr)
    if method == "hrp":
        return _opt_hrp(tickers, mu, cov, c, rfr)
    if method == "black_litterman":
        P = np.array(config.views_P) if config.views_P else np.eye(n)
        q = np.array(config.views_q) if config.views_q else mu * _ANN
        mw = np.array(config.market_weights) if config.market_weights else _w0(n)
        return _opt_black_litterman(tickers, mu, cov, c, rfr, P, q, mw)
    if method == "kelly":
        return _opt_kelly(tickers, mu, cov, c, rfr, config.kelly_fraction)
    if method == "cvar_optimization":
        hist = config.returns_arr
        if hist is None:
            raise ValueError("cvar_optimization requires config.returns_matrix")
        return _opt_cvar(tickers, mu, cov, c, rfr, hist)
    if method == "long_short_constrained":
        return _opt_long_short(tickers, mu, cov, c, rfr)
    raise ValueError(f"Unhandled method: {method}")


def compare_methods(
    config: PortfolioOptimizationConfig,
    methods: Optional[List[str]] = None,
) -> List[OptimizationResult]:
    """Run multiple methods and return a list of results for comparison."""
    if methods is None:
        # Exclude methods that require extra parameters
        methods = [
            m for m in AVAILABLE_METHODS
            if m not in ("target_return", "target_volatility", "black_litterman",
                         "cvar_optimization")
        ]
    results = []
    for m in methods:
        try:
            results.append(optimize(config, m))
        except Exception as exc:
            # Return a failed result rather than crashing the comparison
            n = config.n
            warn = [f"Method failed: {exc}"]
            r = _make_result(m, config.tickers, _w0(n), config.mu_arr, config.cov_arr,
                             config.risk_free_rate, False, warn)
            results.append(r)
    return results


# ===========================================================================
# Efficient frontier
# ===========================================================================

def efficient_frontier(config: PortfolioOptimizationConfig) -> EfficientFrontierResult:
    """Compute the mean-variance efficient frontier.

    Returns ``config.n_frontier_points`` portfolios from min-vol to max-return.
    """
    tickers = config.tickers
    mu = config.mu_arr
    cov = config.cov_arr
    n = config.n
    rfr = config.risk_free_rate
    c = config.constraints
    warn: List[str] = []
    cov = _repair_cov(cov, warn)

    # Determine return range
    min_ann_ret = float(mu.min()) * _ANN
    max_ann_ret = float(mu.max()) * _ANN
    n_pts = max(5, config.n_frontier_points)
    targets = np.linspace(min_ann_ret, max_ann_ret, n_pts)

    bounds = _default_bounds(c, n)
    points: List[EfficientFrontierPoint] = []

    for target in targets:
        daily_t = target / _ANN
        constraints = [
            _sum_constraint(),
            {"type": "eq", "fun": lambda w, t=daily_t: float(w @ mu) - t},
        ]
        res = minimize(lambda w: float(w @ cov @ w), _w0(n), method="SLSQP",
                       bounds=bounds, constraints=constraints,
                       options={"ftol": 1e-12, "maxiter": 500})
        if not res.success:
            points.append(EfficientFrontierPoint(
                expected_return=round(target, 6),
                expected_volatility=0.0,
                sharpe_ratio=0.0,
                weights={},
                feasible=False,
            ))
            continue
        w = res.x
        ret, vol, sharpe = _port_stats(w, mu, cov, rfr)
        points.append(EfficientFrontierPoint(
            expected_return=round(ret, 6),
            expected_volatility=round(vol, 6),
            sharpe_ratio=round(sharpe, 4),
            weights={t: round(float(x), 6) for t, x in zip(tickers, w)},
            feasible=True,
        ))

    feasible = [p for p in points if p.feasible]
    n_feasible = len(feasible)
    n_infeasible = len(points) - n_feasible

    # Locate max-Sharpe and min-vol on the feasible frontier
    max_sharpe_idx = max(range(len(points)), key=lambda i: points[i].sharpe_ratio if points[i].feasible else -999)
    min_vol_idx = min(
        (i for i, p in enumerate(points) if p.feasible),
        key=lambda i: points[i].expected_volatility,
        default=0,
    )

    # Equal-weight anchor point
    w_ew = _w0(n)
    ret_ew, vol_ew, sr_ew = _port_stats(w_ew, mu, cov, rfr)
    ew_point = EfficientFrontierPoint(
        expected_return=round(ret_ew, 6),
        expected_volatility=round(vol_ew, 6),
        sharpe_ratio=round(sr_ew, 4),
        weights={t: round(float(x), 6) for t, x in zip(tickers, w_ew)},
        feasible=True,
    )

    if n_feasible < 3:
        warn.append(f"Only {n_feasible}/{len(points)} frontier points were feasible.")

    return EfficientFrontierResult(
        points=points,
        max_sharpe_idx=max_sharpe_idx,
        min_vol_idx=min_vol_idx,
        equal_weight_point=ew_point,
        n_feasible=n_feasible,
        n_infeasible=n_infeasible,
        warnings=warn,
    )


# ===========================================================================
# Risk attribution
# ===========================================================================

def compute_risk_attribution(
    config: PortfolioOptimizationConfig,
    weights: Dict[str, float],
) -> RiskAttributionResult:
    """Compute risk contributions for a given weight vector."""
    tickers = config.tickers
    cov = config.cov_arr
    w = np.array([weights.get(t, 0.0) for t in tickers])

    warn: List[str] = []
    cov = _repair_cov(cov, warn)

    port_var = float(w @ cov @ w)
    port_vol = math.sqrt(max(port_var, 0.0)) * math.sqrt(_ANN)

    mrc_raw = cov @ w  # n-vector, daily units
    mrc = {t: round(float(x) * _ANN, 8) for t, x in zip(tickers, mrc_raw)}

    crc_raw = w * mrc_raw
    crc = {t: round(float(x) * _ANN, 8) for t, x in zip(tickers, crc_raw)}

    total_crc = sum(crc_raw)
    pct = crc_raw / total_crc if abs(total_crc) > _EPS else np.full(len(w), 1.0 / len(w))
    pct_rc = {t: round(float(x), 8) for t, x in zip(tickers, pct)}

    # Diversification benefit
    vols = np.sqrt(np.maximum(np.diag(cov), _EPS)) * math.sqrt(_ANN)
    weighted_avg_vol = float(w @ vols)
    div_benefit = 1.0 - port_vol / weighted_avg_vol if weighted_avg_vol > _EPS else 0.0

    hhi = _hhi(w)
    eff_n = 1.0 / hhi if hhi > _EPS else float(len(w))

    return RiskAttributionResult(
        tickers=tickers,
        weights={t: round(float(x), 8) for t, x in zip(tickers, w)},
        marginal_contributions=mrc,
        component_contributions=crc,
        pct_contributions=pct_rc,
        portfolio_volatility=round(port_vol, 6),
        diversification_benefit=round(div_benefit, 6),
        hhi=round(hhi, 6),
        effective_n=round(eff_n, 2),
    )


# ===========================================================================
# Stress testing (deterministic — no network calls)
# ===========================================================================

BUILTIN_STRESS_SCENARIOS: Dict[str, StressScenarioConfig] = {
    "2008_crisis": StressScenarioConfig(
        name="2008 Global Financial Crisis",
        description="Lehman collapse; equities fell ~50%.",
        asset_shocks={},
        market_shock=-0.50,
        volatility_multiplier=3.0,
    ),
    "covid_2020": StressScenarioConfig(
        name="COVID-19 Crash (March 2020)",
        description="Pandemic shock; equities fell ~34% in 33 days.",
        asset_shocks={},
        market_shock=-0.34,
        volatility_multiplier=4.0,
    ),
    "dotcom_crash": StressScenarioConfig(
        name="Dot-com Crash 2000–2002",
        description="Tech bubble; NASDAQ fell ~78%; S&P ~49%.",
        asset_shocks={},
        market_shock=-0.49,
        volatility_multiplier=2.0,
    ),
    "black_monday_1987": StressScenarioConfig(
        name="Black Monday 1987",
        description="S&P fell 22.6% in a single day.",
        asset_shocks={},
        market_shock=-0.226,
        volatility_multiplier=5.0,
    ),
    "inflation_shock": StressScenarioConfig(
        name="Inflation / Rate Shock",
        description="Fed hike cycle 2022; stocks -25%, bonds -17%.",
        asset_shocks={},
        market_shock=-0.25,
        volatility_multiplier=1.5,
    ),
    "oil_shock": StressScenarioConfig(
        name="Oil Price Collapse",
        description="Crude oil -60%; energy sector -40%.",
        asset_shocks={},
        market_shock=-0.15,
        volatility_multiplier=1.5,
    ),
    "flash_crash": StressScenarioConfig(
        name="Flash Crash",
        description="Sudden intraday 10% drop with fast recovery.",
        asset_shocks={},
        market_shock=-0.10,
        volatility_multiplier=2.0,
    ),
    "volatility_spike": StressScenarioConfig(
        name="VIX Spike / Vol Crisis",
        description="Volatility doubles; risk assets reprice.",
        asset_shocks={},
        market_shock=-0.12,
        volatility_multiplier=4.0,
    ),
    "credit_spread_widening": StressScenarioConfig(
        name="Credit Spread Widening",
        description="HY spreads widen 500bps; credit-sensitive equities hit.",
        asset_shocks={},
        market_shock=-0.18,
        volatility_multiplier=2.0,
    ),
    "liquidity_crisis": StressScenarioConfig(
        name="Liquidity Crisis",
        description="Bid-ask spreads widen; forced selling.",
        asset_shocks={},
        market_shock=-0.20,
        volatility_multiplier=2.5,
    ),
}


def apply_stress_scenario(
    tickers: List[str],
    weights: Dict[str, float],
    scenario: StressScenarioConfig,
    asset_classes: Optional[Dict[str, str]] = None,
) -> StressScenarioResult:
    """Apply a stress scenario to a portfolio.  Fully deterministic; no downloads."""
    warn: List[str] = []
    w = np.array([weights.get(t, 0.0) for t in tickers])

    # Determine per-asset shock
    shocks = np.full(len(tickers), scenario.market_shock)
    for i, t in enumerate(tickers):
        if t in scenario.asset_shocks:
            shocks[i] = scenario.asset_shocks[t]

    # Asset-level P&L contributions
    asset_impacts: Dict[str, float] = {}
    for i, t in enumerate(tickers):
        asset_impacts[t] = round(float(w[i] * shocks[i]), 6)

    portfolio_impact = float(np.sum(w * shocks))

    # Worst/best contributors
    contributions = [(t, asset_impacts[t]) for t in tickers]
    worst = min(contributions, key=lambda x: x[1])[0]
    best = max(contributions, key=lambda x: x[1])[0]

    # Post-stress weights (renormalised if any remain)
    post_values = w * (1.0 + shocks)
    post_sum = float(post_values.sum())
    if post_sum > _EPS:
        post_w = post_values / post_sum
    else:
        post_w = w.copy()
        warn.append("Portfolio value approaches zero post-stress; weights unchanged.")
    post_weights = {t: round(float(post_w[i]), 6) for i, t in enumerate(tickers)}

    # Severity score 0–10
    severity = min(10.0, abs(portfolio_impact) * 20.0)

    return StressScenarioResult(
        scenario_name=scenario.name,
        portfolio_impact_pct=round(portfolio_impact * 100.0, 4),
        asset_impacts={t: round(v * 100.0, 4) for t, v in asset_impacts.items()},
        worst_contributor=worst,
        best_contributor=best,
        severity_score=round(severity, 2),
        post_stress_weights=post_weights,
        warnings=warn,
    )


def run_all_stress_scenarios(
    tickers: List[str],
    weights: Dict[str, float],
) -> List[StressScenarioResult]:
    """Apply all built-in stress scenarios to a portfolio."""
    return [
        apply_stress_scenario(tickers, weights, sc)
        for sc in BUILTIN_STRESS_SCENARIOS.values()
    ]
