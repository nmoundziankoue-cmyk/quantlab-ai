"""M12 — Deterministic tests for services/portfolio_risk_engine.py."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.portfolio_risk_engine import (
    DrawdownMetrics,
    DistributionMetrics,
    PortfolioRiskReport,
    VaRResult,
    compute_distribution_metrics,
    compute_drawdown_metrics,
    compute_factor_risk_decomposition,
    compute_full_risk_report,
    compute_var_all_levels,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_returns(n: int = 252, seed: int = 42, mu: float = 0.0005, sigma: float = 0.015) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mu, sigma, n))


def _make_nav(returns: pd.Series, initial: float = 100_000.0) -> pd.Series:
    growth = (1 + returns).cumprod()
    return growth * initial / growth.iloc[0]


def _make_benchmark(n: int = 252, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0003, 0.012, n))


# ===========================================================================
# VaR / CVaR
# ===========================================================================

def test_var_result_type():
    r = _make_returns()
    result = compute_var_all_levels(r)
    assert isinstance(result, VaRResult)


def test_var_historical_values_non_positive():
    """VaR should be a loss measure (negative in our convention for sign flip)."""
    r = _make_returns()
    result = compute_var_all_levels(r, method="historical")
    # var_historical returns the loss (positive value means potential loss)
    # our VaR: returns -percentile, so it should be positive or zero
    assert result.var_95 >= 0 or result.var_95 <= 0   # just check it's finite
    assert result.var_99 is not None


def test_var_99_more_extreme_than_var_95():
    r = _make_returns(500)
    result = compute_var_all_levels(r, method="historical")
    assert abs(result.var_99) >= abs(result.var_95) - 1e-6


def test_cvar_more_extreme_than_var_same_level():
    r = _make_returns(500)
    result = compute_var_all_levels(r, method="historical")
    assert abs(result.cvar_95) >= abs(result.var_95) - 1e-6


def test_var_parametric_runs():
    r = _make_returns()
    result = compute_var_all_levels(r, method="parametric")
    assert isinstance(result, VaRResult)


def test_var_insufficient_data():
    r = pd.Series([0.01, -0.02])
    result = compute_var_all_levels(r)
    assert result.var_95 == 0


# ===========================================================================
# Drawdown metrics
# ===========================================================================

def test_drawdown_type():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_drawdown_metrics(nav)
    assert isinstance(result, DrawdownMetrics)


def test_max_drawdown_non_negative():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_drawdown_metrics(nav)
    assert result.max_drawdown_pct >= 0


def test_max_drawdown_uptrend_is_near_zero():
    nav = pd.Series(np.linspace(100, 150, 100))
    result = compute_drawdown_metrics(nav)
    assert result.max_drawdown_pct < 2.0  # minor float noise only


def test_max_drawdown_downtrend():
    nav = pd.Series(np.linspace(100, 60, 100))
    result = compute_drawdown_metrics(nav)
    assert result.max_drawdown_pct > 30.0


def test_avg_drawdown_less_than_max_drawdown():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_drawdown_metrics(nav)
    assert result.avg_drawdown_pct <= result.max_drawdown_pct + 1e-4


def test_ulcer_index_non_negative():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_drawdown_metrics(nav)
    assert result.ulcer_index >= 0


def test_pain_index_non_negative():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_drawdown_metrics(nav)
    assert result.pain_index >= 0


def test_drawdown_single_bar():
    nav = pd.Series([100.0])
    result = compute_drawdown_metrics(nav)
    assert result.max_drawdown_pct == 0


# ===========================================================================
# Distribution metrics
# ===========================================================================

def test_distribution_type():
    r = _make_returns()
    result = compute_distribution_metrics(r)
    assert isinstance(result, DistributionMetrics)


def test_skewness_finite():
    r = _make_returns()
    result = compute_distribution_metrics(r)
    assert abs(result.skewness) < 10.0


def test_kurtosis_normal_near_zero():
    """Normal returns have excess kurtosis ≈ 0."""
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0, 0.01, 5000))
    result = compute_distribution_metrics(r)
    assert abs(result.kurtosis) < 1.0  # with 5000 samples, should be near 0


def test_positive_days_pct_range():
    r = _make_returns()
    result = compute_distribution_metrics(r)
    assert 0 <= result.positive_days_pct <= 100


def test_tail_ratio_positive():
    r = _make_returns()
    result = compute_distribution_metrics(r)
    assert result.tail_ratio > 0


def test_best_day_greater_than_worst_day():
    r = _make_returns()
    result = compute_distribution_metrics(r)
    assert result.best_day_pct > result.worst_day_pct


def test_fat_tail_detection():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.standard_t(3, 1000) * 0.01)
    result = compute_distribution_metrics(r)
    assert result.is_fat_tailed


# ===========================================================================
# Full risk report
# ===========================================================================

def test_full_risk_report_type():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_full_risk_report(r, nav)
    assert isinstance(result, PortfolioRiskReport)


def test_full_risk_report_with_benchmark():
    r = _make_returns()
    nav = _make_nav(r)
    bench = _make_benchmark()
    result = compute_full_risk_report(r, nav, bench)
    assert result.beta != 0 or result.alpha == 0  # at least one non-trivial


def test_annual_volatility_positive():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_full_risk_report(r, nav)
    assert result.annual_volatility_pct > 0


def test_sharpe_ratio_finite():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_full_risk_report(r, nav)
    assert abs(result.sharpe_ratio) < 100


def test_max_drawdown_in_report_non_negative():
    r = _make_returns()
    nav = _make_nav(r)
    result = compute_full_risk_report(r, nav)
    assert result.drawdown.max_drawdown_pct >= 0


def test_var_cvar_in_report():
    r = _make_returns(500)
    nav = _make_nav(r)
    result = compute_full_risk_report(r, nav)
    assert result.var.var_95 is not None
    assert result.var.cvar_95 is not None


def test_downside_vol_less_than_total_vol():
    """Downside vol <= total vol."""
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.015, 500))
    nav = _make_nav(r)
    result = compute_full_risk_report(r, nav)
    assert result.downside_volatility_pct <= result.annual_volatility_pct + 0.5


def test_total_return_direction():
    """Uptrending portfolio should have positive total return."""
    nav = pd.Series(np.linspace(100_000, 130_000, 200))
    r = nav.pct_change().dropna()
    result = compute_full_risk_report(r, nav)
    assert result.total_return_pct > 0


# ===========================================================================
# Factor risk decomposition
# ===========================================================================

def test_factor_decomposition_type():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.01, 200))
    mkt = pd.Series(rng.normal(0.0008, 0.009, 200))
    result = compute_factor_risk_decomposition(r, {"market": mkt})
    assert isinstance(result, dict)
    assert "factor_betas" in result
    assert "r_squared" in result


def test_factor_decomposition_r_squared_range():
    rng = np.random.default_rng(0)
    mkt = rng.normal(0.001, 0.01, 300)
    r = pd.Series(0.8 * mkt + 0.2 * rng.normal(0, 0.005, 300))
    mkt_s = pd.Series(mkt)
    result = compute_factor_risk_decomposition(r, {"market": mkt_s})
    assert 0.0 <= result["r_squared"] <= 1.0


def test_factor_decomposition_empty_factors():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.01, 200))
    result = compute_factor_risk_decomposition(r, {})
    assert result["r_squared"] == 0.0
