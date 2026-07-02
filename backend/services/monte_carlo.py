"""Monte Carlo simulation service — M4.

Supports three process models:
- GBM (Geometric Brownian Motion) — log-normal returns
- Student-t GBM — fat-tailed return distribution
- Bootstrap — resample historical daily returns (non-parametric)

10,000+ simulations are run using vectorised NumPy (no loops over sims).
Only percentile paths are stored, not the full N×T matrix, to keep
memory and database storage bounded.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

_ANN = 252


# ---------------------------------------------------------------------------
# Simulation engines
# ---------------------------------------------------------------------------

def _simulate_gbm(
    mu: float,
    sigma: float,
    n_sims: int,
    n_days: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Standard Geometric Brownian Motion.

    Returns shape (n_sims, n_days+1) — column 0 is the starting value 1.0.
    """
    dt = 1.0
    drift = (mu - 0.5 * sigma ** 2) * dt
    diffusion = sigma * np.sqrt(dt)
    Z = rng.standard_normal((n_sims, n_days))
    log_returns = drift + diffusion * Z
    log_paths = np.hstack([np.zeros((n_sims, 1)), np.cumsum(log_returns, axis=1)])
    return np.exp(log_paths)  # normalised to start at 1.0


def _simulate_student_t(
    mu: float,
    sigma: float,
    n_sims: int,
    n_days: int,
    rng: np.random.Generator,
    df: float = 5.0,
) -> np.ndarray:
    """Fat-tailed GBM using Student-t innovations."""
    dt = 1.0
    drift = (mu - 0.5 * sigma ** 2) * dt
    # t distribution with df degrees of freedom, scaled to match sigma
    t_scale = sigma * np.sqrt((df - 2) / df) if df > 2 else sigma
    raw = rng.standard_t(df, size=(n_sims, n_days))
    innovations = t_scale * raw
    log_returns = drift + innovations
    log_paths = np.hstack([np.zeros((n_sims, 1)), np.cumsum(log_returns, axis=1)])
    return np.exp(log_paths)


def _simulate_bootstrap(
    historical_returns: np.ndarray,
    n_sims: int,
    n_days: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Block bootstrap from historical daily log-returns."""
    log_rets = np.log1p(historical_returns)
    idx = rng.integers(0, len(log_rets), size=(n_sims, n_days))
    sampled = log_rets[idx]
    log_paths = np.hstack([np.zeros((n_sims, 1)), np.cumsum(sampled, axis=1)])
    return np.exp(log_paths)


# ---------------------------------------------------------------------------
# Percentile aggregation
# ---------------------------------------------------------------------------

def _compute_percentile_paths(
    paths: np.ndarray,
    initial_value: float,
    percentiles: List[int],
) -> Dict[str, List[float]]:
    """Convert normalised path matrix to absolute value percentile bands."""
    result: Dict[str, List[float]] = {}
    for p in percentiles:
        pct_path = np.percentile(paths, p, axis=0) * initial_value
        result[f"p{p}"] = [round(float(v), 2) for v in pct_path]
    return result


def _final_value_stats(
    paths: np.ndarray,
    initial_value: float,
) -> Dict[str, float]:
    """Summary statistics of the terminal portfolio value distribution."""
    finals = paths[:, -1] * initial_value
    return {
        "mean": round(float(finals.mean()), 2),
        "median": round(float(np.median(finals)), 2),
        "std": round(float(finals.std()), 2),
        "p5": round(float(np.percentile(finals, 5)), 2),
        "p25": round(float(np.percentile(finals, 25)), 2),
        "p75": round(float(np.percentile(finals, 75)), 2),
        "p95": round(float(np.percentile(finals, 95)), 2),
        "min": round(float(finals.min()), 2),
        "max": round(float(finals.max()), 2),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_monte_carlo(
    portfolio_returns: pd.Series,
    initial_value: float,
    simulation_days: int = 252,
    n_simulations: int = 10_000,
    model: str = "gbm",
    seed: int = 42,
    percentiles: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Run a Monte Carlo portfolio projection.

    Parameters
    ----------
    portfolio_returns :
        Historical daily return series (decimal).
    initial_value :
        Current portfolio value in dollars.
    simulation_days :
        Number of trading days to simulate forward.
    n_simulations :
        Number of independent simulation paths (≥1000 recommended).
    model :
        Process model: ``"gbm"``, ``"student_t"``, or ``"bootstrap"``.
    seed :
        NumPy RNG seed for reproducibility.
    percentiles :
        Percentile bands to store; defaults to [5, 10, 25, 50, 75, 90, 95].

    Returns
    -------
    dict with ``percentile_paths``, ``final_value_stats``, and summary metrics.
    """
    if percentiles is None:
        percentiles = [5, 10, 25, 50, 75, 90, 95]

    r = portfolio_returns.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(r) < 20:
        raise ValueError("Need at least 20 historical return observations.")

    mu = float(r.mean())
    sigma = float(r.std(ddof=1))
    rng = np.random.default_rng(seed=seed)

    if model == "gbm":
        paths = _simulate_gbm(mu, sigma, n_simulations, simulation_days, rng)
    elif model == "student_t":
        paths = _simulate_student_t(mu, sigma, n_simulations, simulation_days, rng)
    elif model == "bootstrap":
        paths = _simulate_bootstrap(r.values, n_simulations, simulation_days, rng)
    else:
        raise ValueError(f"Unknown model: {model!r}. Choose 'gbm', 'student_t', or 'bootstrap'.")

    pct_paths = _compute_percentile_paths(paths, initial_value, percentiles)
    final_stats = _final_value_stats(paths, initial_value)

    # Probability of loss
    finals = paths[:, -1] * initial_value
    prob_loss = float((finals < initial_value).mean())

    # Annualised expected return implied by the simulation
    expected_final = float(finals.mean())
    implied_annual_ret = (expected_final / initial_value) ** (_ANN / simulation_days) - 1.0

    return {
        "model": model,
        "n_simulations": n_simulations,
        "simulation_days": simulation_days,
        "initial_value": round(initial_value, 2),
        "percentile_paths": pct_paths,
        "final_value_stats": final_stats,
        "prob_loss": round(prob_loss, 4),
        "expected_final_value": round(expected_final, 2),
        "implied_annual_return": round(implied_annual_ret, 6),
        "input_mu_daily": round(mu, 8),
        "input_sigma_daily": round(sigma, 8),
    }
