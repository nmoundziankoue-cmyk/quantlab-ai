"""M20 API integration tests — verifies all router endpoints."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
BASE = "/quant/m20"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bar(i: int = 0, price: float = 100.0) -> Dict[str, Any]:
    return {
        "date": f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}",
        "open": price,
        "high": price * 1.005,
        "low": price * 0.995,
        "close": price,
        "volume": 1000.0,
    }


def _rising_bars(n: int = 300, start: float = 100.0, drift: float = 0.002) -> List[Dict[str, Any]]:
    return [_bar(i, start * (1 + drift) ** i) for i in range(n)]


def _daily_returns(n: int = 300, value: float = 0.001) -> List[float]:
    return [value * (1 + 0.1 * (i % 5)) for i in range(n)]


def _returns_dict(n: int = 100, value: float = 0.001) -> Dict[str, float]:
    return {f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}": value * (1 + 0.1 * (i % 5)) for i in range(n)}


# ---------------------------------------------------------------------------
# Regime endpoints
# ---------------------------------------------------------------------------

class TestRegimeDetect:
    def test_detect_success(self):
        body = {"ticker": "AAPL", "bars": _rising_bars(300)}
        resp = client.post(f"{BASE}/regime/detect", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "current_regime" in data
        assert "ticker" in data

    def test_detect_missing_bars_422(self):
        resp = client.post(f"{BASE}/regime/detect", json={"ticker": "AAPL", "bars": [_bar(0)]})
        assert resp.status_code == 422

    def test_detect_from_returns_success(self):
        body = {"ticker": "SYN", "daily_returns": _daily_returns()}
        resp = client.post(f"{BASE}/regime/detect-from-returns", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "current_regime" in data

    def test_get_result_after_detect(self):
        client.post(f"{BASE}/regime/detect", json={"ticker": "APPL2", "bars": _rising_bars(300)})
        resp = client.get(f"{BASE}/regime/result/APPL2")
        assert resp.status_code == 200

    def test_get_result_404(self):
        resp = client.get(f"{BASE}/regime/result/NOEXIST_EVER")
        assert resp.status_code == 404

    def test_get_current_after_detect(self):
        client.post(f"{BASE}/regime/detect", json={"ticker": "MSFT2", "bars": _rising_bars(300)})
        resp = client.get(f"{BASE}/regime/current/MSFT2")
        assert resp.status_code == 200
        assert "regime" in resp.json()

    def test_get_current_404(self):
        resp = client.get(f"{BASE}/regime/current/TOTALLY_MISSING")
        assert resp.status_code == 404

    def test_get_history_after_detect(self):
        client.post(f"{BASE}/regime/detect", json={"ticker": "HIST_TICK", "bars": _rising_bars(300)})
        resp = client.get(f"{BASE}/regime/history/HIST_TICK")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) > 0

    def test_get_history_empty(self):
        resp = client.get(f"{BASE}/regime/history/EMPTY_TICK")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tickers(self):
        client.post(f"{BASE}/regime/detect", json={"ticker": "LIST_TEST", "bars": _rising_bars(300)})
        resp = client.get(f"{BASE}/regime/tickers")
        assert resp.status_code == 200
        tickers = resp.json()
        assert "LIST_TEST" in tickers

    def test_summary(self):
        client.post(f"{BASE}/regime/detect", json={"ticker": "SUM_TICK", "bars": _rising_bars(300)})
        resp = client.get(f"{BASE}/regime/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "dominant_regime" in data

    def test_compare(self):
        client.post(f"{BASE}/regime/detect", json={"ticker": "CMP1", "bars": _rising_bars(300)})
        resp = client.post(f"{BASE}/regime/compare", json={"tickers": ["CMP1", "MISSING"]})
        assert resp.status_code == 200
        data = resp.json()
        assert "CMP1" in data

    def test_reset(self):
        resp = client.delete(f"{BASE}/regime/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Correlation endpoints
# ---------------------------------------------------------------------------

class TestCorrelationEndpoints:
    def _seed_two_tickers(self, ta: str = "AA", tb: str = "BB"):
        client.post(f"{BASE}/correlation/add-returns", json={"ticker": ta, "returns": _returns_dict(100)})
        client.post(f"{BASE}/correlation/add-returns", json={"ticker": tb, "returns": _returns_dict(100)})

    def test_add_returns(self):
        resp = client.post(f"{BASE}/correlation/add-returns", json={"ticker": "ADD_TEST", "returns": _returns_dict(50)})
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "ADD_TEST"

    def test_add_returns_batch(self):
        body = {"entries": [
            {"ticker": "BA1", "returns": _returns_dict(50)},
            {"ticker": "BA2", "returns": _returns_dict(50)},
        ]}
        resp = client.post(f"{BASE}/correlation/add-returns-batch", json=body)
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    def test_correlation_matrix_success(self):
        self._seed_two_tickers("CM1", "CM2")
        resp = client.post(f"{BASE}/correlation/matrix", json={"tickers": ["CM1", "CM2"]})
        assert resp.status_code == 200
        data = resp.json()
        assert "values" in data
        assert data["values"][0][0] == pytest.approx(1.0)

    def test_correlation_matrix_unknown_ticker(self):
        resp = client.post(f"{BASE}/correlation/matrix", json={"tickers": ["NOENT1", "NOENT2"]})
        assert resp.status_code == 422

    def test_get_correlation_matrix_by_id(self):
        self._seed_two_tickers("IDX1", "IDX2")
        post_resp = client.post(f"{BASE}/correlation/matrix", json={"tickers": ["IDX1", "IDX2"]})
        matrix_id = post_resp.json()["matrix_id"]
        resp = client.get(f"{BASE}/correlation/matrix/{matrix_id}")
        assert resp.status_code == 200
        assert resp.json()["matrix_id"] == matrix_id

    def test_get_correlation_matrix_404(self):
        resp = client.get(f"{BASE}/correlation/matrix/no-such-id")
        assert resp.status_code == 404

    def test_rolling_correlation_success(self):
        self._seed_two_tickers("RC1", "RC2")
        resp = client.post(f"{BASE}/correlation/rolling", json={"ticker_a": "RC1", "ticker_b": "RC2", "window": 20})
        assert resp.status_code == 200
        data = resp.json()
        assert "correlations" in data

    def test_rolling_correlation_unknown_ticker(self):
        resp = client.post(f"{BASE}/correlation/rolling", json={"ticker_a": "NO1", "ticker_b": "NO2", "window": 10})
        assert resp.status_code == 422

    def test_clusters_success(self):
        self._seed_two_tickers("CL1", "CL2")
        resp = client.post(f"{BASE}/correlation/clusters", json={"tickers": ["CL1", "CL2"], "threshold": 0.5})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_pairwise_correlation(self):
        self._seed_two_tickers("PW1", "PW2")
        resp = client.post(f"{BASE}/correlation/pairwise", json={"ticker_a": "PW1", "ticker_b": "PW2"})
        assert resp.status_code == 200
        assert "correlation" in resp.json()

    def test_most_correlated(self):
        self._seed_two_tickers("MC1", "MC2")
        resp = client.post(f"{BASE}/correlation/most-correlated", json={"tickers": ["MC1", "MC2"]})
        assert resp.status_code == 200
        assert "ticker_a" in resp.json()

    def test_least_correlated(self):
        self._seed_two_tickers("LC1", "LC2")
        resp = client.post(f"{BASE}/correlation/least-correlated", json={"tickers": ["LC1", "LC2"]})
        assert resp.status_code == 200

    def test_list_tickers(self):
        client.post(f"{BASE}/correlation/add-returns", json={"ticker": "LTCK", "returns": _returns_dict(30)})
        resp = client.get(f"{BASE}/correlation/tickers")
        assert resp.status_code == 200
        assert "LTCK" in resp.json()

    def test_correlation_reset(self):
        resp = client.delete(f"{BASE}/correlation/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Covariance endpoints
# ---------------------------------------------------------------------------

class TestCovarianceEndpoints:
    def _seed_two_tickers(self):
        client.post(f"{BASE}/correlation/add-returns", json={"ticker": "CVA", "returns": _returns_dict(100)})
        client.post(f"{BASE}/correlation/add-returns", json={"ticker": "CVB", "returns": _returns_dict(100)})

    def test_covariance_matrix_success(self):
        self._seed_two_tickers()
        resp = client.post(f"{BASE}/covariance/matrix", json={"tickers": ["CVA", "CVB"], "annualize": True})
        assert resp.status_code == 200
        data = resp.json()
        assert "values" in data
        assert data["annualized"] is True

    def test_covariance_matrix_no_annualize(self):
        self._seed_two_tickers()
        resp = client.post(f"{BASE}/covariance/matrix", json={"tickers": ["CVA", "CVB"], "annualize": False})
        assert resp.status_code == 200
        assert resp.json()["annualized"] is False

    def test_covariance_matrix_unknown_raises(self):
        resp = client.post(f"{BASE}/covariance/matrix", json={"tickers": ["NO_A", "NO_B"]})
        assert resp.status_code == 422

    def test_get_covariance_matrix_by_id(self):
        self._seed_two_tickers()
        post_resp = client.post(f"{BASE}/covariance/matrix", json={"tickers": ["CVA", "CVB"]})
        mid = post_resp.json()["matrix_id"]
        resp = client.get(f"{BASE}/covariance/matrix/{mid}")
        assert resp.status_code == 200

    def test_get_covariance_matrix_404(self):
        resp = client.get(f"{BASE}/covariance/matrix/unknown-uuid")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Strategy Comparison endpoints
# ---------------------------------------------------------------------------

class TestComparisonEndpoints:
    def _signal_dict(self, n: int = 200) -> Dict[str, str]:
        return {f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}": "LONG" for i in range(n)}

    def _price_data(self, n: int = 200, drift: float = 0.002) -> Dict[str, List[Dict[str, Any]]]:
        return {"SIMX": [_bar(i, 100.0 * (1 + drift) ** i) for i in range(n)]}

    def _register_strategy(self, name: str = "Alpha", drift: float = 0.002) -> str:
        body = {
            "strategy_name": name,
            "ticker": "SIMX",
            "price_data": self._price_data(drift=drift),
            "signals": self._signal_dict(),
            "initial_capital": 100000.0,
            "commission_rate": 0.001,
        }
        resp = client.post(f"{BASE}/comparison/run-and-register", json=body)
        assert resp.status_code == 200, resp.text
        return resp.json()["strategy_id"]

    def test_run_and_register_success(self):
        sid = self._register_strategy("Test1")
        assert len(sid) > 0

    def test_run_and_register_returns_metrics(self):
        resp = client.post(f"{BASE}/comparison/run-and-register", json={
            "strategy_name": "T",
            "ticker": "SIMX",
            "price_data": self._price_data(),
            "signals": self._signal_dict(),
        })
        assert resp.status_code == 200
        assert resp.json()["metrics"] is not None

    def test_get_metrics_success(self):
        sid = self._register_strategy("GetTest")
        resp = client.get(f"{BASE}/comparison/metrics/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "sharpe_ratio" in data

    def test_get_metrics_404(self):
        resp = client.get(f"{BASE}/comparison/metrics/no-such-uuid")
        assert resp.status_code == 404

    def test_compare_success(self):
        sid1 = self._register_strategy("CompA", drift=0.003)
        sid2 = self._register_strategy("CompB", drift=0.001)
        resp = client.post(f"{BASE}/comparison/compare", json={
            "strategy_ids": [sid1, sid2],
            "primary_metric": "sharpe_ratio",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_table" in data
        assert len(data["ranked_table"]) == 2

    def test_compare_invalid_metric(self):
        sid1 = self._register_strategy("IM1")
        sid2 = self._register_strategy("IM2")
        resp = client.post(f"{BASE}/comparison/compare", json={
            "strategy_ids": [sid1, sid2],
            "primary_metric": "fake_metric",
        })
        assert resp.status_code == 422

    def test_get_comparison_result(self):
        sid1 = self._register_strategy("CR1")
        sid2 = self._register_strategy("CR2")
        cmp_resp = client.post(f"{BASE}/comparison/compare", json={"strategy_ids": [sid1, sid2]})
        cid = cmp_resp.json()["comparison_id"]
        resp = client.get(f"{BASE}/comparison/result/{cid}")
        assert resp.status_code == 200

    def test_get_comparison_result_404(self):
        resp = client.get(f"{BASE}/comparison/result/no-such-uuid")
        assert resp.status_code == 404

    def test_best_by_metric(self):
        sid1 = self._register_strategy("BB1", drift=0.003)
        sid2 = self._register_strategy("BB2", drift=0.001)
        resp = client.post(f"{BASE}/comparison/best", json={"strategy_ids": [sid1, sid2], "metric": "sharpe_ratio"})
        assert resp.status_code == 200
        assert "strategy_name" in resp.json()

    def test_best_by_metric_invalid(self):
        sid = self._register_strategy("BBI")
        resp = client.post(f"{BASE}/comparison/best", json={"strategy_ids": [sid], "metric": "garbage"})
        assert resp.status_code == 422

    def test_rank_by_metric(self):
        sid1 = self._register_strategy("RK1", drift=0.003)
        sid2 = self._register_strategy("RK2", drift=0.001)
        resp = client.post(f"{BASE}/comparison/rank", json={"strategy_ids": [sid1, sid2], "metric": "total_return"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["rank"] == 1

    def test_head_to_head(self):
        sid1 = self._register_strategy("H2H1", drift=0.003)
        sid2 = self._register_strategy("H2H2", drift=0.001)
        resp = client.post(f"{BASE}/comparison/head-to-head", json={"strategy_id_a": sid1, "strategy_id_b": sid2})
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_winner" in data
        assert "wins_a" in data
        assert "wins_b" in data

    def test_head_to_head_unknown_raises(self):
        resp = client.post(f"{BASE}/comparison/head-to-head", json={"strategy_id_a": "bad", "strategy_id_b": "also-bad"})
        assert resp.status_code == 422

    def test_list_strategies(self):
        self._register_strategy("LST1")
        resp = client.get(f"{BASE}/comparison/strategies")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_comparison_reset(self):
        resp = client.delete(f"{BASE}/comparison/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
