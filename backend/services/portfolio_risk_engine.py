"""M12 Phase 4-5 — Institutional Portfolio Risk Engine.

Wraps and extends services/risk_analytics.py with:
  - Extended metrics (skewness, kurtosis, tail ratio, pain/gain ratios)
  - Drawdown analytics (duration, average, recovery time)
  - Multiple confidence levels (90/95/97.5/99%)
  - Structured output types
  - Factor risk decomposition (contribution to return/risk)
  - Full portfolio risk report

All functions accept pandas Series/DataFrame — no network calls required.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from services.risk_analytics import (
    annual_volatility,
    beta_alpha,
    calmar_ratio,
    cvar as cvar_fn,
    downside_deviation,
    herfindahl_hirschman_index,
    information_ratio,
    max_drawdown,
    r_squared,
    semi_variance,
    sharpe_ratio,
    sortino_ratio,
    tracking_error,
    treynor_ratio,
    ulcer_index,
    var_historical,
    var_monte_carlo,
    var_parametric,
)

_ANN = 252
_EPS = 1e-10
_CONFIDENCE_LEVELS = (0.90, 0.95, 0.975, 0.99)


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class VaRResult:
    """VaR / CVaR at multiple confidence levels."""

    var_90: float
    var_95: float
    var_975: float
    var_99: float
    cvar_90: float
    cvar_95: float
    cvar_975: float
    cvar_99: float
    method: str   # "historical" | "parametric" | "monte_carlo"


@dataclass
class DrawdownMetrics:
    """Complete drawdown analytics."""

    max_drawdown_pct: float
    avg_drawdown_pct: float
    max_drawdown_duration_days: int
    avg_drawdown_duration_days: float
    current_drawdown_pct: float
    recovery_time_days: Optional[int]
    ulcer_index: float
    pain_index: float


@dataclass
class DistributionMetrics:
    """Return-distribution statistics."""

    mean_daily: float
    std_daily: float
    skewness: float
    kurtosis: float          # excess kurtosis
    is_fat_tailed: bool      # kurtosis > 3
    tail_ratio: float        # 95th / abs(5th) percentile
    gain_to_pain: float      # sum(positive) / abs(sum(negative))
    best_day_pct: float
    worst_day_pct: float
    positive_days_pct: float


@dataclass
class PortfolioRiskReport:
    """Complete risk report for a portfolio."""

    # Annualised return metrics
    total_return_pct: float
    annual_return_pct: float
    annual_volatility_pct: float
    downside_volatility_pct: float
    semi_variance_daily: float

    # Risk-adjusted ratios
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    treynor_ratio: float
    information_ratio: float

    # Benchmark-relative
    alpha: float
    beta: float
    r_squared: float
    tracking_error_pct: float
    benchmark_return_pct: float

    # VaR / CVaR
    var: VaRResult

    # Drawdown
    drawdown: DrawdownMetrics

    # Distribution
    distribution: DistributionMetrics

    # Risk metrics
    ulcer_index: float

    # Warnings
    warnings: List[str]


# ===========================================================================
# VaR / CVaR engine
# ===========================================================================

def compute_var_all_levels(
    returns: pd.Series,
    method: str = "historical",
    n_mc_sims: int = 10_000,
    seed: int = 42,
) -> VaRResult:
    """Compute VaR and CVaR at 4 confidence levels.

    Parameters
    ----------
    returns : daily return series (decimal)
    method : "historical" | "parametric" | "monte_carlo"
    n_mc_sims : number of Monte Carlo simulations (only for method="monte_carlo")
    seed : RNG seed (for "monte_carlo" only)
    """
    r = _clean(returns)
    if len(r) < 10:
        z = VaRResult(0, 0, 0, 0, 0, 0, 0, 0, method)
        return z

    kwargs: Dict = {}
    if method == "monte_carlo":
        kwargs = {"n_simulations": n_mc_sims, "seed": seed}

    fn = {
        "historical": var_historical,
        "parametric": var_parametric,
        "monte_carlo": var_monte_carlo,
    }.get(method, var_historical)

    def _var(cl: float) -> float:
        return float(fn(r, confidence=cl, **kwargs))

    def _cvar(cl: float) -> float:
        return float(cvar_fn(r, confidence=cl))

    return VaRResult(
        var_90=round(_var(0.90), 6),
        var_95=round(_var(0.95), 6),
        var_975=round(_var(0.975), 6),
        var_99=round(_var(0.99), 6),
        cvar_90=round(_cvar(0.90), 6),
        cvar_95=round(_cvar(0.95), 6),
        cvar_975=round(_cvar(0.975), 6),
        cvar_99=round(_cvar(0.99), 6),
        method=method,
    )


# ===========================================================================
# Drawdown analytics
# ===========================================================================

def compute_drawdown_metrics(nav: pd.Series) -> DrawdownMetrics:
    """Compute comprehensive drawdown statistics from a NAV series."""
    if len(nav) < 2:
        return DrawdownMetrics(0, 0, 0, 0.0, 0, None, 0.0, 0.0)

    nav_arr = np.asarray(nav, dtype=float)
    peak = np.maximum.accumulate(nav_arr)
    dd = (nav_arr - peak) / peak   # always ≤ 0

    # Current drawdown
    current_dd = float(dd[-1]) * 100.0

    # Max drawdown
    mdd = float(-dd.min()) * 100.0

    # Average drawdown (only during drawdown periods)
    in_dd = dd[dd < 0]
    avg_dd = float(-in_dd.mean()) * 100.0 if len(in_dd) > 0 else 0.0

    # Drawdown duration analysis
    max_dur, avg_dur, recovery = _drawdown_durations(dd)

    # Ulcer index
    ui = float(ulcer_index(pd.Series(nav_arr)))

    # Pain index: mean of absolute drawdown values
    pain = float((-dd).mean()) * 100.0

    return DrawdownMetrics(
        max_drawdown_pct=round(mdd, 4),
        avg_drawdown_pct=round(avg_dd, 4),
        max_drawdown_duration_days=max_dur,
        avg_drawdown_duration_days=round(avg_dur, 1),
        current_drawdown_pct=round(current_dd, 4),
        recovery_time_days=recovery,
        ulcer_index=round(ui, 6),
        pain_index=round(pain, 4),
    )


def _drawdown_durations(dd: np.ndarray) -> Tuple[int, float, Optional[int]]:
    """Return (max_duration, avg_duration, recovery_days_from_last_peak)."""
    n = len(dd)
    durations: List[int] = []
    cur_dur = 0
    recovery: Optional[int] = None
    in_drawdown = False

    for i in range(n):
        if dd[i] < 0:
            cur_dur += 1
            in_drawdown = True
        else:
            if in_drawdown:
                durations.append(cur_dur)
            cur_dur = 0
            in_drawdown = False

    if in_drawdown and cur_dur > 0:
        durations.append(cur_dur)
        recovery = None
    else:
        recovery = durations[-1] if durations else 0

    max_dur = max(durations) if durations else 0
    avg_dur = float(np.mean(durations)) if durations else 0.0
    return max_dur, avg_dur, recovery


# ===========================================================================
# Distribution statistics
# ===========================================================================

def compute_distribution_metrics(returns: pd.Series) -> DistributionMetrics:
    """Compute return-distribution statistics."""
    r = _clean(returns)
    if len(r) < 5:
        return DistributionMetrics(0, 0, 0, 0, False, 1.0, 0.0, 0.0, 0.0, 0.0)

    r_arr = r.values
    sk = float(scipy_stats.skew(r_arr))
    ku = float(scipy_stats.kurtosis(r_arr))   # excess kurtosis

    p95 = float(np.percentile(r_arr, 95))
    p5 = float(np.percentile(r_arr, 5))
    tail_ratio = p95 / abs(p5) if abs(p5) > _EPS else 1.0

    pos = r_arr[r_arr > 0]
    neg = r_arr[r_arr < 0]
    gain_pain = float(pos.sum()) / float(abs(neg.sum())) if neg.sum() < 0 else float("inf")

    pos_days_pct = float((r_arr > 0).mean()) * 100.0

    return DistributionMetrics(
        mean_daily=round(float(r_arr.mean()), 8),
        std_daily=round(float(r_arr.std(ddof=1)), 8),
        skewness=round(sk, 4),
        kurtosis=round(ku, 4),
        is_fat_tailed=ku > 3.0,
        tail_ratio=round(tail_ratio, 4),
        gain_to_pain=round(min(gain_pain, 1e6), 4),
        best_day_pct=round(float(r_arr.max()) * 100.0, 4),
        worst_day_pct=round(float(r_arr.min()) * 100.0, 4),
        positive_days_pct=round(pos_days_pct, 2),
    )


# ===========================================================================
# Full risk report
# ===========================================================================

def compute_full_risk_report(
    returns: pd.Series,
    nav: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    initial_capital: float = 100_000.0,
) -> PortfolioRiskReport:
    """Compute a complete institutional risk report.

    Parameters
    ----------
    returns : daily portfolio return series
    nav : daily NAV series (same length as returns, starts at initial_capital)
    benchmark_returns : optional daily benchmark returns
    initial_capital : starting portfolio value
    """
    warn: List[str] = []
    r = _clean(returns)
    if len(r) < 10:
        warn.append("Insufficient data for full risk report (< 10 observations).")

    # Benchmark handling
    bench = _clean(benchmark_returns) if benchmark_returns is not None else pd.Series(dtype=float)
    aligned_r, aligned_bench = r.align(bench, join="inner")
    has_bench = len(aligned_bench) >= 10

    # Return metrics
    final_nav = float(nav.iloc[-1]) if len(nav) > 0 else initial_capital
    total_ret = (final_nav / initial_capital - 1.0) * 100.0
    n_days = max(len(r), 1)
    years = n_days / _ANN
    ann_ret = ((final_nav / initial_capital) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0
    bench_ret = float(aligned_bench.add(1).prod() - 1.0) * 100.0 if has_bench else 0.0

    # Volatility
    ann_vol = float(annual_volatility(r)) * 100.0
    dd_vol = float(downside_deviation(r)) * 100.0   # downside_deviation already annualises
    sv = float(semi_variance(r))

    # Ratios
    sharpe = float(sharpe_ratio(r))
    sortino = float(sortino_ratio(r))
    calmar = float(calmar_ratio(r, nav)) if len(nav) >= 10 else 0.0
    treynor = float(treynor_ratio(aligned_r, aligned_bench)) if has_bench else 0.0
    ir = float(information_ratio(aligned_r, aligned_bench)) if has_bench else 0.0

    # Benchmark-relative
    alpha_val, beta_val = 0.0, 0.0
    r2, te = 0.0, 0.0
    if has_bench:
        beta_v, alpha_v = beta_alpha(aligned_r, aligned_bench)
        alpha_val = alpha_v * _ANN * 100.0
        beta_val = float(beta_v)
        r2 = float(r_squared(aligned_r, aligned_bench))
        te = float(tracking_error(aligned_r, aligned_bench)) * 100.0

    # VaR
    var_result = compute_var_all_levels(r, method="historical")

    # Drawdown
    dd_metrics = compute_drawdown_metrics(nav)

    # Distribution
    dist_metrics = compute_distribution_metrics(r)

    # Ulcer
    ui = float(ulcer_index(nav)) if len(nav) >= 2 else 0.0

    return PortfolioRiskReport(
        total_return_pct=round(total_ret, 4),
        annual_return_pct=round(ann_ret, 4),
        annual_volatility_pct=round(ann_vol, 4),
        downside_volatility_pct=round(dd_vol, 4),
        semi_variance_daily=round(sv, 8),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        calmar_ratio=round(calmar, 4),
        treynor_ratio=round(treynor, 6),
        information_ratio=round(ir, 4),
        alpha=round(alpha_val, 4),
        beta=round(beta_val, 4),
        r_squared=round(r2, 4),
        tracking_error_pct=round(te, 4),
        benchmark_return_pct=round(bench_ret, 4),
        var=var_result,
        drawdown=dd_metrics,
        distribution=dist_metrics,
        ulcer_index=round(ui, 6),
        warnings=warn,
    )


# ===========================================================================
# Factor risk decomposition
# ===========================================================================

def compute_factor_risk_decomposition(
    returns: pd.Series,
    factor_returns: Dict[str, pd.Series],
) -> Dict[str, Dict[str, float]]:
    """Decompose portfolio risk into factor contributions via OLS regression.

    Returns a dict with keys: 'factor_betas', 'factor_variance_contribution',
    'residual_variance', 'r_squared', 'total_variance'.
    """
    r = _clean(returns)
    result: Dict[str, float] = {}
    betas: Dict[str, float] = {}
    r2 = 0.0

    if not factor_returns:
        return {"factor_betas": {}, "factor_variance_contribution": {},
                "residual_variance": float(r.var()) if len(r) > 1 else 0.0,
                "r_squared": 0.0,
                "total_variance": float(r.var()) if len(r) > 1 else 0.0}

    # Build factor matrix
    factor_df = pd.DataFrame(factor_returns)
    aligned = pd.concat([r.rename("portfolio"), factor_df], axis=1).dropna()
    if len(aligned) < 10 or aligned.shape[1] < 2:
        return {"factor_betas": {}, "factor_variance_contribution": {},
                "residual_variance": float(r.var()), "r_squared": 0.0,
                "total_variance": float(r.var())}

    Y = aligned["portfolio"].values
    X = aligned.drop(columns="portfolio").values
    factor_names = [c for c in aligned.columns if c != "portfolio"]

    # OLS: w = (X'X)^-1 X'Y
    try:
        XtX_inv = np.linalg.pinv(X.T @ X)
        b = XtX_inv @ X.T @ Y
        Y_hat = X @ b
        residuals = Y - Y_hat
        ss_tot = np.sum((Y - Y.mean()) ** 2)
        ss_res = np.sum(residuals ** 2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > _EPS else 0.0
        for i, name in enumerate(factor_names):
            betas[name] = round(float(b[i]), 6)
    except np.linalg.LinAlgError:
        return {"factor_betas": {}, "factor_variance_contribution": {},
                "residual_variance": float(r.var()), "r_squared": 0.0,
                "total_variance": float(r.var())}

    total_var = float(np.var(Y, ddof=1))
    factor_cov = np.cov(X.T)
    if X.shape[1] == 1:
        factor_cov = np.array([[factor_cov]])
    factor_var = float(b @ factor_cov @ b)
    resid_var = total_var - factor_var

    contrib: Dict[str, float] = {}
    for i, name in enumerate(factor_names):
        if X.shape[1] > 1:
            fi = np.zeros(len(b))
            fi[i] = b[i]
            contrib[name] = round(float(fi @ factor_cov @ b), 8)
        else:
            contrib[name] = round(factor_var, 8)

    return {
        "factor_betas": betas,
        "factor_variance_contribution": contrib,
        "residual_variance": round(max(resid_var, 0.0), 8),
        "r_squared": round(max(0.0, r2), 4),
        "total_variance": round(total_var, 8),
    }


# ===========================================================================
# Internal helper
# ===========================================================================

def _clean(s: Optional[pd.Series]) -> pd.Series:
    if s is None or len(s) == 0:
        return pd.Series(dtype=float)
    return s.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
