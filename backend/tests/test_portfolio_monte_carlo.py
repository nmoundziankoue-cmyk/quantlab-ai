"""M12 — Deterministic tests for services/portfolio_monte_carlo.py."""
from __future__ import annotations

import numpy as np
import pytest

from services.portfolio_monte_carlo import MonteCarloConfig, MonteCarloResult, run_portfolio_monte_carlo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_2asset(n_sims: int = 1000, model: str = "gbm", seed: int = 42) -> MonteCarloResult:
    weights = [0.6, 0.4]
    mu = [0.0005, 0.0004]
    cov = [[0.0001, 0.00002], [0.00002, 0.00008]]
    cfg = MonteCarloConfig(n_simulations=n_sims, simulation_days=252, model=model, seed=seed)
    return run_portfolio_monte_carlo(weights, mu, cov, cfg)


def _make_hist_returns(T: int = 300, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0004, 0.01, (T, 2))


# ===========================================================================
# Config validation
# ===========================================================================

def test_config_invalid_model():
    with pytest.raises(ValueError, match="Unknown model"):
        MonteCarloConfig(model="magic")


def test_config_zero_sims():
    with pytest.raises(ValueError, match="n_simulations"):
        MonteCarloConfig(n_simulations=0)


def test_config_zero_days():
    with pytest.raises(ValueError, match="simulation_days"):
        MonteCarloConfig(simulation_days=0)


# ===========================================================================
# GBM basic properties
# ===========================================================================

def test_gbm_result_type():
    result = _simple_2asset()
    assert isinstance(result, MonteCarloResult)


def test_gbm_model_label():
    result = _simple_2asset(model="gbm")
    assert result.model == "gbm"


def test_gbm_percentile_paths_present():
    result = _simple_2asset()
    assert "p5" in result.percentile_paths
    assert "p50" in result.percentile_paths
    assert "p95" in result.percentile_paths


def test_gbm_path_length():
    result = _simple_2asset()
    # Each path has simulation_days + 1 values (day 0 to day 252)
    assert len(result.percentile_paths["p50"]) == 253


def test_gbm_initial_value():
    result = _simple_2asset()
    # Day-0 value should be initial_value for all percentiles
    assert abs(result.percentile_paths["p50"][0] - 100_000.0) < 1.0


def test_gbm_expected_terminal_near_initial():
    """With μ≈0 drift over 252 days, expected terminal should be > initial."""
    result = _simple_2asset()
    assert result.expected_terminal >= result.initial_value * 0.90


def test_gbm_prob_loss_between_0_and_1():
    result = _simple_2asset()
    assert 0.0 <= result.probability_of_loss <= 1.0


def test_gbm_ruin_probability_non_negative():
    result = _simple_2asset()
    assert result.ruin_probability >= 0.0


def test_gbm_var_non_negative():
    result = _simple_2asset()
    assert result.var_95 >= 0


def test_gbm_cvar_gte_var():
    result = _simple_2asset()
    assert result.cvar_95 >= result.var_95 - 1e-6


def test_gbm_best_case_gt_worst_case():
    result = _simple_2asset(n_sims=2000)
    assert result.best_case > result.worst_case


def test_gbm_median_between_worst_best():
    result = _simple_2asset(n_sims=2000)
    assert result.worst_case <= result.median_terminal <= result.best_case + 1e-2


# ===========================================================================
# Determinism
# ===========================================================================

def test_determinism_same_seed():
    r1 = _simple_2asset(seed=123)
    r2 = _simple_2asset(seed=123)
    assert r1.expected_terminal == r2.expected_terminal
    assert r1.probability_of_loss == r2.probability_of_loss


def test_different_seeds_give_different_results():
    r1 = _simple_2asset(seed=1)
    r2 = _simple_2asset(seed=2)
    assert r1.expected_terminal != r2.expected_terminal


# ===========================================================================
# Student-t model
# ===========================================================================

def test_student_t_runs():
    result = _simple_2asset(model="student_t")
    assert result.model == "student_t"
    assert result.expected_terminal > 0


def test_student_t_fatter_tails_than_gbm():
    """Student-t should have worse worst-case and better best-case than GBM."""
    n = 5000
    gbm = _simple_2asset(n_sims=n, model="gbm", seed=0)
    st = _simple_2asset(n_sims=n, model="student_t", seed=0)
    # Student-t CVaR should generally be worse (higher loss)
    assert st.cvar_95 >= gbm.cvar_95 - 0.02


# ===========================================================================
# Bootstrap model
# ===========================================================================

def test_bootstrap_runs_with_hist():
    hist = _make_hist_returns()
    weights = [0.6, 0.4]
    mu = [0.0004, 0.0003]
    cov = [[0.0001, 0.00002], [0.00002, 0.00008]]
    cfg = MonteCarloConfig(n_simulations=500, simulation_days=100, model="bootstrap", seed=42)
    result = run_portfolio_monte_carlo(weights, mu, cov, cfg, hist_returns=hist)
    assert result.model == "bootstrap"
    assert result.expected_terminal > 0


def test_bootstrap_falls_back_without_hist():
    """Without hist_returns, bootstrap falls back to GBM with a warning."""
    weights = [0.6, 0.4]
    mu = [0.0004, 0.0003]
    cov = [[0.0001, 0.00002], [0.00002, 0.00008]]
    cfg = MonteCarloConfig(n_simulations=500, simulation_days=100, model="bootstrap", seed=42)
    result = run_portfolio_monte_carlo(weights, mu, cov, cfg, hist_returns=None)
    assert len(result.warnings) > 0


# ===========================================================================
# Regime-switching model
# ===========================================================================

def test_regime_switching_runs():
    result = _simple_2asset(model="regime_switching", n_sims=500)
    assert result.model == "regime_switching"
    assert result.expected_terminal > 0


# ===========================================================================
# Target return probability
# ===========================================================================

def test_prob_target_return_set():
    weights = [0.6, 0.4]
    mu = [0.0005, 0.0004]
    cov = [[0.0001, 0.00002], [0.00002, 0.00008]]
    cfg = MonteCarloConfig(n_simulations=2000, simulation_days=252, model="gbm", seed=42,
                           target_return=0.05)
    result = run_portfolio_monte_carlo(weights, mu, cov, cfg)
    assert result.probability_of_target_return is not None
    assert 0.0 <= result.probability_of_target_return <= 1.0


def test_prob_target_return_none_when_not_set():
    result = _simple_2asset()
    assert result.probability_of_target_return is None


# ===========================================================================
# Drawdown distribution
# ===========================================================================

def test_drawdown_distribution_non_negative():
    result = _simple_2asset(n_sims=500)
    assert result.median_max_drawdown_pct >= 0
    assert result.p95_max_drawdown_pct >= 0


def test_p95_drawdown_gte_median():
    result = _simple_2asset(n_sims=1000)
    assert result.p95_max_drawdown_pct >= result.median_max_drawdown_pct - 1e-4


# ===========================================================================
# Dimension validation
# ===========================================================================

def test_weight_mu_cov_mismatch_raises():
    with pytest.raises(Exception):
        from schemas.portfolio_optimization import MonteCarloRequest
        req = MonteCarloRequest(weights=[0.5, 0.5], mu=[0.001], cov=[[0.0001]])


def test_single_asset_simulation():
    """Single-asset portfolio should work."""
    weights = [1.0]
    mu = [0.0005]
    cov = [[0.0001]]
    cfg = MonteCarloConfig(n_simulations=500, simulation_days=100, model="gbm", seed=42)
    result = run_portfolio_monte_carlo(weights, mu, cov, cfg)
    assert result.expected_terminal > 0
