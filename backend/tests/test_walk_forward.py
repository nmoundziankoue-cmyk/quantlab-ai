"""Tests for M9 Phase 5 — walk-forward, parameter sweep, Kelly criterion."""
import pytest
from services.walk_forward import (
    walk_forward_test, parameter_sweep, rolling_optimization,
    kelly_criterion, compute_metrics, _sharpe, _max_drawdown, _cagr,
)


def make_prices(n=200, start=100.0, drift=0.001):
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + drift))
    return prices


def sma_crossover(prices, params):
    fast = int(params.get("fast", 10))
    slow = int(params.get("slow", 30))
    if len(prices) < slow + 1:
        return []
    returns = []
    position = 0
    for i in range(slow, len(prices)):
        sma_f = sum(prices[i - fast:i]) / fast
        sma_s = sum(prices[i - slow:i]) / slow
        signal = 1 if sma_f > sma_s else -1
        if i > slow:
            daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
            returns.append(position * daily_return)
        position = signal
    return returns


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def test_empty(self):
        m = compute_metrics([])
        assert m["n"] == 0
        assert m["sharpe"] == 0.0

    def test_positive_returns(self):
        import random
        random.seed(42)
        returns = [0.01 + random.gauss(0, 0.005) for _ in range(252)]
        m = compute_metrics(returns)
        assert m["cagr"] > 0

    def test_zero_drawdown_on_constant_growth(self):
        returns = [0.001] * 100
        m = compute_metrics(returns)
        assert m["max_drawdown"] == 0.0

    def test_negative_returns(self):
        returns = [-0.01] * 50
        m = compute_metrics(returns)
        assert m["total_return"] < 0

    def test_max_drawdown_monotone_decline(self):
        returns = [-0.02] * 50
        m = compute_metrics(returns)
        assert m["max_drawdown"] > 0


# ---------------------------------------------------------------------------
# Walk-forward test
# ---------------------------------------------------------------------------

class TestWalkForward:
    def test_returns_windows(self):
        prices = make_prices(200)
        result = walk_forward_test(prices, sma_crossover, {"fast": 5, "slow": 20}, 80, 20)
        assert len(result.windows) > 0

    def test_aggregate_has_n_windows(self):
        prices = make_prices(200)
        result = walk_forward_test(prices, sma_crossover, {"fast": 5, "slow": 20}, 80, 20)
        assert result.aggregate["n_windows"] == len(result.windows)

    def test_window_structure(self):
        prices = make_prices(200)
        result = walk_forward_test(prices, sma_crossover, {"fast": 5, "slow": 20}, 80, 20)
        w = result.windows[0]
        assert "in_sample" in w
        assert "out_of_sample" in w
        assert w["is_end"] == w["oos_start"]

    def test_consistency_ratio_range(self):
        prices = make_prices(300)
        result = walk_forward_test(prices, sma_crossover, {"fast": 5, "slow": 20}, 100, 25)
        assert 0.0 <= result.aggregate["consistency"] <= 1.0

    def test_too_short_prices(self):
        result = walk_forward_test([100, 101], sma_crossover, {"fast": 5, "slow": 10}, 50, 20)
        assert result.windows == []

    def test_oos_combined_metrics(self):
        prices = make_prices(300)
        result = walk_forward_test(prices, sma_crossover, {"fast": 5, "slow": 20}, 100, 30)
        oos = result.aggregate["oos_combined"]
        assert "sharpe" in oos
        assert "max_drawdown" in oos


# ---------------------------------------------------------------------------
# Parameter sweep
# ---------------------------------------------------------------------------

class TestParameterSweep:
    def test_returns_best_params(self):
        prices = make_prices(150)
        grid = {"fast": [5, 10], "slow": [20, 30]}
        result = parameter_sweep(prices, sma_crossover, grid, metric="sharpe")
        assert result.best_params in [{"fast": f, "slow": s} for f in [5, 10] for s in [20, 30]]

    def test_all_results_count(self):
        prices = make_prices(150)
        grid = {"fast": [5, 10], "slow": [20, 30]}
        result = parameter_sweep(prices, sma_crossover, grid)
        assert len(result.all_results) == 4

    def test_sorted_descending(self):
        prices = make_prices(150)
        grid = {"fast": [5, 10, 15], "slow": [20, 30, 50]}
        result = parameter_sweep(prices, sma_crossover, grid, metric="sharpe")
        metrics = [r["metrics"]["sharpe"] for r in result.all_results]
        assert metrics == sorted(metrics, reverse=True)

    def test_single_param_combo(self):
        prices = make_prices(100)
        grid = {"fast": [5], "slow": [20]}
        result = parameter_sweep(prices, sma_crossover, grid)
        assert len(result.all_results) == 1


# ---------------------------------------------------------------------------
# Kelly Criterion
# ---------------------------------------------------------------------------

class TestKellyCriterion:
    def test_positive_edge(self):
        k = kelly_criterion(0.6, 0.10, 0.05)
        assert k["full_kelly"] > 0

    def test_no_edge_zero_kelly(self):
        k = kelly_criterion(0.5, 0.10, 0.10)
        assert k["full_kelly"] == pytest.approx(0.0)

    def test_half_kelly_is_half(self):
        k = kelly_criterion(0.6, 0.10, 0.05)
        assert k["half_kelly"] == pytest.approx(k["full_kelly"] * 0.5)

    def test_quarter_kelly(self):
        k = kelly_criterion(0.6, 0.10, 0.05)
        assert k["quarter_kelly"] == pytest.approx(k["full_kelly"] * 0.25)

    def test_extreme_win_prob_zero(self):
        k = kelly_criterion(0.0, 0.10, 0.05)
        assert k["full_kelly"] == 0.0

    def test_win_prob_one_max_bet(self):
        k = kelly_criterion(1.0, 0.10, 0.05)
        assert k["full_kelly"] == pytest.approx(0.0)  # division-guard

    def test_log_growth_nonnegative_positive_edge(self):
        k = kelly_criterion(0.6, 0.15, 0.05)
        assert k["expected_log_growth"] >= 0

    def test_invalid_loss_return(self):
        k = kelly_criterion(0.6, 0.10, 0.0)
        assert k["full_kelly"] == 0.0
