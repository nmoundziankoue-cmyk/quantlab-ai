"""Tests for M4 stress testing service.

Uses only custom (no-network) scenarios for unit tests.
Built-in scenario tests mock the network call.
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from services.stress_testing import (
    BUILTIN_SCENARIOS,
    run_custom_scenario,
    run_builtin_scenario,
    run_all_builtin_scenarios,
)


@pytest.fixture
def simple_holdings():
    return {"AAPL": 50_000.0, "MSFT": 30_000.0, "GOOG": 20_000.0}


@pytest.fixture
def single_holding():
    return {"AAPL": 100_000.0}


# ---------------------------------------------------------------------------
# Built-in scenario registry
# ---------------------------------------------------------------------------

class TestBuiltinRegistry:
    def test_at_least_5_scenarios(self):
        assert len(BUILTIN_SCENARIOS) >= 5

    def test_each_scenario_has_required_keys(self):
        for key, val in BUILTIN_SCENARIOS.items():
            assert "name" in val
            assert "start" in val
            assert "end" in val
            assert "description" in val

    def test_scenario_dates_valid(self):
        from datetime import date
        for key, val in BUILTIN_SCENARIOS.items():
            start = date.fromisoformat(val["start"])
            end = date.fromisoformat(val["end"])
            assert end > start, f"Scenario {key}: end must be after start"


# ---------------------------------------------------------------------------
# Custom scenario
# ---------------------------------------------------------------------------

class TestCustomScenario:
    def test_full_market_crash(self, simple_holdings):
        shocks = {"_MARKET_": -0.30}
        result = run_custom_scenario("Test Crash", shocks, simple_holdings)
        assert result["portfolio_return_pct"] == pytest.approx(-30.0, abs=0.01)
        assert result["total_pnl"] == pytest.approx(-30_000.0, abs=0.01)

    def test_per_ticker_shocks(self, simple_holdings):
        shocks = {"AAPL": -0.50, "MSFT": -0.20, "GOOG": 0.0}
        result = run_custom_scenario("Tech Crash", shocks, simple_holdings)
        expected_pnl = 50_000 * -0.50 + 30_000 * -0.20 + 20_000 * 0.0
        assert result["total_pnl"] == pytest.approx(expected_pnl, abs=0.01)

    def test_mixed_shocks(self, simple_holdings):
        shocks = {"AAPL": -0.20, "_MARKET_": -0.10}
        result = run_custom_scenario("Mixed", shocks, simple_holdings)
        # AAPL gets -20%, others get -10%
        expected_pnl = 50_000 * -0.20 + 30_000 * -0.10 + 20_000 * -0.10
        assert result["total_pnl"] == pytest.approx(expected_pnl, abs=0.01)

    def test_asset_impacts_sorted_by_pnl(self, simple_holdings):
        shocks = {"AAPL": -0.50, "MSFT": -0.10, "GOOG": 0.05}
        result = run_custom_scenario("Sort test", shocks, simple_holdings)
        pnls = [a["pnl"] for a in result["asset_impacts"]]
        assert pnls == sorted(pnls)

    def test_weight_pct_sums_to_100(self, simple_holdings):
        shocks = {"_MARKET_": -0.20}
        result = run_custom_scenario("Weight test", shocks, simple_holdings)
        total_weight = sum(a["weight_pct"] for a in result["asset_impacts"])
        assert abs(total_weight - 100.0) < 0.01

    def test_scenario_metadata(self, simple_holdings):
        result = run_custom_scenario("My Scenario", {"_MARKET_": 0.0}, simple_holdings)
        assert result["scenario_name"] == "My Scenario"
        assert result["scenario_key"] == "custom"

    def test_zero_shock_zero_pnl(self, simple_holdings):
        shocks = {"_MARKET_": 0.0}
        result = run_custom_scenario("Zero", shocks, simple_holdings)
        assert result["total_pnl"] == 0.0

    def test_positive_shock(self, simple_holdings):
        shocks = {"_MARKET_": 0.10}
        result = run_custom_scenario("Rally", shocks, simple_holdings)
        assert result["total_pnl"] == pytest.approx(10_000.0, abs=0.01)


# ---------------------------------------------------------------------------
# Built-in scenario (with mocked network)
# ---------------------------------------------------------------------------

MOCK_PRICES = {
    "AAPL": [150.0, 90.0],   # -40% return
    "MSFT": [200.0, 140.0],  # -30% return
    "GOOG": [100.0, 55.0],   # -45% return
}


def _make_mock_prices(tickers, start, end):
    import pandas as pd
    import numpy as np
    dates = pd.date_range(start, end, periods=2)
    data = {t: MOCK_PRICES.get(t, [100.0, 80.0]) for t in tickers}
    return pd.DataFrame(data, index=dates)


class TestBuiltinScenario:
    @patch("services.stress_testing.get_price_history", side_effect=_make_mock_prices)
    def test_covid_crash_correct_pnl(self, mock_prices, simple_holdings):
        result = run_builtin_scenario("covid_crash", simple_holdings)
        # AAPL: -40%, MSFT: -30%, GOOG: -45%
        expected_pnl = 50_000 * -0.40 + 30_000 * -0.30 + 20_000 * -0.45
        assert result["total_pnl"] == pytest.approx(expected_pnl, rel=0.01)

    @patch("services.stress_testing.get_price_history", side_effect=_make_mock_prices)
    def test_result_structure(self, mock_prices, simple_holdings):
        result = run_builtin_scenario("2008_financial_crisis", simple_holdings)
        assert "scenario_key" in result
        assert "asset_impacts" in result
        assert "portfolio_return_pct" in result

    def test_invalid_scenario_key_raises(self, simple_holdings):
        with pytest.raises(ValueError, match="Unknown scenario"):
            run_builtin_scenario("nonexistent_crash", simple_holdings)


# ---------------------------------------------------------------------------
# run_all_builtin_scenarios
# ---------------------------------------------------------------------------

class TestRunAllScenarios:
    @patch("services.stress_testing.get_price_history", side_effect=_make_mock_prices)
    def test_returns_all_scenarios(self, mock_prices, simple_holdings):
        results = run_all_builtin_scenarios(simple_holdings)
        assert len(results) == len(BUILTIN_SCENARIOS)

    @patch("services.stress_testing.get_price_history", side_effect=_make_mock_prices)
    def test_each_result_has_scenario_key(self, mock_prices, simple_holdings):
        results = run_all_builtin_scenarios(simple_holdings)
        for r in results:
            assert "scenario_key" in r
            assert "scenario_name" in r
