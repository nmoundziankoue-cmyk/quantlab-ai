"""Tests for M4 portfolio optimization service.

All tests are pure numerical — no network calls, no database.
"""
import numpy as np
import pandas as pd
import pytest

from services.optimization import (
    AVAILABLE_METHODS,
    black_litterman_mu,
    efficient_frontier,
    equal_weight,
    equal_weight,
    hierarchical_risk_parity,
    max_diversification,
    max_sharpe,
    min_variance,
    risk_parity,
    run_optimization,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tickers():
    return ["AAPL", "MSFT", "GOOG", "AMZN"]


@pytest.fixture
def mu(tickers):
    return np.array([0.0006, 0.0005, 0.0004, 0.0003])


@pytest.fixture
def cov(tickers):
    rng = np.random.default_rng(42)
    A = rng.normal(0, 0.01, (4, 4))
    return A.T @ A + np.diag([0.0001] * 4)


@pytest.fixture
def returns_df(tickers):
    rng = np.random.default_rng(77)
    data = rng.normal(0.0003, 0.012, (252, 4))
    return pd.DataFrame(data, columns=tickers)


# ---------------------------------------------------------------------------
# Helper assertions
# ---------------------------------------------------------------------------

def _assert_valid_result(result: dict, method: str, tickers: list):
    assert result["method"] == method
    assert "weights" in result
    assert "expected_return" in result
    assert "expected_volatility" in result
    assert "sharpe_ratio" in result
    weights = list(result["weights"].values())
    assert len(weights) == len(tickers)
    total = sum(weights)
    assert abs(total - 1.0) < 1e-4, f"Weights sum to {total}, not 1.0"
    for w in weights:
        assert w >= -1e-4, f"Negative weight: {w}"


# ---------------------------------------------------------------------------
# Equal weight
# ---------------------------------------------------------------------------

class TestEqualWeight:
    def test_weights_uniform(self, tickers, mu, cov):
        result = equal_weight(tickers, mu, cov)
        for w in result["weights"].values():
            assert abs(w - 0.25) < 1e-10

    def test_valid_result(self, tickers, mu, cov):
        _assert_valid_result(equal_weight(tickers, mu, cov), "equal_weight", tickers)


# ---------------------------------------------------------------------------
# Min variance
# ---------------------------------------------------------------------------

class TestMinVariance:
    def test_valid_result(self, tickers, mu, cov):
        result = min_variance(tickers, mu, cov)
        _assert_valid_result(result, "min_variance", tickers)

    def test_lower_vol_than_equal_weight(self, tickers, mu, cov):
        ew = equal_weight(tickers, mu, cov)
        mv = min_variance(tickers, mu, cov)
        assert mv["expected_volatility"] <= ew["expected_volatility"] + 1e-6

    def test_converged(self, tickers, mu, cov):
        result = min_variance(tickers, mu, cov)
        assert result.get("converged") is True


# ---------------------------------------------------------------------------
# Max Sharpe
# ---------------------------------------------------------------------------

class TestMaxSharpe:
    def test_valid_result(self, tickers, mu, cov):
        result = max_sharpe(tickers, mu, cov)
        _assert_valid_result(result, "max_sharpe", tickers)

    def test_higher_sharpe_than_equal_weight(self, tickers, mu, cov):
        ew = equal_weight(tickers, mu, cov)
        ms = max_sharpe(tickers, mu, cov)
        assert ms["sharpe_ratio"] >= ew["sharpe_ratio"] - 1e-4

    def test_converged(self, tickers, mu, cov):
        result = max_sharpe(tickers, mu, cov)
        assert result.get("converged") is True


# ---------------------------------------------------------------------------
# Risk parity
# ---------------------------------------------------------------------------

class TestRiskParity:
    def test_valid_result(self, tickers, mu, cov):
        result = risk_parity(tickers, mu, cov)
        _assert_valid_result(result, "risk_parity", tickers)

    def test_approximately_equal_risk_contributions(self, tickers, mu, cov):
        from services.risk_analytics import pct_risk_contributions
        result = risk_parity(tickers, mu, cov)
        w = np.array(list(result["weights"].values()))
        pct = pct_risk_contributions(w, cov)
        # Each asset should contribute ~25% to total risk (within 10%)
        for p in pct:
            assert abs(p - 0.25) < 0.10, f"Risk contribution {p:.3f} too far from 0.25"


# ---------------------------------------------------------------------------
# Max diversification
# ---------------------------------------------------------------------------

class TestMaxDiversification:
    def test_valid_result(self, tickers, mu, cov):
        result = max_diversification(tickers, mu, cov)
        _assert_valid_result(result, "max_diversification", tickers)

    def test_dr_gte_equal_weight(self, tickers, mu, cov):
        from services.risk_analytics import diversification_ratio
        ew = equal_weight(tickers, mu, cov)
        md = max_diversification(tickers, mu, cov)
        w_ew = np.array(list(ew["weights"].values()))
        w_md = np.array(list(md["weights"].values()))
        dr_ew = diversification_ratio(w_ew, cov)
        dr_md = diversification_ratio(w_md, cov)
        assert dr_md >= dr_ew - 1e-4


# ---------------------------------------------------------------------------
# HRP
# ---------------------------------------------------------------------------

class TestHRP:
    def test_valid_result(self, tickers, mu, cov):
        result = hierarchical_risk_parity(tickers, mu, cov)
        _assert_valid_result(result, "hrp", tickers)

    def test_two_assets(self):
        t = ["A", "B"]
        mu = np.array([0.001, 0.002])
        cov = np.array([[0.0004, 0.0001], [0.0001, 0.0009]])
        result = hierarchical_risk_parity(t, mu, cov)
        _assert_valid_result(result, "hrp", t)


# ---------------------------------------------------------------------------
# Black-Litterman
# ---------------------------------------------------------------------------

class TestBlackLitterman:
    def test_shifts_return_toward_view(self, mu, cov):
        market_weights = np.array([0.25, 0.25, 0.25, 0.25])
        # Two views: AAPL outperforms AMZN by 2% annual = ~7.9e-5 daily
        P = np.array([[1.0, 0.0, 0.0, -1.0]])
        q = np.array([0.02 / 252])
        mu_bl_positive = black_litterman_mu(market_weights, cov, P, q)
        # Opposite view: AAPL underperforms
        q_neg = np.array([-0.02 / 252])
        mu_bl_negative = black_litterman_mu(market_weights, cov, P, q_neg)
        assert mu_bl_positive.shape == (4,)
        # Positive view on AAPL should push its expected return above the negative-view case
        assert mu_bl_positive[0] > mu_bl_negative[0]

    def test_output_shape(self, mu, cov):
        market_weights = np.array([0.25, 0.25, 0.25, 0.25])
        P = np.eye(4)
        q = mu.copy()
        mu_bl = black_litterman_mu(market_weights, cov, P, q)
        assert mu_bl.shape == (4,)


# ---------------------------------------------------------------------------
# Efficient frontier
# ---------------------------------------------------------------------------

class TestEfficientFrontier:
    def test_returns_list_of_dicts(self, tickers, mu, cov):
        points = efficient_frontier(tickers, mu, cov, n_points=10)
        assert isinstance(points, list)
        assert len(points) > 0

    def test_each_point_has_required_keys(self, tickers, mu, cov):
        points = efficient_frontier(tickers, mu, cov, n_points=10)
        for p in points:
            for key in ["expected_return", "expected_volatility", "sharpe_ratio", "weights"]:
                assert key in p

    def test_points_sorted_by_return(self, tickers, mu, cov):
        points = efficient_frontier(tickers, mu, cov, n_points=10)
        rets = [p["expected_return"] for p in points]
        assert rets == sorted(rets)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class TestDispatcher:
    def test_all_methods_available(self):
        assert len(AVAILABLE_METHODS) >= 5

    def test_run_optimization_equal_weight(self, tickers, returns_df):
        result = run_optimization("equal_weight", tickers, returns_df)
        assert result["method"] == "equal_weight"

    def test_run_optimization_unknown_method(self, tickers, returns_df):
        with pytest.raises(ValueError, match="Unknown optimization method"):
            run_optimization("nonexistent", tickers, returns_df)

    def test_run_optimization_insufficient_assets(self, returns_df):
        with pytest.raises(ValueError, match="at least 2 assets"):
            run_optimization("equal_weight", ["AAPL"], returns_df)

    @pytest.mark.parametrize("method", ["equal_weight", "min_variance", "max_sharpe", "risk_parity", "max_diversification", "hrp"])
    def test_all_methods_run(self, method, tickers, returns_df):
        result = run_optimization(method, tickers, returns_df)
        assert result["method"] == method
        assert "weights" in result
