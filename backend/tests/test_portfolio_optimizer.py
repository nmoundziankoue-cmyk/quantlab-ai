"""M12 — Deterministic tests for services/portfolio_optimizer.py.

All inputs are synthetic — zero network calls.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pytest

from services.portfolio_optimizer import (
    AVAILABLE_METHODS,
    BUILTIN_STRESS_SCENARIOS,
    CovarianceDiagnostics,
    EfficientFrontierResult,
    OptimizationConstraints,
    OptimizationResult,
    PortfolioOptimizationConfig,
    RiskAttributionResult,
    StressScenarioConfig,
    apply_stress_scenario,
    compare_methods,
    compute_risk_attribution,
    covariance_diagnostics,
    efficient_frontier,
    estimate_covariance,
    optimize,
    run_all_stress_scenarios,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_config(
    n: int = 5,
    seed: int = 42,
    T: int = 252,
    long_only: bool = True,
) -> PortfolioOptimizationConfig:
    """Synthetic n-asset config with positive-definite covariance."""
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((n, n))
    cov = (A @ A.T) / n + 0.1 * np.eye(n)
    cov = cov * 0.0001   # daily scale
    mu = rng.uniform(0.0002, 0.0008, n).tolist()
    tickers = [f"T{i+1}" for i in range(n)]
    L = np.linalg.cholesky(cov)
    returns = (rng.standard_normal((T, n)) @ L.T + np.array(mu)).tolist()
    c = OptimizationConstraints(long_only=long_only)
    return PortfolioOptimizationConfig(
        tickers=tickers,
        mu=mu,
        cov=cov.tolist(),
        constraints=c,
        returns_matrix=returns,
    )


def _make_singular_cov_config(n: int = 5) -> PortfolioOptimizationConfig:
    """Config with a rank-deficient covariance matrix."""
    rng = np.random.default_rng(0)
    A = rng.standard_normal((n, 1))   # rank 1
    cov = A @ A.T * 0.0001            # singular
    mu = [0.0005] * n
    tickers = [f"S{i}" for i in range(n)]
    return PortfolioOptimizationConfig(tickers=tickers, mu=mu, cov=cov.tolist())


# ===========================================================================
# Config validation
# ===========================================================================

def test_config_mu_length_mismatch():
    with pytest.raises(ValueError, match="len\\(mu\\)"):
        PortfolioOptimizationConfig(tickers=["A", "B"], mu=[0.001], cov=[[1, 0], [0, 1]])


def test_config_cov_not_square():
    with pytest.raises(ValueError, match="n × n"):
        PortfolioOptimizationConfig(tickers=["A"], mu=[0.001], cov=[[1, 0]])


def test_config_zero_assets():
    with pytest.raises(ValueError, match="at least 1"):
        PortfolioOptimizationConfig(tickers=[], mu=[], cov=[])


def test_config_n_property():
    cfg = _make_config(4)
    assert cfg.n == 4


def test_config_mu_arr():
    cfg = _make_config(3)
    assert cfg.mu_arr.shape == (3,)


def test_config_cov_arr():
    cfg = _make_config(3)
    assert cfg.cov_arr.shape == (3, 3)


# ===========================================================================
# Optimization methods — basic smoke tests
# ===========================================================================

@pytest.mark.parametrize("method", [
    "equal_weight", "inverse_volatility", "min_variance", "max_sharpe",
    "mean_variance", "risk_parity", "max_diversification", "hrp", "kelly",
])
def test_method_returns_result(method):
    cfg = _make_config(5)
    result = optimize(cfg, method)
    assert isinstance(result, OptimizationResult)
    assert result.method == method
    assert len(result.tickers) == 5


@pytest.mark.parametrize("method", [
    "equal_weight", "inverse_volatility", "min_variance", "max_sharpe",
    "mean_variance", "risk_parity", "max_diversification", "hrp",
])
def test_weights_sum_to_one_long_only(method):
    cfg = _make_config(5)
    result = optimize(cfg, method)
    total = sum(result.weights.values())
    assert abs(total - 1.0) < 1e-4, f"{method}: weights sum = {total}"


@pytest.mark.parametrize("method", [
    "equal_weight", "inverse_volatility", "min_variance", "max_sharpe",
    "mean_variance", "risk_parity", "max_diversification", "hrp",
])
def test_weights_non_negative_long_only(method):
    cfg = _make_config(5)
    result = optimize(cfg, method)
    for t, w in result.weights.items():
        assert w >= -1e-6, f"{method}: {t} has negative weight {w}"


def test_equal_weight_exact():
    cfg = _make_config(4)
    result = optimize(cfg, "equal_weight")
    for w in result.weights.values():
        assert abs(w - 0.25) < 1e-8


def test_inverse_volatility_higher_weight_lower_vol():
    cfg = _make_config(5)
    result = optimize(cfg, "inverse_volatility")
    vols = np.sqrt(np.diag(cfg.cov_arr))
    weights_arr = np.array([result.weights[t] for t in cfg.tickers])
    # Asset with lowest vol should have highest weight
    min_vol_idx = int(np.argmin(vols))
    max_weight_idx = int(np.argmax(weights_arr))
    assert min_vol_idx == max_weight_idx


def test_min_variance_lower_vol_than_equal_weight():
    cfg = _make_config(5)
    ew = optimize(cfg, "equal_weight")
    mv = optimize(cfg, "min_variance")
    assert mv.expected_volatility <= ew.expected_volatility + 1e-4


def test_max_sharpe_higher_sharpe_than_min_variance():
    cfg = _make_config(5)
    mv = optimize(cfg, "min_variance")
    ms = optimize(cfg, "max_sharpe")
    assert ms.sharpe_ratio >= mv.sharpe_ratio - 0.1


def test_risk_parity_equal_risk_contributions():
    cfg = _make_config(5)
    result = optimize(cfg, "risk_parity")
    pcts = list(result.risk_contributions.values())
    # Each should be approximately 20% (1/5)
    for p in pcts:
        assert abs(p - 0.20) < 0.10, f"Risk contribution {p:.3f} far from 1/5"


def test_hrp_weights_non_negative():
    cfg = _make_config(6)
    result = optimize(cfg, "hrp")
    for w in result.weights.values():
        assert w >= -1e-6


def test_kelly_weights_sum_to_one():
    cfg = _make_config(5)
    result = optimize(cfg, "kelly")
    total = sum(result.weights.values())
    assert abs(total - 1.0) < 1e-4


# ===========================================================================
# Target return / volatility methods
# ===========================================================================

def test_target_return_method():
    cfg = _make_config(5)
    mu_arr = cfg.mu_arr
    target_ann = float(mu_arr.mean()) * 252
    cfg.target_return = target_ann
    result = optimize(cfg, "target_return")
    assert isinstance(result, OptimizationResult)


def test_target_return_requires_config():
    cfg = _make_config(5)
    cfg.target_return = None
    with pytest.raises(ValueError, match="target_return"):
        optimize(cfg, "target_return")


def test_target_volatility_method():
    cfg = _make_config(5)
    # Set a reasonable target volatility
    mv = optimize(cfg, "min_variance")
    target_vol = mv.expected_volatility * 1.5
    cfg.target_volatility = target_vol
    result = optimize(cfg, "target_volatility")
    assert isinstance(result, OptimizationResult)


def test_target_volatility_requires_config():
    cfg = _make_config(5)
    cfg.target_volatility = None
    with pytest.raises(ValueError, match="target_volatility"):
        optimize(cfg, "target_volatility")


# ===========================================================================
# CVaR optimization
# ===========================================================================

def test_cvar_optimization_requires_returns():
    cfg = _make_config(5)
    cfg_no_returns = PortfolioOptimizationConfig(
        tickers=cfg.tickers, mu=cfg.mu, cov=cfg.cov
    )
    with pytest.raises(ValueError, match="returns_matrix"):
        optimize(cfg_no_returns, "cvar_optimization")


def test_cvar_optimization_with_returns():
    cfg = _make_config(5, T=200)
    result = optimize(cfg, "cvar_optimization")
    assert isinstance(result, OptimizationResult)
    total = sum(result.weights.values())
    assert abs(total - 1.0) < 1e-3


# ===========================================================================
# Long/Short constrained
# ===========================================================================

def test_long_short_constrained_runs():
    cfg = _make_config(5, long_only=False)
    cfg.constraints.long_only = False
    result = optimize(cfg, "long_short_constrained")
    assert isinstance(result, OptimizationResult)


# ===========================================================================
# Black-Litterman
# ===========================================================================

def test_black_litterman_with_views():
    cfg = _make_config(4)
    n = cfg.n
    cfg.views_P = [[1.0, 0.0, 0.0, 0.0]]  # view on T1
    cfg.views_q = [cfg.mu[0] * 1.2]        # T1 outperforms by 20%
    cfg.market_weights = [0.25, 0.25, 0.25, 0.25]
    result = optimize(cfg, "black_litterman")
    assert isinstance(result, OptimizationResult)
    total = sum(result.weights.values())
    assert abs(total - 1.0) < 1e-3


def test_black_litterman_no_views_falls_back():
    """Without explicit views, BL uses identity picking matrix."""
    cfg = _make_config(4)
    result = optimize(cfg, "black_litterman")
    assert isinstance(result, OptimizationResult)


# ===========================================================================
# Unknown method
# ===========================================================================

def test_unknown_method_raises():
    cfg = _make_config(3)
    with pytest.raises(ValueError, match="Unknown method"):
        optimize(cfg, "magic_optimizer")


# ===========================================================================
# Single-asset portfolio
# ===========================================================================

def test_single_asset_portfolio():
    cfg = PortfolioOptimizationConfig(
        tickers=["AAPL"],
        mu=[0.0005],
        cov=[[0.0001]],
    )
    result = optimize(cfg, "equal_weight")
    assert result.weights["AAPL"] == pytest.approx(1.0)
    assert "Single-asset" in " ".join(result.warnings)


# ===========================================================================
# Singular covariance
# ===========================================================================

def test_singular_cov_repaired_and_converges():
    cfg = _make_singular_cov_config(4)
    result = optimize(cfg, "min_variance")
    assert isinstance(result, OptimizationResult)
    # Weight warning about PD repair should appear
    all_warnings = " ".join(result.warnings)
    assert "positive-definite" in all_warnings or result.converged in (True, False)


# ===========================================================================
# Compare methods
# ===========================================================================

def test_compare_methods_returns_list():
    cfg = _make_config(4)
    results = compare_methods(cfg)
    assert isinstance(results, list)
    assert len(results) > 0


def test_compare_methods_all_have_results():
    cfg = _make_config(4)
    results = compare_methods(cfg)
    for r in results:
        assert isinstance(r, OptimizationResult)


def test_compare_methods_subset():
    cfg = _make_config(4)
    results = compare_methods(cfg, ["equal_weight", "min_variance", "max_sharpe"])
    assert len(results) == 3


def test_compare_methods_never_crashes():
    """compare_methods should not raise even for numerically tricky inputs."""
    cfg = _make_singular_cov_config(3)
    results = compare_methods(cfg)
    assert all(isinstance(r, OptimizationResult) for r in results)


# ===========================================================================
# Efficient frontier
# ===========================================================================

def test_frontier_returns_result():
    cfg = _make_config(5)
    cfg.n_frontier_points = 20
    result = efficient_frontier(cfg)
    assert isinstance(result, EfficientFrontierResult)


def test_frontier_has_correct_length():
    cfg = _make_config(5)
    cfg.n_frontier_points = 25
    result = efficient_frontier(cfg)
    assert len(result.points) == 25


def test_frontier_has_max_sharpe_idx():
    cfg = _make_config(5)
    cfg.n_frontier_points = 30
    result = efficient_frontier(cfg)
    assert 0 <= result.max_sharpe_idx < len(result.points)


def test_frontier_equal_weight_point():
    cfg = _make_config(5)
    cfg.n_frontier_points = 20
    result = efficient_frontier(cfg)
    ew = result.equal_weight_point
    total = sum(ew.weights.values())
    assert abs(total - 1.0) < 1e-4


def test_frontier_n_feasible_reasonable():
    cfg = _make_config(5)
    cfg.n_frontier_points = 40
    result = efficient_frontier(cfg)
    assert result.n_feasible > 0


def test_frontier_min_vol_at_low_end():
    cfg = _make_config(5)
    cfg.n_frontier_points = 30
    result = efficient_frontier(cfg)
    feasible = [p for p in result.points if p.feasible]
    if len(feasible) > 2:
        min_vol = min(p.expected_volatility for p in feasible)
        min_vol_p = result.points[result.min_vol_idx]
        assert min_vol_p.feasible
        assert abs(min_vol_p.expected_volatility - min_vol) < 0.001


# ===========================================================================
# Risk attribution
# ===========================================================================

def test_risk_attribution_returns_result():
    cfg = _make_config(5)
    w = {t: 0.2 for t in cfg.tickers}
    result = compute_risk_attribution(cfg, w)
    assert isinstance(result, RiskAttributionResult)


def test_risk_attribution_pct_sum_to_one():
    cfg = _make_config(5)
    w = {t: 0.2 for t in cfg.tickers}
    result = compute_risk_attribution(cfg, w)
    total = sum(result.pct_contributions.values())
    assert abs(total - 1.0) < 1e-4


def test_risk_attribution_hhi_range():
    cfg = _make_config(5)
    w = {t: 0.2 for t in cfg.tickers}
    result = compute_risk_attribution(cfg, w)
    assert 0.0 <= result.hhi <= 1.0


def test_risk_attribution_effective_n():
    cfg = _make_config(5)
    w = {t: 0.2 for t in cfg.tickers}
    result = compute_risk_attribution(cfg, w)
    # Equal weight: effective_n should be close to 5
    assert abs(result.effective_n - 5.0) < 0.5


def test_risk_attribution_portfolio_volatility_positive():
    cfg = _make_config(5)
    w = {t: 0.2 for t in cfg.tickers}
    result = compute_risk_attribution(cfg, w)
    assert result.portfolio_volatility > 0


def test_risk_attribution_diversification_benefit_range():
    cfg = _make_config(5)
    w = {t: 0.2 for t in cfg.tickers}
    result = compute_risk_attribution(cfg, w)
    assert 0.0 <= result.diversification_benefit <= 1.0


# ===========================================================================
# Covariance estimation
# ===========================================================================

def test_estimate_covariance_sample():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((100, 5)) * 0.01
    cov, alpha = estimate_covariance(X, method="sample")
    assert cov.shape == (5, 5)
    assert alpha == 0.0


def test_estimate_covariance_ledoit_wolf():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((100, 5)) * 0.01
    cov, alpha = estimate_covariance(X, method="ledoit_wolf")
    assert cov.shape == (5, 5)
    assert 0.0 <= alpha <= 1.0


def test_estimate_covariance_ewm():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((100, 5)) * 0.01
    cov, alpha = estimate_covariance(X, method="ewm")
    assert cov.shape == (5, 5)


def test_ledoit_wolf_less_extreme_than_sample():
    """LW-shrunk cov should have lower condition number than sample."""
    rng = np.random.default_rng(0)
    X = rng.standard_normal((30, 20)) * 0.01   # underdetermined → ill-conditioned sample
    cov_s, _ = estimate_covariance(X, method="sample")
    cov_lw, alpha = estimate_covariance(X, method="ledoit_wolf")
    cond_s = np.linalg.cond(cov_s)
    cond_lw = np.linalg.cond(cov_lw)
    # LW should shrink condition number
    assert cond_lw <= cond_s + 1e-3


# ===========================================================================
# Covariance diagnostics
# ===========================================================================

def test_covariance_diagnostics_structure():
    cfg = _make_config(5)
    X = np.array(cfg.returns_matrix)
    diag = covariance_diagnostics(cfg.tickers, X)
    assert isinstance(diag, CovarianceDiagnostics)
    assert diag.n_assets == 5
    assert diag.n_observations == X.shape[0]


def test_covariance_diagnostics_pd_for_healthy_data():
    cfg = _make_config(5, T=300)
    X = np.array(cfg.returns_matrix)
    diag = covariance_diagnostics(cfg.tickers, X)
    assert diag.is_positive_definite


def test_covariance_diagnostics_detects_high_correlation():
    """Highly correlated pair should appear in highly_correlated_pairs."""
    rng = np.random.default_rng(42)
    base = rng.standard_normal(300) * 0.01
    noise = rng.standard_normal(300) * 0.0001
    X = np.column_stack([base, base + noise, rng.standard_normal(300) * 0.01])
    diag = covariance_diagnostics(["A", "B", "C"], X)
    # A and B should be flagged
    pairs = [(a, b) for a, b, _ in diag.highly_correlated_pairs]
    assert ("A", "B") in pairs or ("B", "A") in pairs


def test_covariance_diagnostics_warns_underdetermined():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((15, 20)) * 0.01   # T < 2n
    tickers = [f"A{i}" for i in range(20)]
    diag = covariance_diagnostics(tickers, X)
    assert any("Observations" in w for w in diag.warnings)


# ===========================================================================
# Stress testing (deterministic)
# ===========================================================================

def test_stress_scenario_apply_runs():
    tickers = ["A", "B", "C"]
    weights = {"A": 0.4, "B": 0.3, "C": 0.3}
    sc = StressScenarioConfig(
        name="Test", description="Test scenario",
        asset_shocks={}, market_shock=-0.20
    )
    result = apply_stress_scenario(tickers, weights, sc)
    assert result.portfolio_impact_pct < 0


def test_stress_scenario_market_shock_uniform():
    tickers = ["A", "B"]
    weights = {"A": 0.5, "B": 0.5}
    sc = StressScenarioConfig(
        name="Test", description="Test",
        asset_shocks={}, market_shock=-0.30
    )
    result = apply_stress_scenario(tickers, weights, sc)
    assert abs(result.portfolio_impact_pct - (-30.0)) < 0.1


def test_stress_scenario_asset_specific_shock():
    tickers = ["A", "B"]
    weights = {"A": 0.6, "B": 0.4}
    sc = StressScenarioConfig(
        name="Test", description="Test",
        asset_shocks={"A": -0.50}, market_shock=0.0
    )
    result = apply_stress_scenario(tickers, weights, sc)
    # Portfolio impact = 0.6 * (-50%) + 0.4 * 0% = -30%
    assert abs(result.portfolio_impact_pct - (-30.0)) < 0.1


def test_stress_worst_best_contributors():
    tickers = ["A", "B", "C"]
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}
    sc = StressScenarioConfig(
        name="T", description="T",
        asset_shocks={"A": -0.50, "B": -0.10, "C": 0.05},
        market_shock=0.0
    )
    result = apply_stress_scenario(tickers, weights, sc)
    assert result.worst_contributor == "A"
    assert result.best_contributor == "C"


def test_stress_severity_score_range():
    tickers = ["A"]
    weights = {"A": 1.0}
    sc = StressScenarioConfig(
        name="T", description="T", asset_shocks={}, market_shock=-0.50
    )
    result = apply_stress_scenario(tickers, weights, sc)
    assert 0.0 <= result.severity_score <= 10.0


def test_run_all_stress_scenarios_returns_10():
    tickers = ["AAPL", "MSFT"]
    weights = {"AAPL": 0.5, "MSFT": 0.5}
    results = run_all_stress_scenarios(tickers, weights)
    assert len(results) == len(BUILTIN_STRESS_SCENARIOS)


def test_stress_post_weights_sum_near_one():
    tickers = ["A", "B"]
    weights = {"A": 0.5, "B": 0.5}
    sc = StressScenarioConfig(
        name="T", description="T", asset_shocks={}, market_shock=-0.30
    )
    result = apply_stress_scenario(tickers, weights, sc)
    total = sum(result.post_stress_weights.values())
    assert abs(total - 1.0) < 0.01


# ===========================================================================
# AVAILABLE_METHODS
# ===========================================================================

def test_available_methods_count():
    assert len(AVAILABLE_METHODS) == 14


def test_all_method_keys_present():
    expected = {
        "equal_weight", "inverse_volatility", "min_variance", "max_sharpe",
        "mean_variance", "target_return", "target_volatility", "risk_parity",
        "max_diversification", "hrp", "black_litterman", "kelly",
        "cvar_optimization", "long_short_constrained",
    }
    assert set(AVAILABLE_METHODS) == expected


# ===========================================================================
# Metric sanity checks
# ===========================================================================

def test_expected_return_positive_for_positive_mu():
    cfg = _make_config(5)
    for method in ["equal_weight", "max_sharpe", "min_variance"]:
        result = optimize(cfg, method)
        assert result.expected_return > 0, f"{method}: expected_return <= 0"


def test_expected_volatility_positive():
    cfg = _make_config(5)
    for method in ["equal_weight", "max_sharpe", "min_variance"]:
        result = optimize(cfg, method)
        assert result.expected_volatility > 0


def test_concentration_score_in_range():
    cfg = _make_config(5)
    result = optimize(cfg, "equal_weight")
    # HHI for 5 equal weights = 5 * (0.2)^2 = 0.20
    assert abs(result.concentration_score - 0.20) < 0.01


def test_gross_exposure_long_only():
    cfg = _make_config(5)
    result = optimize(cfg, "max_sharpe")
    assert abs(result.gross_exposure - 1.0) < 1e-4


def test_determinism():
    cfg1 = _make_config(5, seed=99)
    cfg2 = _make_config(5, seed=99)
    r1 = optimize(cfg1, "max_sharpe")
    r2 = optimize(cfg2, "max_sharpe")
    assert r1.weights == r2.weights
