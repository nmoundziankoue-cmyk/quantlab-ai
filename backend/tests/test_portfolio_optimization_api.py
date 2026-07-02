"""M12 — API endpoint tests for /portfolio-optimization.

Uses FastAPI TestClient — no network calls.
"""
from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared synthetic 4-asset inputs
# ---------------------------------------------------------------------------

def _inputs(n: int = 4, seed: int = 42, T: int = 100):
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((n, n))
    cov = (A @ A.T) / n + 0.1 * np.eye(n)
    cov = (cov * 0.0001).tolist()
    mu = rng.uniform(0.0003, 0.0007, n).tolist()
    tickers = [f"T{i+1}" for i in range(n)]
    L = np.linalg.cholesky(np.array(cov))
    returns = (rng.standard_normal((T, n)) @ L.T + np.array(mu)).tolist()
    return tickers, mu, cov, returns


# ===========================================================================
# GET /portfolio-optimization/methods
# ===========================================================================

def test_get_methods_status():
    res = client.get("/portfolio-optimization/methods")
    assert res.status_code == 200


def test_get_methods_count():
    res = client.get("/portfolio-optimization/methods")
    data = res.json()
    assert len(data["methods"]) == 14


def test_get_methods_keys_present():
    res = client.get("/portfolio-optimization/methods")
    keys = {m["key"] for m in res.json()["methods"]}
    assert "max_sharpe" in keys
    assert "hrp" in keys
    assert "risk_parity" in keys


# ===========================================================================
# POST /portfolio-optimization/optimize
# ===========================================================================

def test_optimize_max_sharpe():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/optimize", json={
        "tickers": t, "mu": m, "cov": c, "method": "max_sharpe"
    })
    assert res.status_code == 200
    data = res.json()
    assert "weights" in data
    assert data["method"] == "max_sharpe"


def test_optimize_equal_weight():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/optimize", json={
        "tickers": t, "mu": m, "cov": c, "method": "equal_weight"
    })
    assert res.status_code == 200
    weights = res.json()["weights"]
    for w in weights.values():
        assert abs(w - 0.25) < 0.01


def test_optimize_unknown_method_422():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/optimize", json={
        "tickers": t, "mu": m, "cov": c, "method": "doesnt_exist"
    })
    assert res.status_code == 422


def test_optimize_dimension_mismatch_422():
    t, m, c, _ = _inputs(4)
    m_bad = m[:3]  # wrong length
    res = client.post("/portfolio-optimization/optimize", json={
        "tickers": t, "mu": m_bad, "cov": c, "method": "equal_weight"
    })
    assert res.status_code == 422


def test_optimize_hrp():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/optimize", json={
        "tickers": t, "mu": m, "cov": c, "method": "hrp"
    })
    assert res.status_code == 200
    assert res.json()["converged"]


def test_optimize_risk_parity():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/optimize", json={
        "tickers": t, "mu": m, "cov": c, "method": "risk_parity"
    })
    assert res.status_code == 200


def test_optimize_cvar_with_returns():
    t, m, c, returns = _inputs(T=200)
    res = client.post("/portfolio-optimization/optimize", json={
        "tickers": t, "mu": m, "cov": c, "method": "cvar_optimization",
        "returns_matrix": returns
    })
    assert res.status_code == 200


# ===========================================================================
# POST /portfolio-optimization/compare
# ===========================================================================

def test_compare_returns_list():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/compare", json={
        "tickers": t, "mu": m, "cov": c,
        "methods": ["equal_weight", "min_variance", "max_sharpe"]
    })
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_compare_no_methods_uses_defaults():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/compare", json={
        "tickers": t, "mu": m, "cov": c
    })
    assert res.status_code == 200
    assert len(res.json()) >= 5


# ===========================================================================
# POST /portfolio-optimization/frontier
# ===========================================================================

def test_frontier_returns_points():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/frontier", json={
        "tickers": t, "mu": m, "cov": c, "n_points": 20
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["points"]) == 20


def test_frontier_has_equal_weight_point():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/frontier", json={
        "tickers": t, "mu": m, "cov": c, "n_points": 20
    })
    assert res.status_code == 200
    ew = res.json()["equal_weight_point"]
    assert abs(sum(ew["weights"].values()) - 1.0) < 0.01


# ===========================================================================
# POST /portfolio-optimization/risk
# ===========================================================================

def test_risk_report_returns_200():
    rng = np.random.default_rng(0)
    returns = rng.normal(0.0005, 0.01, 300).tolist()
    nav = np.cumprod(1 + np.array(returns)).tolist()
    nav = [v * 100_000 for v in nav]
    res = client.post("/portfolio-optimization/risk", json={
        "returns": returns, "nav": nav
    })
    assert res.status_code == 200
    data = res.json()
    assert "sharpe_ratio" in data
    assert "drawdown" in data
    assert "var" in data


def test_risk_report_with_benchmark():
    rng = np.random.default_rng(0)
    returns = rng.normal(0.0005, 0.01, 300).tolist()
    bench = rng.normal(0.0003, 0.009, 300).tolist()
    nav = (np.cumprod(1 + np.array(returns)) * 100_000).tolist()
    res = client.post("/portfolio-optimization/risk", json={
        "returns": returns, "nav": nav, "benchmark_returns": bench
    })
    assert res.status_code == 200


# ===========================================================================
# POST /portfolio-optimization/attribution
# ===========================================================================

def test_attribution_runs():
    t, m, c, _ = _inputs(4)
    weights = {t[i]: 0.25 for i in range(4)}
    res = client.post("/portfolio-optimization/attribution", json={
        "tickers": t, "mu": m, "cov": c, "weights": weights
    })
    assert res.status_code == 200
    data = res.json()
    assert "pct_contributions" in data
    total = sum(data["pct_contributions"].values())
    assert abs(total - 1.0) < 0.01


# ===========================================================================
# POST /portfolio-optimization/stress
# ===========================================================================

def test_stress_all_scenarios():
    res = client.post("/portfolio-optimization/stress", json={
        "tickers": ["AAPL", "MSFT"],
        "weights": {"AAPL": 0.5, "MSFT": 0.5}
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) == 10   # 10 built-in scenarios


def test_stress_custom_scenario():
    res = client.post("/portfolio-optimization/stress", json={
        "tickers": ["AAPL", "MSFT"],
        "weights": {"AAPL": 0.5, "MSFT": 0.5},
        "custom_shocks": {"AAPL": -0.40, "MSFT": -0.25}
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) == 1
    assert data["scenarios"][0]["portfolio_impact_pct"] < 0


def test_stress_single_builtin_scenario():
    res = client.post("/portfolio-optimization/stress", json={
        "tickers": ["AAPL", "MSFT"],
        "weights": {"AAPL": 0.5, "MSFT": 0.5},
        "scenario_key": "2008_crisis"
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) == 1
    assert data["scenarios"][0]["scenario_name"] == "2008 Global Financial Crisis"


def test_stress_unknown_scenario_422():
    res = client.post("/portfolio-optimization/stress", json={
        "tickers": ["AAPL"],
        "weights": {"AAPL": 1.0},
        "scenario_key": "nonexistent_scenario"
    })
    assert res.status_code == 422


# ===========================================================================
# POST /portfolio-optimization/monte-carlo
# ===========================================================================

def test_monte_carlo_runs():
    weights = [0.5, 0.5]
    mu = [0.0005, 0.0004]
    cov = [[0.0001, 0.00002], [0.00002, 0.00008]]
    res = client.post("/portfolio-optimization/monte-carlo", json={
        "weights": weights, "mu": mu, "cov": cov,
        "n_simulations": 500, "simulation_days": 100
    })
    assert res.status_code == 200
    data = res.json()
    assert "expected_terminal" in data
    assert "probability_of_loss" in data


def test_monte_carlo_dimension_mismatch_422():
    res = client.post("/portfolio-optimization/monte-carlo", json={
        "weights": [0.5, 0.5], "mu": [0.001],  # mismatch
        "cov": [[0.0001, 0.00002], [0.00002, 0.00008]]
    })
    assert res.status_code == 422


# ===========================================================================
# POST /portfolio-optimization/covariance
# ===========================================================================

def test_covariance_endpoint_runs():
    rng = np.random.default_rng(0)
    returns = rng.normal(0.0005, 0.01, (200, 3)).tolist()
    res = client.post("/portfolio-optimization/covariance", json={
        "tickers": ["A", "B", "C"],
        "returns_matrix": returns
    })
    assert res.status_code == 200
    data = res.json()
    assert "condition_number" in data
    assert "covariance_matrix" in data


# ===========================================================================
# POST /portfolio-optimization/full-analysis
# ===========================================================================

def test_full_analysis_runs():
    t, m, c, returns = _inputs(4, T=200)
    res = client.post("/portfolio-optimization/full-analysis", json={
        "tickers": t, "mu": m, "cov": c,
        "method": "max_sharpe",
        "returns_matrix": returns,
        "run_stress": True,
        "run_mc": True,
        "mc_simulations": 300,
    })
    assert res.status_code == 200
    data = res.json()
    assert "optimization" in data
    assert "frontier" in data
    assert "stress_scenarios" in data
    assert "monte_carlo" in data


def test_full_analysis_optimization_has_weights():
    t, m, c, _ = _inputs()
    res = client.post("/portfolio-optimization/full-analysis", json={
        "tickers": t, "mu": m, "cov": c, "method": "equal_weight",
        "run_stress": False, "run_mc": False,
    })
    assert res.status_code == 200
    weights = res.json()["optimization"]["weights"]
    assert len(weights) == 4
