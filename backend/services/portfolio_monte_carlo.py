"""M12 Phase 8 — Multi-asset correlated portfolio Monte Carlo engine.

Extends services/monte_carlo.py for portfolio-level simulation:
  - Correlated multi-asset Geometric Brownian Motion (Cholesky)
  - Correlated Student-t (fat-tail) innovation
  - Block bootstrap (preserves autocorrelation structure)
  - Regime-switching GBM (two-state bull/bear)
  - Portfolio-level path generation with full metrics
  - Deterministic when seed is provided

All public functions return plain Python dicts for easy JSON serialisation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_ANN = 252
_EPS = 1e-10


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class MonteCarloConfig:
    """Specification for a portfolio Monte Carlo simulation."""

    n_simulations: int = 5_000
    simulation_days: int = _ANN
    model: str = "gbm"             # "gbm" | "student_t" | "bootstrap" | "regime_switching"
    seed: int = 42
    initial_value: float = 100_000.0
    percentiles: List[int] = field(default_factory=lambda: [5, 10, 25, 50, 75, 90, 95])
    target_return: Optional[float] = None    # annual — used for probability calculation
    # Regime-switching parameters (used when model="regime_switching")
    bull_fraction: float = 0.70    # fraction of time in bull regime
    bear_mu_scale: float = -0.5    # bear mu = bull_mu * bear_mu_scale
    bear_sigma_scale: float = 2.0  # bear vol = bull_vol * bear_sigma_scale
    # Bootstrap block size
    block_size: int = 20
    # Student-t degrees of freedom
    student_df: float = 5.0

    def __post_init__(self) -> None:
        if self.model not in ("gbm", "student_t", "bootstrap", "regime_switching"):
            raise ValueError(
                f"Unknown model '{self.model}'. Choose: gbm, student_t, bootstrap, regime_switching"
            )
        if self.n_simulations < 1:
            raise ValueError("n_simulations must be >= 1")
        if self.simulation_days < 1:
            raise ValueError("simulation_days must be >= 1")


@dataclass
class MonteCarloResult:
    """Complete output from a portfolio Monte Carlo run."""

    model: str
    n_simulations: int
    simulation_days: int
    initial_value: float
    # Percentile path bands (dict: "p5", "p25", etc. -> list of daily values)
    percentile_paths: Dict[str, List[float]]
    # Terminal value statistics
    expected_terminal: float
    median_terminal: float
    std_terminal: float
    best_case: float      # 95th percentile
    worst_case: float     # 5th percentile
    # Risk metrics
    probability_of_loss: float
    probability_of_target_return: Optional[float]   # None if no target set
    var_95: float
    cvar_95: float
    ruin_probability: float   # probability of losing > 50%
    # Drawdown distribution
    median_max_drawdown_pct: float
    p95_max_drawdown_pct: float
    # Annualised implied return
    implied_annual_return: float
    warnings: List[str]


# ===========================================================================
# Simulation engines
# ===========================================================================

def _cholesky_factor(cov: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    """Compute Cholesky factor; repair non-PD covariance if needed."""
    warn: List[str] = []
    try:
        L = np.linalg.cholesky(cov)
        return L, warn
    except np.linalg.LinAlgError:
        warn.append("Covariance not positive-definite; applying eigenvalue floor.")
        eigvals, eigvecs = np.linalg.eigh(cov)
        eigvals = np.maximum(eigvals, _EPS)
        cov_fixed = eigvecs @ np.diag(eigvals) @ eigvecs.T
        L = np.linalg.cholesky(cov_fixed)
        return L, warn


def _simulate_portfolio_gbm(
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    n_sims: int,
    n_days: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Correlated GBM paths.  Returns shape (n_sims, n_days+1) portfolio wealth."""
    n = len(w)
    L, _ = _cholesky_factor(cov)
    Z = rng.standard_normal((n_sims, n_days, n))
    Z_corr = Z @ L.T            # (n_sims, n_days, n) correlated shocks
    drift = mu - 0.5 * np.diag(cov)   # drift correction per asset
    log_rets = drift + Z_corr   # (n_sims, n_days, n)
    # Portfolio log-return = w · log_asset_rets  (approximate for small dt)
    port_log_rets = (log_rets * w).sum(axis=2)   # (n_sims, n_days)
    port_log_paths = np.hstack([
        np.zeros((n_sims, 1)),
        np.cumsum(port_log_rets, axis=1),
    ])
    return np.exp(port_log_paths)


def _simulate_portfolio_student_t(
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    n_sims: int,
    n_days: int,
    rng: np.random.Generator,
    df: float = 5.0,
) -> np.ndarray:
    """Correlated Student-t innovations."""
    n = len(w)
    L, _ = _cholesky_factor(cov)
    chi2 = rng.chisquare(df, size=(n_sims, n_days, 1))
    Z = rng.standard_normal((n_sims, n_days, n))
    t_innov = Z / np.sqrt(chi2 / df)   # Student-t via normal/chi2 mixture
    # Scale to match target cov
    scale = np.sqrt((df - 2.0) / df) if df > 2.0 else 1.0
    t_corr = (t_innov @ L.T) * scale
    drift = mu - 0.5 * np.diag(cov)
    log_rets = drift + t_corr
    port_log_rets = (log_rets * w).sum(axis=2)
    port_log_paths = np.hstack([
        np.zeros((n_sims, 1)),
        np.cumsum(port_log_rets, axis=1),
    ])
    return np.exp(port_log_paths)


def _simulate_portfolio_bootstrap(
    w: np.ndarray,
    hist_returns: np.ndarray,
    n_sims: int,
    n_days: int,
    rng: np.random.Generator,
    block_size: int = 20,
) -> np.ndarray:
    """Stationary block bootstrap preserving autocorrelation."""
    T, n = hist_returns.shape
    # Portfolio historical returns
    port_hist = hist_returns @ w   # T-vector
    n_blocks = math.ceil(n_days / block_size)
    starts = rng.integers(0, max(1, T - block_size), size=(n_sims, n_blocks))

    paths = np.zeros((n_sims, n_days))
    for s in range(n_sims):
        row = []
        for b in range(n_blocks):
            start = int(starts[s, b])
            block = port_hist[start: start + block_size]
            row.extend(block.tolist())
        paths[s] = np.log1p(row[:n_days])

    port_log_paths = np.hstack([np.zeros((n_sims, 1)), np.cumsum(paths, axis=1)])
    return np.exp(port_log_paths)


def _simulate_portfolio_regime_switching(
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    n_sims: int,
    n_days: int,
    rng: np.random.Generator,
    bull_fraction: float = 0.70,
    bear_mu_scale: float = -0.5,
    bear_sigma_scale: float = 2.0,
) -> np.ndarray:
    """Two-state (bull/bear) regime-switching GBM."""
    n = len(w)
    bear_cov = cov * bear_sigma_scale ** 2

    # Regime path: 1 = bull, 0 = bear
    is_bull = rng.random((n_sims, n_days)) < bull_fraction
    L_bull, _ = _cholesky_factor(cov)
    L_bear, _ = _cholesky_factor(bear_cov)

    Z = rng.standard_normal((n_sims, n_days, n))
    port_log_rets = np.zeros((n_sims, n_days))

    # Vectorised: split by regime, apply different parameters
    for sim in range(n_sims):
        for day in range(n_days):
            if is_bull[sim, day]:
                z_corr = Z[sim, day] @ L_bull.T
                drift = mu - 0.5 * np.diag(cov)
            else:
                z_corr = Z[sim, day] @ L_bear.T
                bear_mu = mu * bear_mu_scale
                drift = bear_mu - 0.5 * np.diag(bear_cov)
            port_log_rets[sim, day] = float((drift + z_corr) @ w)

    port_log_paths = np.hstack([np.zeros((n_sims, 1)), np.cumsum(port_log_rets, axis=1)])
    return np.exp(port_log_paths)


# ===========================================================================
# Path analytics
# ===========================================================================

def _compute_percentile_paths(
    paths: np.ndarray,
    initial: float,
    percentiles: List[int],
) -> Dict[str, List[float]]:
    result: Dict[str, List[float]] = {}
    for p in percentiles:
        band = np.percentile(paths, p, axis=0) * initial
        result[f"p{p}"] = [round(float(v), 2) for v in band]
    return result


def _path_max_drawdown(path: np.ndarray) -> float:
    """Maximum drawdown fraction for a single path (values normalised to 1.0)."""
    peak = np.maximum.accumulate(path)
    dd = (path - peak) / peak
    return float(-dd.min())


def _compute_drawdown_distribution(
    paths: np.ndarray,
    percentiles: Tuple[float, float] = (50.0, 95.0),
) -> Tuple[float, float]:
    """Return (median, p95) max drawdown across all paths."""
    # For speed, sample at most 2000 paths
    n_sims = paths.shape[0]
    sample_idx = np.arange(min(2000, n_sims))
    mdds = np.array([_path_max_drawdown(paths[i]) for i in sample_idx])
    p50 = float(np.percentile(mdds, percentiles[0])) * 100.0
    p95 = float(np.percentile(mdds, percentiles[1])) * 100.0
    return p50, p95


# ===========================================================================
# Main entry point
# ===========================================================================

def run_portfolio_monte_carlo(
    weights: List[float],
    mu: List[float],
    cov: List[List[float]],
    config: MonteCarloConfig,
    hist_returns: Optional[np.ndarray] = None,
) -> MonteCarloResult:
    """Run a multi-asset correlated Monte Carlo portfolio simulation.

    Parameters
    ----------
    weights : asset weights (sum = 1)
    mu : daily expected returns per asset
    cov : daily covariance matrix
    config : simulation configuration
    hist_returns : T × n historical daily return matrix (required for bootstrap)

    Returns
    -------
    MonteCarloResult
    """
    warn: List[str] = []
    w = np.array(weights, dtype=float)
    mu_arr = np.array(mu, dtype=float)
    cov_arr = np.array(cov, dtype=float)
    n = len(w)
    rng = np.random.default_rng(config.seed)

    if config.model == "bootstrap":
        if hist_returns is None:
            warn.append("bootstrap model requires hist_returns; falling back to GBM.")
            config = MonteCarloConfig(**{**config.__dict__, "model": "gbm"})
        elif hist_returns.shape[0] < config.block_size * 5:
            warn.append(
                f"Too few historical observations ({hist_returns.shape[0]}) for block bootstrap; "
                "falling back to GBM."
            )
            config = MonteCarloConfig(**{**config.__dict__, "model": "gbm"})

    n_sims = config.n_simulations
    n_days = config.simulation_days

    # Generate paths (normalised to start at 1.0)
    if config.model == "gbm":
        paths = _simulate_portfolio_gbm(w, mu_arr, cov_arr, n_sims, n_days, rng)
    elif config.model == "student_t":
        paths = _simulate_portfolio_student_t(w, mu_arr, cov_arr, n_sims, n_days, rng, df=config.student_df)
    elif config.model == "bootstrap" and hist_returns is not None:
        paths = _simulate_portfolio_bootstrap(w, hist_returns, n_sims, n_days, rng, config.block_size)
    elif config.model == "regime_switching":
        paths = _simulate_portfolio_regime_switching(
            w, mu_arr, cov_arr, n_sims, n_days, rng,
            config.bull_fraction, config.bear_mu_scale, config.bear_sigma_scale,
        )
    else:
        paths = _simulate_portfolio_gbm(w, mu_arr, cov_arr, n_sims, n_days, rng)
        warn.append(f"Unknown model '{config.model}'; used GBM.")

    initial = config.initial_value
    finals = paths[:, -1] * initial

    pct_paths = _compute_percentile_paths(paths, initial, config.percentiles)

    # Terminal statistics
    expected = float(finals.mean())
    median = float(np.median(finals))
    std = float(finals.std())
    p5 = float(np.percentile(finals, 5))
    p95 = float(np.percentile(finals, 95))

    # Probability of loss
    prob_loss = float((finals < initial).mean())

    # Probability of target return
    prob_target: Optional[float] = None
    if config.target_return is not None:
        target_final = initial * (1.0 + config.target_return) ** (n_days / _ANN)
        prob_target = float((finals >= target_final).mean())

    # VaR / CVaR
    terminal_rets = finals / initial - 1.0
    var_95 = float(-np.percentile(terminal_rets, 5))
    tail = terminal_rets[terminal_rets <= -var_95]
    cvar_95 = float(-tail.mean()) if len(tail) > 0 else var_95

    # Ruin probability (lose > 50%)
    ruin_prob = float((finals < initial * 0.5).mean())

    # Drawdown distribution
    med_mdd, p95_mdd = _compute_drawdown_distribution(paths)

    # Implied annual return
    years = n_days / _ANN
    implied_ret = (expected / initial) ** (1.0 / years) - 1.0 if years > 0 else 0.0

    return MonteCarloResult(
        model=config.model,
        n_simulations=n_sims,
        simulation_days=n_days,
        initial_value=round(initial, 2),
        percentile_paths=pct_paths,
        expected_terminal=round(expected, 2),
        median_terminal=round(median, 2),
        std_terminal=round(std, 2),
        best_case=round(p95, 2),
        worst_case=round(p5, 2),
        probability_of_loss=round(prob_loss, 4),
        probability_of_target_return=round(prob_target, 4) if prob_target is not None else None,
        var_95=round(var_95, 6),
        cvar_95=round(cvar_95, 6),
        ruin_probability=round(ruin_prob, 6),
        median_max_drawdown_pct=round(med_mdd, 4),
        p95_max_drawdown_pct=round(p95_mdd, 4),
        implied_annual_return=round(implied_ret, 6),
        warnings=warn,
    )
