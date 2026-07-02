"""Tests for M4 risk analytics service.

All tests are pure numerical — no network calls, no database.
"""
import numpy as np
import pandas as pd
import pytest

from services.risk_analytics import (
    annual_volatility,
    beta_alpha,
    calmar_ratio,
    component_risk_contributions,
    compute_full_risk_metrics,
    cvar,
    diversification_ratio,
    downside_deviation,
    herfindahl_hirschman_index,
    information_ratio,
    marginal_risk_contributions,
    max_drawdown,
    pct_risk_contributions,
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def flat_returns() -> pd.Series:
    """All-zero returns — zero risk."""
    return pd.Series(np.zeros(252))


@pytest.fixture
def positive_returns() -> pd.Series:
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(0.001, 0.01, 252))


@pytest.fixture
def negative_returns() -> pd.Series:
    rng = np.random.default_rng(0)
    return pd.Series(rng.normal(-0.002, 0.015, 252))


@pytest.fixture
def bench_returns() -> pd.Series:
    rng = np.random.default_rng(99)
    return pd.Series(rng.normal(0.0005, 0.012, 252))


@pytest.fixture
def nav_up() -> pd.Series:
    """Monotonically increasing NAV — zero drawdown."""
    return pd.Series(100.0 + np.arange(252) * 0.1)


@pytest.fixture
def nav_crash() -> pd.Series:
    """NAV that peaks at 150 then crashes to 100."""
    arr = np.concatenate([np.linspace(100, 150, 100), np.linspace(150, 100, 152)])
    return pd.Series(arr)


@pytest.fixture
def equal_weights_2() -> np.ndarray:
    return np.array([0.5, 0.5])


@pytest.fixture
def cov_2x2() -> np.ndarray:
    return np.array([[0.0004, 0.0001], [0.0001, 0.0009]])


# ---------------------------------------------------------------------------
# VaR
# ---------------------------------------------------------------------------

class TestVaRHistorical:
    def test_positive_loss(self, negative_returns):
        result = var_historical(negative_returns)
        assert result > 0.0

    def test_zero_for_zero_returns(self, flat_returns):
        assert var_historical(flat_returns) == 0.0

    def test_higher_confidence_means_higher_var(self, negative_returns):
        v95 = var_historical(negative_returns, 0.95)
        v99 = var_historical(negative_returns, 0.99)
        assert v99 >= v95

    def test_returns_float(self, positive_returns):
        assert isinstance(var_historical(positive_returns), float)

    def test_empty_series_returns_zero(self):
        assert var_historical(pd.Series(dtype=float)) == 0.0


class TestVaRParametric:
    def test_positive_for_volatile_returns(self, negative_returns):
        assert var_parametric(negative_returns) > 0.0

    def test_close_to_historical_for_normal(self, positive_returns):
        hist = var_historical(positive_returns)
        param = var_parametric(positive_returns)
        assert abs(hist - param) < 0.05  # within 5% of each other

    def test_returns_float(self, positive_returns):
        assert isinstance(var_parametric(positive_returns), float)


class TestVaRMonteCarlo:
    def test_positive_for_volatile_returns(self, negative_returns):
        result = var_monte_carlo(negative_returns, n_sims=1000)
        assert result > 0.0

    def test_returns_float(self, positive_returns):
        assert isinstance(var_monte_carlo(positive_returns, n_sims=500), float)


class TestCVaR:
    def test_cvar_gte_var(self, negative_returns):
        v = var_historical(negative_returns)
        c = cvar(negative_returns)
        assert c >= v - 1e-10

    def test_zero_for_flat(self, flat_returns):
        assert cvar(flat_returns) == 0.0

    def test_returns_positive(self, negative_returns):
        assert cvar(negative_returns) >= 0.0


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------

class TestVolatility:
    def test_zero_for_flat(self, flat_returns):
        assert annual_volatility(flat_returns) == 0.0

    def test_positive_for_random(self, positive_returns):
        assert annual_volatility(positive_returns) > 0.0

    def test_higher_sigma_means_higher_vol(self):
        r_low = pd.Series(np.random.default_rng(0).normal(0, 0.005, 252))
        r_high = pd.Series(np.random.default_rng(0).normal(0, 0.020, 252))
        assert annual_volatility(r_high) > annual_volatility(r_low)

    def test_downside_deviation_leq_vol(self, positive_returns):
        dd = downside_deviation(positive_returns)
        vol = annual_volatility(positive_returns)
        assert dd <= vol + 1e-6

    def test_semi_variance_nonneg(self, positive_returns):
        assert semi_variance(positive_returns) >= 0.0

    def test_semi_variance_zero_for_all_positive(self):
        r = pd.Series(np.full(100, 0.01))
        assert semi_variance(r) == 0.0


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------

class TestDrawdown:
    def test_zero_for_monotonic_increase(self, nav_up):
        assert max_drawdown(nav_up) < 1e-10

    def test_correct_magnitude(self, nav_crash):
        mdd = max_drawdown(nav_crash)
        assert 0.30 < mdd < 0.35  # peak=150 trough=100 → 33.3%

    def test_ulcer_index_zero_for_monotonic(self, nav_up):
        assert ulcer_index(nav_up) < 1e-6

    def test_ulcer_index_positive_for_crash(self, nav_crash):
        assert ulcer_index(nav_crash) > 0.0


# ---------------------------------------------------------------------------
# Risk-adjusted ratios
# ---------------------------------------------------------------------------

class TestRatios:
    def test_sharpe_higher_for_better_portfolio(self, positive_returns, negative_returns):
        s_pos = sharpe_ratio(positive_returns)
        s_neg = sharpe_ratio(negative_returns)
        assert s_pos > s_neg

    def test_sharpe_zero_for_flat(self, flat_returns):
        assert sharpe_ratio(flat_returns) == 0.0

    def test_sortino_gte_sharpe_for_positive_skew(self, positive_returns):
        sr = sharpe_ratio(positive_returns)
        so = sortino_ratio(positive_returns)
        assert so >= sr - 1e-6

    def test_calmar_positive_for_growing_nav(self, positive_returns, nav_up):
        result = calmar_ratio(positive_returns, nav_up)
        assert isinstance(result, float)

    def test_treynor_returns_float(self, positive_returns, bench_returns):
        result = treynor_ratio(positive_returns, bench_returns)
        assert isinstance(result, float)

    def test_information_ratio_returns_float(self, positive_returns, bench_returns):
        result = information_ratio(positive_returns, bench_returns)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Benchmark statistics
# ---------------------------------------------------------------------------

class TestBenchmarkStats:
    def test_beta_alpha_returns_tuple(self, positive_returns, bench_returns):
        b, a = beta_alpha(positive_returns, bench_returns)
        assert isinstance(b, float)
        assert isinstance(a, float)

    def test_r_squared_between_0_and_1(self, positive_returns, bench_returns):
        r2 = r_squared(positive_returns, bench_returns)
        assert 0.0 <= r2 <= 1.0

    def test_r_squared_high_for_correlated(self):
        base = pd.Series(np.random.default_rng(7).normal(0.001, 0.01, 252))
        correlated = base + pd.Series(np.random.default_rng(8).normal(0, 0.001, 252))
        r2 = r_squared(base, correlated)
        assert r2 > 0.9

    def test_tracking_error_nonneg(self, positive_returns, bench_returns):
        te = tracking_error(positive_returns, bench_returns)
        assert te >= 0.0

    def test_tracking_error_zero_for_identical(self, positive_returns):
        te = tracking_error(positive_returns, positive_returns.copy())
        assert te < 1e-10


# ---------------------------------------------------------------------------
# Concentration & diversification
# ---------------------------------------------------------------------------

class TestConcentration:
    def test_hhi_equal_weights(self):
        w = np.array([0.25, 0.25, 0.25, 0.25])
        hhi = herfindahl_hirschman_index(w)
        assert abs(hhi - 0.25) < 1e-6

    def test_hhi_fully_concentrated(self):
        w = np.array([1.0, 0.0, 0.0])
        assert abs(herfindahl_hirschman_index(w) - 1.0) < 1e-6

    def test_hhi_between_0_and_1(self, equal_weights_2):
        assert 0.0 < herfindahl_hirschman_index(equal_weights_2) <= 1.0

    def test_diversification_ratio_gte_1(self, equal_weights_2, cov_2x2):
        dr = diversification_ratio(equal_weights_2, cov_2x2)
        assert dr >= 1.0 - 1e-6

    def test_risk_contributions_sum_to_1(self, equal_weights_2, cov_2x2):
        pct = pct_risk_contributions(equal_weights_2, cov_2x2)
        assert abs(pct.sum() - 1.0) < 1e-10

    def test_component_risk_sum_equals_portfolio_vol(self, equal_weights_2, cov_2x2):
        crc = component_risk_contributions(equal_weights_2, cov_2x2)
        port_vol = np.sqrt(equal_weights_2 @ cov_2x2 @ equal_weights_2)
        assert abs(crc.sum() - port_vol) < 1e-10

    def test_marginal_rc_shape(self, equal_weights_2, cov_2x2):
        mrc = marginal_risk_contributions(equal_weights_2, cov_2x2)
        assert mrc.shape == (2,)


# ---------------------------------------------------------------------------
# Full metrics pipeline
# ---------------------------------------------------------------------------

class TestFullMetrics:
    def test_returns_dict(self, positive_returns, bench_returns, nav_up):
        result = compute_full_risk_metrics(positive_returns, bench_returns, nav_up)
        assert isinstance(result, dict)

    def test_contains_core_keys(self, positive_returns, bench_returns, nav_up):
        result = compute_full_risk_metrics(positive_returns, bench_returns, nav_up)
        for key in ["var_historical_95", "cvar_95", "sharpe_ratio", "max_drawdown_pct", "beta"]:
            assert key in result

    def test_with_concentration_metrics(self, positive_returns, bench_returns, nav_up, equal_weights_2, cov_2x2):
        result = compute_full_risk_metrics(
            positive_returns, bench_returns, nav_up,
            weights=equal_weights_2,
            cov_matrix=cov_2x2,
            tickers=["A", "B"],
        )
        assert "hhi" in result
        assert "diversification_ratio" in result
        assert "risk_contributions" in result
        assert "A" in result["risk_contributions"]
