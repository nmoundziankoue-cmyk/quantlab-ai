"""Tests for M19 OptimizationLab service."""

import math
import pytest
from services.m19_optimization_lab import (
    OptimizationLab,
    OptimizationResult,
    OptimizationType,
    FrontierPoint,
    WeightConstraint,
    _mat_inv,
    _mat_mul,
    _mat_T,
)


def two_asset_setup():
    tickers = ["AAPL", "MSFT"]
    exp_rets = {"AAPL": 0.12, "MSFT": 0.10}
    cov = {
        "AAPL": {"AAPL": 0.04, "MSFT": 0.01},
        "MSFT": {"AAPL": 0.01, "MSFT": 0.03},
    }
    return tickers, exp_rets, cov


def three_asset_setup():
    tickers = ["AAPL", "MSFT", "JPM"]
    exp_rets = {"AAPL": 0.15, "MSFT": 0.12, "JPM": 0.08}
    cov = {
        "AAPL": {"AAPL": 0.04, "MSFT": 0.015, "JPM": 0.005},
        "MSFT": {"AAPL": 0.015, "MSFT": 0.035, "JPM": 0.005},
        "JPM": {"AAPL": 0.005, "MSFT": 0.005, "JPM": 0.025},
    }
    return tickers, exp_rets, cov


class TestOptimizationLabInit:
    def test_created(self):
        lab = OptimizationLab()
        assert lab is not None

    def test_starts_empty(self):
        lab = OptimizationLab()
        assert lab.list_results() == []

    def test_reset_clears_results(self):
        lab = OptimizationLab()
        tickers, er, cov = two_asset_setup()
        lab.mean_variance(tickers, er, cov)
        lab.reset()
        assert lab.list_results() == []

    def test_get_nonexistent_none(self):
        lab = OptimizationLab()
        assert lab.get_result("fake") is None


class TestMeanVariance:
    def setup_method(self):
        self.lab = OptimizationLab()

    def test_returns_result(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        assert result is not None

    def test_weights_sum_to_one(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-3

    def test_weights_non_negative(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        for w in result.weights.values():
            assert w >= -1e-6

    def test_all_tickers_in_weights(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        for t in tickers:
            assert t in result.weights

    def test_has_expected_return(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        assert isinstance(result.expected_return, float)

    def test_has_volatility(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        assert result.volatility > 0

    def test_has_sharpe(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        assert isinstance(result.sharpe_ratio, float)

    def test_high_risk_aversion_shifts_to_low_vol(self):
        tickers, er, cov = three_asset_setup()
        low_ra = self.lab.mean_variance(tickers, er, cov, risk_aversion=0.5)
        high_ra = self.lab.mean_variance(tickers, er, cov, risk_aversion=10.0)
        assert high_ra.volatility <= low_ra.volatility + 0.01

    def test_cached_by_result_id(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        cached = self.lab.get_result(result.result_id)
        assert cached is not None

    def test_optimization_type(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        assert result.optimization_type == OptimizationType.MEAN_VARIANCE

    def test_with_weight_constraints(self):
        tickers, er, cov = three_asset_setup()
        constraints = [WeightConstraint(ticker="AAPL", min_weight=0.2, max_weight=0.4)]
        result = self.lab.mean_variance(tickers, er, cov, constraints=constraints)
        aapl_w = result.weights.get("AAPL", 0.0)
        assert aapl_w >= 0.15

    def test_num_assets_field(self):
        tickers, er, cov = three_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        assert result.num_assets >= 1

    def test_risk_contributions_sum_to_one(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        total = sum(result.risk_contributions.values())
        assert abs(total - 1.0) < 1e-3

    def test_to_dict(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.mean_variance(tickers, er, cov)
        d = result.to_dict()
        for key in ["result_id", "weights", "sharpe_ratio", "volatility"]:
            assert key in d


class TestMinVariance:
    def setup_method(self):
        self.lab = OptimizationLab()

    def test_returns_result(self):
        tickers, _, cov = two_asset_setup()
        result = self.lab.min_variance(tickers, cov)
        assert result is not None

    def test_weights_sum_to_one(self):
        tickers, _, cov = two_asset_setup()
        result = self.lab.min_variance(tickers, cov)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3

    def test_min_variance_lower_vol_than_equal_weight(self):
        tickers, er, cov = three_asset_setup()
        mv = self.lab.min_variance(tickers, cov)
        mv_vol = mv.volatility
        n = len(tickers)
        w = [1.0 / n] * n
        Sigma = self.lab._build_cov_matrix(tickers, cov)
        ew_var = sum(Sigma[i][j] * w[i] * w[j] for i in range(n) for j in range(n))
        ew_vol = math.sqrt(max(ew_var, 0.0))
        assert mv_vol <= ew_vol + 0.01

    def test_optimization_type(self):
        tickers, _, cov = two_asset_setup()
        result = self.lab.min_variance(tickers, cov)
        assert result.optimization_type == OptimizationType.MIN_VARIANCE


class TestMaxSharpe:
    def setup_method(self):
        self.lab = OptimizationLab()

    def test_returns_result(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.max_sharpe(tickers, er, cov)
        assert result is not None

    def test_weights_sum_to_one(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.max_sharpe(tickers, er, cov)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3

    def test_optimization_type(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.max_sharpe(tickers, er, cov)
        assert result.optimization_type == OptimizationType.MAX_SHARPE

    def test_sharpe_positive_for_positive_expected_returns(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.max_sharpe(tickers, er, cov)
        assert result.sharpe_ratio >= 0.0

    def test_max_sharpe_better_than_equal_weight(self):
        tickers, er, cov = three_asset_setup()
        ms = self.lab.max_sharpe(tickers, er, cov)
        n = len(tickers)
        w = [1.0 / n] * n
        mu = [er.get(t, 0.0) for t in tickers]
        Sigma = self.lab._build_cov_matrix(tickers, cov)
        ew_ret = sum(mu[i] * w[i] for i in range(n))
        ew_var = sum(Sigma[i][j] * w[i] * w[j] for i in range(n) for j in range(n))
        ew_vol = math.sqrt(max(ew_var, 0.0))
        ew_sharpe = (ew_ret - 0.04) / ew_vol if ew_vol > 0 else 0.0
        assert ms.sharpe_ratio >= ew_sharpe - 0.1


class TestRiskParity:
    def setup_method(self):
        self.lab = OptimizationLab()

    def test_returns_result(self):
        tickers, _, cov = two_asset_setup()
        result = self.lab.risk_parity(tickers, cov)
        assert result is not None

    def test_weights_sum_to_one(self):
        tickers, _, cov = two_asset_setup()
        result = self.lab.risk_parity(tickers, cov)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3

    def test_risk_contributions_approximately_equal(self):
        tickers, _, cov = two_asset_setup()
        result = self.lab.risk_parity(tickers, cov)
        rcs = list(result.risk_contributions.values())
        assert abs(rcs[0] - rcs[1]) < 0.1

    def test_optimization_type(self):
        tickers, _, cov = two_asset_setup()
        result = self.lab.risk_parity(tickers, cov)
        assert result.optimization_type == OptimizationType.RISK_PARITY

    def test_three_asset_risk_parity(self):
        tickers, _, cov = three_asset_setup()
        result = self.lab.risk_parity(tickers, cov)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3


class TestEfficientFrontier:
    def setup_method(self):
        self.lab = OptimizationLab()

    def test_frontier_returns_list(self):
        tickers, er, cov = three_asset_setup()
        points = self.lab.compute_frontier(tickers, er, cov, n_points=10)
        assert isinstance(points, list)

    def test_frontier_non_empty(self):
        tickers, er, cov = three_asset_setup()
        points = self.lab.compute_frontier(tickers, er, cov, n_points=10)
        assert len(points) > 0

    def test_frontier_sorted_by_volatility(self):
        tickers, er, cov = three_asset_setup()
        points = self.lab.compute_frontier(tickers, er, cov, n_points=10)
        vols = [p.volatility for p in points]
        assert vols == sorted(vols)

    def test_frontier_point_has_weights(self):
        tickers, er, cov = two_asset_setup()
        points = self.lab.compute_frontier(tickers, er, cov, n_points=5)
        if points:
            for t in tickers:
                assert t in points[0].weights

    def test_frontier_point_to_dict(self):
        tickers, er, cov = two_asset_setup()
        points = self.lab.compute_frontier(tickers, er, cov, n_points=5)
        if points:
            d = points[0].to_dict()
            assert "expected_return" in d and "volatility" in d and "sharpe_ratio" in d


class TestFactorConstrainedOptimization:
    def setup_method(self):
        self.lab = OptimizationLab()

    def test_returns_result(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.factor_constrained_optimize(tickers, er, cov, {})
        assert result is not None

    def test_weights_sum_to_one(self):
        tickers, er, cov = two_asset_setup()
        result = self.lab.factor_constrained_optimize(tickers, er, cov, {})
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3


class TestBuildHelpers:
    def setup_method(self):
        self.lab = OptimizationLab()

    def test_build_cov_matrix(self):
        tickers = ["A", "B"]
        cov = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.03}}
        Sigma = self.lab._build_cov_matrix(tickers, cov)
        assert Sigma[0][0] == 0.04
        assert Sigma[0][1] == 0.01

    def test_build_cov_matrix_min_diagonal(self):
        tickers = ["A"]
        cov = {"A": {"A": 0.0}}
        Sigma = self.lab._build_cov_matrix(tickers, cov)
        assert Sigma[0][0] >= 1e-6

    def test_build_bounds_default(self):
        lb, ub = self.lab._build_bounds(["A", "B"], None)
        assert lb == [0.0, 0.0]
        assert ub == [1.0, 1.0]

    def test_build_bounds_with_constraints(self):
        constraints = [WeightConstraint(ticker="A", min_weight=0.2, max_weight=0.6)]
        lb, ub = self.lab._build_bounds(["A", "B"], constraints)
        assert lb[0] == 0.2
        assert ub[0] == 0.6

    def test_project_simplex(self):
        w = [0.3, 0.3, 0.3]
        lb = [0.0, 0.0, 0.0]
        ub = [1.0, 1.0, 1.0]
        projected = self.lab._project_simplex(w, lb, ub)
        assert abs(sum(projected) - 1.0) < 1e-6

    def test_compute_risk_contributions_sum_to_one(self):
        tickers, _, cov = two_asset_setup()
        w = [0.5, 0.5]
        Sigma = self.lab._build_cov_matrix(tickers, cov)
        rc = self.lab._compute_risk_contributions(w, Sigma)
        assert abs(sum(rc) - 1.0) < 1e-6

    def test_list_results_after_multiple(self):
        tickers, er, cov = two_asset_setup()
        self.lab.mean_variance(tickers, er, cov)
        self.lab.min_variance(tickers, cov)
        lst = self.lab.list_results()
        assert len(lst) == 2
