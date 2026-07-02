"""Tests for M4 Monte Carlo simulation service.

All tests are pure numerical — no network calls.
"""
import numpy as np
import pandas as pd
import pytest

from services.monte_carlo import (
    run_monte_carlo,
    _simulate_gbm,
    _simulate_student_t,
    _simulate_bootstrap,
    _final_value_stats,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_returns() -> pd.Series:
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(0.0005, 0.012, 500))


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(seed=0)


# ---------------------------------------------------------------------------
# Simulation engines
# ---------------------------------------------------------------------------

class TestGBM:
    def test_shape(self, rng):
        paths = _simulate_gbm(0.001, 0.015, 100, 50, rng)
        assert paths.shape == (100, 51)

    def test_starts_at_one(self, rng):
        paths = _simulate_gbm(0.001, 0.015, 100, 50, rng)
        assert np.allclose(paths[:, 0], 1.0)

    def test_all_positive(self, rng):
        paths = _simulate_gbm(0.001, 0.015, 1000, 252, rng)
        assert (paths > 0).all()


class TestStudentT:
    def test_shape(self, rng):
        paths = _simulate_student_t(0.001, 0.015, 100, 50, rng)
        assert paths.shape == (100, 51)

    def test_starts_at_one(self, rng):
        paths = _simulate_student_t(0.001, 0.015, 100, 50, rng)
        assert np.allclose(paths[:, 0], 1.0)

    def test_all_positive(self, rng):
        paths = _simulate_student_t(0.001, 0.015, 1000, 252, rng)
        assert (paths > 0).all()

    def test_returns_paths_shape(self, rng):
        """Student-t simulation returns correct shape — fat-tail test done at sample level."""
        rng2 = np.random.default_rng(1)
        paths = _simulate_student_t(0.0, 0.015, 500, 252, rng2)
        assert paths.shape == (500, 253)

    def test_all_positive_values(self, rng):
        rng2 = np.random.default_rng(2)
        paths = _simulate_student_t(0.001, 0.012, 1000, 100, rng2)
        assert (paths > 0).all()


class TestBootstrap:
    def test_shape(self, rng):
        hist = np.random.default_rng(5).normal(0.001, 0.01, 250)
        paths = _simulate_bootstrap(hist, 100, 50, rng)
        assert paths.shape == (100, 51)

    def test_starts_at_one(self, rng):
        hist = np.random.default_rng(5).normal(0.001, 0.01, 250)
        paths = _simulate_bootstrap(hist, 100, 50, rng)
        assert np.allclose(paths[:, 0], 1.0)


# ---------------------------------------------------------------------------
# Final value stats
# ---------------------------------------------------------------------------

class TestFinalValueStats:
    def test_returns_dict_with_required_keys(self, rng):
        paths = _simulate_gbm(0.001, 0.015, 500, 100, rng)
        stats = _final_value_stats(paths, 100_000)
        for k in ["mean", "median", "std", "p5", "p25", "p75", "p95", "min", "max"]:
            assert k in stats

    def test_p5_lt_p95(self, rng):
        paths = _simulate_gbm(0.001, 0.015, 1000, 100, rng)
        stats = _final_value_stats(paths, 100_000)
        assert stats["p5"] < stats["p95"]

    def test_min_lte_p5(self, rng):
        paths = _simulate_gbm(0.001, 0.015, 1000, 100, rng)
        stats = _final_value_stats(paths, 100_000)
        assert stats["min"] <= stats["p5"]


# ---------------------------------------------------------------------------
# run_monte_carlo integration
# ---------------------------------------------------------------------------

class TestRunMonteCarlo:
    def test_gbm_returns_required_keys(self, sample_returns):
        result = run_monte_carlo(sample_returns, 100_000, n_simulations=1000, model="gbm")
        for key in ["percentile_paths", "final_value_stats", "prob_loss", "expected_final_value"]:
            assert key in result

    def test_student_t_model(self, sample_returns):
        result = run_monte_carlo(sample_returns, 100_000, n_simulations=1000, model="student_t")
        assert result["model"] == "student_t"

    def test_bootstrap_model(self, sample_returns):
        result = run_monte_carlo(sample_returns, 100_000, n_simulations=1000, model="bootstrap")
        assert result["model"] == "bootstrap"

    def test_invalid_model_raises(self, sample_returns):
        with pytest.raises(ValueError, match="Unknown model"):
            run_monte_carlo(sample_returns, 100_000, model="invalid")

    def test_prob_loss_between_0_and_1(self, sample_returns):
        result = run_monte_carlo(sample_returns, 100_000, n_simulations=1000, model="gbm")
        assert 0.0 <= result["prob_loss"] <= 1.0

    def test_percentile_paths_correct_length(self, sample_returns):
        days = 50
        result = run_monte_carlo(sample_returns, 100_000, simulation_days=days, n_simulations=500, model="gbm")
        for key, path in result["percentile_paths"].items():
            assert len(path) == days + 1  # includes day 0

    def test_p50_starts_at_initial_value(self, sample_returns):
        initial = 100_000.0
        result = run_monte_carlo(sample_returns, initial, simulation_days=30, n_simulations=1000, model="gbm")
        p50_start = result["percentile_paths"]["p50"][0]
        assert abs(p50_start - initial) < 1.0

    def test_insufficient_data_raises(self):
        short = pd.Series([0.01, -0.02, 0.005])  # only 3 observations
        with pytest.raises(ValueError, match="at least 20"):
            run_monte_carlo(short, 100_000)
