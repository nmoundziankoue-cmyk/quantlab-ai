"""API integration tests for M19 Quant Research Engine endpoints."""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

client = TestClient(app)
BASE = "/quant"


def make_bar(date="2024-01-01", price=100.0):
    return {"date": date, "open": price, "high": price * 1.01, "low": price * 0.99, "close": price, "volume": 10000}


def make_price_data(n=15, start=100.0):
    return {
        "AAPL": [make_bar(f"2024-01-{i+1:02d}", start + i * 0.5) for i in range(min(n, 28))]
    }


def make_signal(date="2024-01-01", ticker="AAPL", signal_type="LONG"):
    return {"date": date, "ticker": ticker, "signal_type": signal_type}


def run_backtest_and_get_id():
    resp = client.post(f"{BASE}/backtest/run", json={
        "strategy_name": "test",
        "signals": [make_signal()],
        "price_data": make_price_data(),
    })
    assert resp.status_code == 200
    return resp.json()["backtest_id"]


def run_gbm_and_get_id():
    resp = client.post(f"{BASE}/monte-carlo/gbm", json={
        "mean_daily_return": 0.0003,
        "daily_volatility": 0.01,
        "num_paths": 50,
        "num_steps": 50,
    })
    assert resp.status_code == 200
    return resp.json()["simulation_id"]


class TestResearchHealth:
    def test_health(self):
        resp = client.get(f"{BASE}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_capabilities(self):
        resp = client.get(f"{BASE}/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "backtest" in data

    def test_overview(self):
        resp = client.get(f"{BASE}/research/overview")
        assert resp.status_code == 200
        assert resp.json()["milestone"] == "M19"


class TestBacktestEndpoints:
    def test_run_backtest(self):
        resp = client.post(f"{BASE}/backtest/run", json={
            "strategy_name": "momentum",
            "signals": [make_signal()],
            "price_data": make_price_data(),
        })
        assert resp.status_code == 200
        assert "backtest_id" in resp.json()

    def test_run_returns_metrics(self):
        resp = client.post(f"{BASE}/backtest/run", json={
            "strategy_name": "s",
            "signals": [make_signal()],
            "price_data": make_price_data(),
        })
        assert "metrics" in resp.json()

    def test_list_backtests(self):
        run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/list")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_backtest_by_id(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}")
        assert resp.status_code == 200
        assert resp.json()["backtest_id"] == bid

    def test_get_backtest_not_found(self):
        resp = client.get(f"{BASE}/backtest/fake-id")
        assert resp.status_code == 404

    def test_get_equity_curve(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/equity-curve")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_trades(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/trades")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_drawdown(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/drawdown")
        assert resp.status_code == 200

    def test_get_monthly_returns(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/monthly-returns")
        assert resp.status_code == 200
        assert "monthly_returns" in resp.json()

    def test_get_metrics(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/metrics")
        assert resp.status_code == 200
        assert "sharpe_ratio" in resp.json()

    def test_compare_backtests(self):
        bid1 = run_backtest_and_get_id()
        bid2 = run_backtest_and_get_id()
        resp = client.post(f"{BASE}/backtest/compare", json={"backtest_ids": [bid1, bid2]})
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    def test_delete_backtest(self):
        bid = run_backtest_and_get_id()
        resp = client.delete(f"{BASE}/backtest/{bid}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_not_found(self):
        resp = client.delete(f"{BASE}/backtest/fake")
        assert resp.status_code == 404

    def test_get_statistics(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/statistics")
        assert resp.status_code == 200

    def test_get_winning_trades(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/winning-trades")
        assert resp.status_code == 200

    def test_get_losing_trades(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/losing-trades")
        assert resp.status_code == 200

    def test_get_tickers(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/tickers")
        assert resp.status_code == 200

    def test_get_peak_equity(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/peak-equity")
        assert resp.status_code == 200
        assert "peak_equity" in resp.json()

    def test_get_config(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/config")
        assert resp.status_code == 200
        assert "commission_rate" in resp.json()

    def test_return_series(self):
        bid = run_backtest_and_get_id()
        resp = client.get(f"{BASE}/backtest/{bid}/return-series")
        assert resp.status_code == 200


class TestExecutionEndpoints:
    def test_simulate(self):
        resp = client.post(f"{BASE}/execution/simulate", json={
            "order": {"ticker": "AAPL", "side": "BUY", "quantity": 100.0},
            "market_price": 150.0,
        })
        assert resp.status_code == 200
        assert "fill_id" in resp.json()

    def test_batch_simulate(self):
        resp = client.post(f"{BASE}/execution/batch", json={
            "orders": [{"ticker": "AAPL", "side": "BUY", "quantity": 100.0}],
            "prices": {"AAPL": 150.0},
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_fill_model(self):
        resp = client.post(f"{BASE}/execution/fill-model", json={"model_name": "TestModel"})
        assert resp.status_code == 200
        assert resp.json()["model_name"] == "TestModel"

    def test_slippage_report(self):
        client.post(f"{BASE}/execution/simulate", json={
            "order": {"ticker": "AAPL", "side": "BUY", "quantity": 100.0},
            "market_price": 150.0,
        })
        resp = client.get(f"{BASE}/execution/slippage-report")
        assert resp.status_code == 200

    def test_fill_history(self):
        resp = client.get(f"{BASE}/execution/fills")
        assert resp.status_code == 200

    def test_order_history(self):
        resp = client.get(f"{BASE}/execution/orders")
        assert resp.status_code == 200

    def test_implementation_shortfall(self):
        resp = client.post(f"{BASE}/execution/implementation-shortfall", json={
            "order": {"ticker": "AAPL", "side": "BUY", "quantity": 100.0},
            "decision_price": 100.0,
            "fill_price": 101.0,
            "fill_qty": 100.0,
        })
        assert resp.status_code == 200

    def test_execution_stats(self):
        resp = client.get(f"{BASE}/execution/stats")
        assert resp.status_code == 200

    def test_list_slippage_models(self):
        resp = client.get(f"{BASE}/execution/models")
        assert resp.status_code == 200
        assert "FIXED_BPS" in resp.json()

    def test_list_order_types(self):
        resp = client.get(f"{BASE}/execution/order-types")
        assert resp.status_code == 200
        assert "MARKET" in resp.json()

    def test_impact_model_info(self):
        resp = client.get(f"{BASE}/execution/impact-model")
        assert resp.status_code == 200

    def test_reset_execution_simulator(self):
        resp = client.post(f"{BASE}/execution/reset")
        assert resp.status_code == 200
        assert resp.json()["reset"] is True


class TestMonteCarloEndpoints:
    def test_bootstrap(self):
        resp = client.post(f"{BASE}/monte-carlo/bootstrap", json={
            "daily_returns": [0.001] * 50,
            "num_paths": 50,
            "num_steps": 50,
        })
        assert resp.status_code == 200
        assert "simulation_id" in resp.json()

    def test_gbm(self):
        resp = client.post(f"{BASE}/monte-carlo/gbm", json={
            "mean_daily_return": 0.0003,
            "daily_volatility": 0.01,
            "num_paths": 50,
            "num_steps": 50,
        })
        assert resp.status_code == 200

    def test_get_result(self):
        sid = run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/{sid}")
        assert resp.status_code == 200

    def test_get_result_not_found(self):
        resp = client.get(f"{BASE}/monte-carlo/fake-id")
        assert resp.status_code == 404

    def test_confidence_intervals(self):
        sid = run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/{sid}/confidence-intervals")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_distribution(self):
        sid = run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/{sid}/distribution")
        assert resp.status_code == 200
        assert "returns" in resp.json()

    def test_paths(self):
        sid = run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/{sid}/paths?max_paths=10")
        assert resp.status_code == 200

    def test_list_mc(self):
        run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/list/all")
        assert resp.status_code == 200

    def test_mc_var(self):
        sid = run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/{sid}/var")
        assert resp.status_code == 200
        assert "var_95" in resp.json()

    def test_mc_drawdown_dist(self):
        sid = run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/{sid}/drawdown-distribution")
        assert resp.status_code == 200

    def test_mc_summary(self):
        sid = run_gbm_and_get_id()
        resp = client.get(f"{BASE}/monte-carlo/{sid}/summary")
        assert resp.status_code == 200

    def test_params_from_returns(self):
        resp = client.post(f"{BASE}/monte-carlo/params-from-returns", json={
            "daily_returns": [0.001, -0.002, 0.003] * 50
        })
        assert resp.status_code == 200
        assert "mean_daily_return" in resp.json()

    def test_sensitivity(self):
        resp = client.post(f"{BASE}/monte-carlo/sensitivity", json={
            "daily_returns": [0.001] * 30,
            "drift_shocks": [0.0],
            "vol_shocks": [1.0],
            "num_paths": 20,
            "num_steps": 20,
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestFactorModelEndpoints:
    def _add_returns(self):
        client.post(f"{BASE}/factors/returns", json={
            "factor_returns": [
                {"date": f"2024-01-{i+1:02d}", "factor": "MARKET", "return_value": 0.001 * i}
                for i in range(30)
            ]
        })

    def test_add_factor_returns(self):
        resp = client.post(f"{BASE}/factors/returns", json={
            "factor_returns": [
                {"date": "2024-01-01", "factor": "MARKET", "return_value": 0.01}
            ]
        })
        assert resp.status_code == 200

    def test_list_factor_types(self):
        resp = client.get(f"{BASE}/factors/types")
        assert resp.status_code == 200
        assert "MARKET" in resp.json()

    def test_list_tickers(self):
        resp = client.get(f"{BASE}/factors/tickers")
        assert resp.status_code == 200

    def test_factor_summary(self):
        self._add_returns()
        resp = client.get(f"{BASE}/factors/summary")
        assert resp.status_code == 200

    def test_factor_dates(self):
        self._add_returns()
        resp = client.get(f"{BASE}/factors/dates")
        assert resp.status_code == 200

    def test_reset_factor_engine(self):
        resp = client.post(f"{BASE}/factors/reset")
        assert resp.status_code == 200

    def test_factor_series(self):
        self._add_returns()
        resp = client.get(f"{BASE}/factors/series/MARKET")
        assert resp.status_code == 200

    def test_portfolio_beta(self):
        resp = client.post(f"{BASE}/factors/portfolio-beta", json={
            "weights": {"AAPL": 0.5, "MSFT": 0.5}, "factor": "MARKET"
        })
        assert resp.status_code == 200


class TestOptimizationEndpoints:
    def _payload(self, n_tickers=2):
        tickers = ["AAPL", "MSFT", "JPM"][:n_tickers]
        er = {"AAPL": 0.12, "MSFT": 0.10, "JPM": 0.08}
        cov = {t: {t2: 0.04 if t == t2 else 0.01 for t2 in tickers} for t in tickers}
        return tickers, {k: v for k, v in er.items() if k in tickers}, cov

    def test_mean_variance(self):
        t, er, cov = self._payload()
        resp = client.post(f"{BASE}/optimize/mean-variance", json={
            "tickers": t, "expected_returns": er, "covariance_matrix": cov
        })
        assert resp.status_code == 200
        assert "weights" in resp.json()

    def test_min_variance(self):
        t, _, cov = self._payload()
        resp = client.post(f"{BASE}/optimize/min-variance", json={
            "tickers": t, "covariance_matrix": cov
        })
        assert resp.status_code == 200

    def test_max_sharpe(self):
        t, er, cov = self._payload()
        resp = client.post(f"{BASE}/optimize/max-sharpe", json={
            "tickers": t, "expected_returns": er, "covariance_matrix": cov
        })
        assert resp.status_code == 200
        assert "sharpe_ratio" in resp.json()

    def test_risk_parity(self):
        t, _, cov = self._payload()
        resp = client.post(f"{BASE}/optimize/risk-parity", json={
            "tickers": t, "covariance_matrix": cov
        })
        assert resp.status_code == 200

    def test_frontier(self):
        t, er, cov = self._payload(3)
        resp = client.post(f"{BASE}/optimize/frontier", json={
            "tickers": t, "expected_returns": er, "covariance_matrix": cov, "n_points": 5
        })
        assert resp.status_code == 200
        assert "points" in resp.json()

    def test_get_optimization_result(self):
        t, er, cov = self._payload()
        run = client.post(f"{BASE}/optimize/mean-variance", json={
            "tickers": t, "expected_returns": er, "covariance_matrix": cov
        })
        rid = run.json()["result_id"]
        resp = client.get(f"{BASE}/optimize/{rid}")
        assert resp.status_code == 200

    def test_get_result_not_found(self):
        resp = client.get(f"{BASE}/optimize/fake-id")
        assert resp.status_code == 404

    def test_list_results(self):
        t, er, cov = self._payload()
        client.post(f"{BASE}/optimize/mean-variance", json={
            "tickers": t, "expected_returns": er, "covariance_matrix": cov
        })
        resp = client.get(f"{BASE}/optimize/list/all")
        assert resp.status_code == 200

    def test_get_weights(self):
        t, er, cov = self._payload()
        run = client.post(f"{BASE}/optimize/mean-variance", json={
            "tickers": t, "expected_returns": er, "covariance_matrix": cov
        })
        rid = run.json()["result_id"]
        resp = client.get(f"{BASE}/optimize/{rid}/weights")
        assert resp.status_code == 200

    def test_get_risk_contributions(self):
        t, er, cov = self._payload()
        run = client.post(f"{BASE}/optimize/mean-variance", json={
            "tickers": t, "expected_returns": er, "covariance_matrix": cov
        })
        rid = run.json()["result_id"]
        resp = client.get(f"{BASE}/optimize/{rid}/risk-contributions")
        assert resp.status_code == 200

    def test_reset_optimization(self):
        resp = client.post(f"{BASE}/optimize/reset")
        assert resp.status_code == 200

    def test_list_optimization_types(self):
        resp = client.get(f"{BASE}/optimize/types/all")
        assert resp.status_code == 200
        assert "MEAN_VARIANCE" in resp.json()

    def test_rebalance(self):
        resp = client.post(f"{BASE}/optimize/rebalance", json={
            "current_weights": {"AAPL": 0.6, "MSFT": 0.4},
            "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
            "portfolio_value": 100_000.0,
        })
        assert resp.status_code == 200
        assert "trades" in resp.json()

    def test_portfolio_risk(self):
        resp = client.post(f"{BASE}/optimize/portfolio-risk", json={
            "weights": {"AAPL": 0.5, "MSFT": 0.5},
            "covariance_matrix": {"AAPL": {"AAPL": 0.04, "MSFT": 0.01}, "MSFT": {"AAPL": 0.01, "MSFT": 0.03}},
        })
        assert resp.status_code == 200
        assert "portfolio_volatility" in resp.json()

    def test_weight_validation_valid(self):
        resp = client.post(f"{BASE}/optimize/weight-validation", json={
            "weights": {"AAPL": 0.6, "MSFT": 0.4}
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is True


class TestStrategyAnalysisEndpoints:
    def test_rolling_sharpe(self):
        rets = [0.001 * i for i in range(100)]
        resp = client.post(f"{BASE}/strategy/rolling-sharpe", json={
            "daily_returns": rets, "window": 20
        })
        assert resp.status_code == 200

    def test_rolling_drawdown(self):
        equity = [100_000 + 500 * i for i in range(20)]
        resp = client.post(f"{BASE}/strategy/rolling-drawdown", json={"equity_values": equity})
        assert resp.status_code == 200
        assert "max_drawdown" in resp.json()

    def test_returns_stats(self):
        resp = client.post(f"{BASE}/strategy/returns-stats", json={"daily_returns": [0.001, -0.002, 0.003] * 20})
        assert resp.status_code == 200
        assert "mean" in resp.json()

    def test_correlation_matrix(self):
        resp = client.post(f"{BASE}/strategy/correlation-matrix", json={
            "returns": {"A": [0.01, 0.02, -0.01] * 5, "B": [0.02, 0.01, -0.02] * 5}
        })
        assert resp.status_code == 200

    def test_covariance_from_returns(self):
        resp = client.post(f"{BASE}/strategy/covariance-from-returns", json={
            "returns": {"A": [0.01, 0.02, -0.01] * 10, "B": [0.02, 0.01, -0.02] * 10}
        })
        assert resp.status_code == 200
        assert "covariance_matrix" in resp.json()

    def test_reset_all(self):
        resp = client.post(f"{BASE}/research/reset-all")
        assert resp.status_code == 200
        assert resp.json()["engines"] == 6
