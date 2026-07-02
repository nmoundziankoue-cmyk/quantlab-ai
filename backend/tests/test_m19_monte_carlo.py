"""Tests for M19 MonteCarloEngine service."""

import math
import pytest
from services.m19_monte_carlo import (
    MonteCarloEngine,
    MCPath,
    MCResult,
    ConfidenceInterval,
)


def flat_returns(n=252, daily_ret=0.001) -> list:
    return [daily_ret] * n


def random_returns(n=252, seed=0) -> list:
    import random
    rng = random.Random(seed)
    return [rng.gauss(0.0005, 0.01) for _ in range(n)]


class TestMonteCarloEngineInit:
    def test_created(self):
        engine = MonteCarloEngine()
        assert engine is not None

    def test_starts_empty(self):
        engine = MonteCarloEngine()
        assert engine.list_results() == []

    def test_reset_clears_results(self):
        engine = MonteCarloEngine(seed=0)
        engine.run_gbm(0.0003, 0.01, num_paths=10, num_steps=10)
        engine.reset()
        assert engine.list_results() == []

    def test_get_nonexistent_returns_none(self):
        engine = MonteCarloEngine()
        assert engine.get_result("fake") is None

    def test_get_paths_nonexistent_returns_empty(self):
        engine = MonteCarloEngine()
        assert engine.get_paths("fake") == []

    def test_seed_determinism(self):
        e1 = MonteCarloEngine(seed=42)
        e2 = MonteCarloEngine(seed=42)
        r1 = e1.run_gbm(0.0003, 0.01, num_paths=50, num_steps=50)
        r2 = e2.run_gbm(0.0003, 0.01, num_paths=50, num_steps=50)
        assert r1.var_95 == r2.var_95


class TestBootstrapSimulation:
    def setup_method(self):
        self.engine = MonteCarloEngine(seed=1)

    def test_returns_result(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=100)
        assert result is not None

    def test_simulation_id_non_empty(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=50, num_steps=50)
        assert len(result.simulation_id) > 0

    def test_num_paths_correct(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=200, num_steps=50)
        assert result.num_paths == 200

    def test_num_steps_correct(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=50, num_steps=126)
        assert result.num_steps == 126

    def test_var_95_between_0_and_1(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=100)
        assert 0.0 <= result.var_95 <= 1.0

    def test_var_99_gte_var_95(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=200, num_steps=100)
        assert result.var_99 >= result.var_95 - 0.01

    def test_probability_of_profit_in_range(self):
        rets = flat_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=100)
        assert 0.0 <= result.probability_of_profit <= 1.0

    def test_probability_of_ruin_non_negative(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=100)
        assert result.probability_of_ruin >= 0.0

    def test_method_is_bootstrap(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=50, num_steps=50)
        assert result.method == "bootstrap"

    def test_cached(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=50, num_steps=50)
        cached = self.engine.get_result(result.simulation_id)
        assert cached is not None

    def test_positive_returns_high_profit_probability(self):
        rets = flat_returns(daily_ret=0.002)
        result = self.engine.run_bootstrap(rets, num_paths=200, num_steps=252)
        assert result.probability_of_profit > 0.5

    def test_block_size_gt_1(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=50, num_steps=50, block_size=5)
        assert result.num_paths == 50


class TestGBMSimulation:
    def setup_method(self):
        self.engine = MonteCarloEngine(seed=2)

    def test_returns_result(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=100, num_steps=100)
        assert result is not None

    def test_simulation_id_non_empty(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=50, num_steps=50)
        assert len(result.simulation_id) > 0

    def test_method_is_gbm(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=50, num_steps=50)
        assert result.method == "gbm"

    def test_num_paths_correct(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=300, num_steps=50)
        assert result.num_paths == 300

    def test_var_95_non_negative(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=100, num_steps=100)
        assert result.var_95 >= 0

    def test_expected_shortfall_gte_var(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=200, num_steps=100)
        assert result.expected_shortfall_95 >= result.var_95 - 0.05

    def test_negative_drift_reduces_profit_prob(self):
        pos = self.engine.run_gbm(0.001, 0.01, num_paths=200, num_steps=252)
        neg = self.engine.run_gbm(-0.001, 0.01, num_paths=200, num_steps=252)
        assert pos.probability_of_profit >= neg.probability_of_profit

    def test_higher_vol_increases_max_drawdown(self):
        lo = self.engine.run_gbm(0.0003, 0.005, num_paths=200, num_steps=252)
        hi = self.engine.run_gbm(0.0003, 0.030, num_paths=200, num_steps=252)
        assert hi.max_drawdown_p50 >= lo.max_drawdown_p50

    def test_initial_equity_stored(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=50, num_steps=50, initial_equity=200_000.0)
        assert result.initial_equity == 200_000.0


class TestMCPaths:
    def setup_method(self):
        self.engine = MonteCarloEngine(seed=3)

    def test_get_paths_returns_list(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=50, num_steps=50)
        paths = self.engine.get_paths(result.simulation_id)
        assert isinstance(paths, list)

    def test_get_paths_max_paths(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=200, num_steps=50)
        paths = self.engine.get_paths(result.simulation_id, max_paths=10)
        assert len(paths) <= 10

    def test_path_has_final_equity(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=20, num_steps=20)
        paths = self.engine.get_paths(result.simulation_id)
        if paths:
            assert paths[0].final_equity >= 0

    def test_path_has_total_return(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=20, num_steps=20)
        paths = self.engine.get_paths(result.simulation_id)
        if paths:
            assert isinstance(paths[0].total_return, float)

    def test_path_to_dict(self):
        result = self.engine.run_gbm(0.0003, 0.01, num_paths=20, num_steps=20)
        paths = self.engine.get_paths(result.simulation_id)
        if paths:
            d = paths[0].to_dict()
            assert "path_id" in d and "total_return" in d


class TestConfidenceIntervals:
    def setup_method(self):
        self.engine = MonteCarloEngine(seed=4)

    def test_confidence_intervals_exist(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=100)
        cis = self.engine.get_confidence_intervals(result.simulation_id)
        assert len(cis) > 0

    def test_three_confidence_intervals(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=100)
        cis = self.engine.get_confidence_intervals(result.simulation_id)
        assert len(cis) == 3

    def test_ci_has_metric(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=100)
        cis = self.engine.get_confidence_intervals(result.simulation_id)
        metrics = {ci["metric"] for ci in cis}
        assert "total_return" in metrics

    def test_ci_p50_between_p25_and_p75(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=200, num_steps=100)
        cis = self.engine.get_confidence_intervals(result.simulation_id)
        for ci in cis:
            assert ci["p25"] <= ci["p50"] + 1e-6
            assert ci["p50"] <= ci["p75"] + 1e-6

    def test_ci_empty_for_unknown(self):
        cis = self.engine.get_confidence_intervals("unknown")
        assert cis == []


class TestMCDistribution:
    def setup_method(self):
        self.engine = MonteCarloEngine(seed=5)

    def test_distribution_has_returns_key(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=50)
        dist = self.engine.get_distribution(result.simulation_id)
        assert "returns" in dist

    def test_distribution_has_final_equities(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=50)
        dist = self.engine.get_distribution(result.simulation_id)
        assert "final_equities" in dist

    def test_distribution_sorted(self):
        rets = random_returns()
        result = self.engine.run_bootstrap(rets, num_paths=100, num_steps=50)
        dist = self.engine.get_distribution(result.simulation_id)
        rets_d = dist["returns"]
        assert rets_d == sorted(rets_d)


class TestSensitivityAnalysis:
    def setup_method(self):
        self.engine = MonteCarloEngine(seed=6)

    def test_sensitivity_returns_rows(self):
        rets = random_returns()
        rows = self.engine.sensitivity_analysis(rets, [-0.001, 0.0, 0.001], [0.8, 1.0, 1.2], num_paths=50, num_steps=50)
        assert len(rows) == 9

    def test_sensitivity_row_has_var(self):
        rets = random_returns()
        rows = self.engine.sensitivity_analysis(rets, [0.0], [1.0], num_paths=50, num_steps=50)
        assert "var_95" in rows[0]

    def test_sensitivity_row_has_simulation_id(self):
        rets = random_returns()
        rows = self.engine.sensitivity_analysis(rets, [0.0], [1.0], num_paths=50, num_steps=50)
        assert "simulation_id" in rows[0]


class TestMCListResults:
    def test_list_after_multiple_runs(self):
        engine = MonteCarloEngine(seed=7)
        rets = random_returns()
        engine.run_bootstrap(rets, num_paths=50, num_steps=50)
        engine.run_gbm(0.0003, 0.01, num_paths=50, num_steps=50)
        lst = engine.list_results()
        assert len(lst) == 2

    def test_list_item_has_simulation_id(self):
        engine = MonteCarloEngine(seed=8)
        engine.run_gbm(0.0003, 0.01, num_paths=50, num_steps=50)
        lst = engine.list_results()
        assert "simulation_id" in lst[0]
