"""Tests for the Market Intelligence Platform (M7) — pure/no-DB service."""
from __future__ import annotations

import pytest

from services.market_intelligence import (
    SECTORS,
    get_correlation_matrix,
    get_global_macro,
    get_liquidity_metrics,
    get_market_breadth,
    get_market_regime,
    get_sector_heatmap,
    get_yield_curve,
)


# ---------------------------------------------------------------------------
# Sector heatmap
# ---------------------------------------------------------------------------

class TestSectorHeatmap:
    def test_returns_all_sectors(self):
        result = get_sector_heatmap("1D")
        assert len(result["sectors"]) == len(SECTORS)

    def test_each_sector_has_performance(self):
        result = get_sector_heatmap("1D")
        for s in result["sectors"]:
            assert "performance" in s
            assert isinstance(s["performance"], float)

    def test_best_worst_sectors_present(self):
        result = get_sector_heatmap("1D")
        assert result["best_sector"] is not None
        assert result["worst_sector"] is not None

    def test_market_breadth_between_0_and_1(self):
        result = get_sector_heatmap("1D")
        assert 0 <= result["market_breadth"] <= 1

    def test_weekly_period(self):
        result = get_sector_heatmap("1W")
        assert result["period"] == "1W"

    def test_monthly_period(self):
        result = get_sector_heatmap("1M")
        assert result["period"] == "1M"

    def test_sectors_sorted_by_performance(self):
        result = get_sector_heatmap("1D")
        perfs = [s["performance"] for s in result["sectors"]]
        assert perfs == sorted(perfs, reverse=True)

    def test_deterministic_output(self):
        r1 = get_sector_heatmap("1D")
        r2 = get_sector_heatmap("1D")
        assert r1["best_sector"] == r2["best_sector"]


# ---------------------------------------------------------------------------
# Market breadth
# ---------------------------------------------------------------------------

class TestMarketBreadth:
    def test_returns_expected_keys(self):
        result = get_market_breadth()
        assert "advancing" in result
        assert "declining" in result
        assert "ad_ratio" in result
        assert "new_52w_highs" in result
        assert "new_52w_lows" in result
        assert "pct_above_50ma" in result
        assert "pct_above_200ma" in result

    def test_advancing_plus_declining_leq_universe(self):
        result = get_market_breadth()
        assert result["advancing"] + result["declining"] <= result["universe"]

    def test_ad_ratio_positive(self):
        result = get_market_breadth()
        assert result["ad_ratio"] > 0

    def test_pct_above_ma_in_range(self):
        result = get_market_breadth()
        assert 0 <= result["pct_above_50ma"] <= 100
        assert 0 <= result["pct_above_200ma"] <= 100

    def test_deterministic_output(self):
        r1 = get_market_breadth()
        r2 = get_market_breadth()
        assert r1["advancing"] == r2["advancing"]


# ---------------------------------------------------------------------------
# Market regime
# ---------------------------------------------------------------------------

class TestMarketRegime:
    def test_returns_regime_label(self):
        result = get_market_regime()
        assert "regime" in result
        assert "regime_label" in result

    def test_regime_is_valid(self):
        result = get_market_regime()
        valid_regimes = {"BULL_TRENDING", "BULL_CONSOLIDATING", "BEAR_TRENDING", "HIGH_VOLATILITY", "NEUTRAL"}
        assert result["regime"] in valid_regimes

    def test_vix_positive(self):
        result = get_market_regime()
        assert result["vix"] > 0

    def test_vol_regime_present(self):
        result = get_market_regime()
        valid_vol = {"LOW_VOL", "NORMAL_VOL", "HIGH_VOL", "EXTREME_VOL"}
        assert result["vol_regime"] in valid_vol

    def test_risk_on_score_in_range(self):
        result = get_market_regime()
        assert 0 <= result["risk_on_score"] <= 100

    def test_signals_dict_present(self):
        result = get_market_regime()
        assert "signals" in result
        assert "breadth_pct_above_200ma" in result["signals"]


# ---------------------------------------------------------------------------
# Yield curve
# ---------------------------------------------------------------------------

class TestYieldCurve:
    def test_returns_curve_points(self):
        result = get_yield_curve()
        assert "curve" in result
        assert len(result["curve"]) > 0

    def test_spread_2s10s_present(self):
        result = get_yield_curve()
        assert "spread_2s10s" in result

    def test_is_inverted_boolean(self):
        result = get_yield_curve()
        assert isinstance(result["is_inverted"], bool)

    def test_curve_shape_valid(self):
        result = get_yield_curve()
        assert result["curve_shape"] in ("inverted", "flat", "normal")

    def test_all_yields_positive(self):
        result = get_yield_curve()
        for point in result["curve"]:
            assert point["yield"] > 0

    def test_spread_consistency(self):
        result = get_yield_curve()
        inv = result["is_inverted"]
        spread = result["spread_2s10s"]
        assert (spread < 0) == inv


# ---------------------------------------------------------------------------
# Global macro
# ---------------------------------------------------------------------------

class TestGlobalMacro:
    def test_returns_us_indicators(self):
        result = get_global_macro()
        assert "us" in result
        assert "gdp_growth_yoy" in result["us"]
        assert "cpi_yoy" in result["us"]

    def test_returns_global_indicators(self):
        result = get_global_macro()
        assert "global" in result
        assert "dollar_index_dxy" in result["global"]

    def test_returns_central_banks(self):
        result = get_global_macro()
        assert "central_banks" in result
        assert "fed_rate" in result["central_banks"]

    def test_gdp_growth_in_plausible_range(self):
        result = get_global_macro()
        gdp = result["us"]["gdp_growth_yoy"]
        assert -5 < gdp < 15


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

class TestCorrelationMatrix:
    def test_diagonal_is_1(self):
        result = get_correlation_matrix(["AAPL", "MSFT", "GOOGL"])
        for i in range(3):
            assert result["matrix"][i][i] == 1.0

    def test_symmetric(self):
        tickers = ["AAPL", "MSFT", "GOOGL"]
        result = get_correlation_matrix(tickers)
        m = result["matrix"]
        for i in range(len(tickers)):
            for j in range(len(tickers)):
                assert m[i][j] == m[j][i]

    def test_correlations_in_range(self):
        result = get_correlation_matrix(["AAPL", "NVDA"])
        for row in result["matrix"]:
            for v in row:
                assert -1.0 <= v <= 1.0

    def test_single_ticker(self):
        result = get_correlation_matrix(["AAPL"])
        assert result["matrix"] == [[1.0]]


# ---------------------------------------------------------------------------
# Liquidity metrics
# ---------------------------------------------------------------------------

class TestLiquidityMetrics:
    def test_returns_expected_keys(self):
        result = get_liquidity_metrics("AAPL")
        assert "ticker" in result
        assert "avg_daily_volume" in result
        assert "bid_ask_spread_bps" in result
        assert "liquidity_score" in result

    def test_liquidity_score_in_range(self):
        result = get_liquidity_metrics("AAPL")
        assert 0 <= result["liquidity_score"] <= 100

    def test_ticker_returned(self):
        result = get_liquidity_metrics("MSFT")
        assert result["ticker"] == "MSFT"

    def test_deterministic(self):
        r1 = get_liquidity_metrics("AAPL")
        r2 = get_liquidity_metrics("AAPL")
        assert r1["avg_daily_volume"] == r2["avg_daily_volume"]
