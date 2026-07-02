"""Tests for M17 Execution Engine (slippage, impact, VWAP/TWAP, fill simulation)."""
import pytest
import math
from services.execution_engine import (
    ExecutionEngine, SlippageModel, ExecutionBenchmark, MarketImpactModel,
    SlippageEstimate, MarketImpactEstimate, SimulatedFill,
    VWAPResult, TWAPResult, ImplementationShortfall, ExecutionQuality,
)


def _eng():
    return ExecutionEngine()


# ---------------------------------------------------------------------------
# estimate_slippage
# ---------------------------------------------------------------------------

class TestSlippage:
    def test_sqrt_model_positive(self):
        e = _eng()
        r = e.estimate_slippage(10000, 175.0, 500000, 0.02, SlippageModel.SQRT)
        assert r.estimated_slippage_pct > 0
        assert r.estimated_slippage_bps > 0
        assert r.estimated_cost_usd > 0

    def test_sqrt_model_formula(self):
        e = _eng()
        pov = 10000 / 500000
        vol = 0.02
        expected_pct = math.sqrt(pov) * vol
        r = e.estimate_slippage(10000, 175.0, 500000, vol, SlippageModel.SQRT)
        assert r.estimated_slippage_pct == pytest.approx(expected_pct, rel=1e-4)

    def test_linear_model_scales_with_pov(self):
        e = _eng()
        r1 = e.estimate_slippage(10000, 175.0, 500000, 0.02, SlippageModel.LINEAR)
        r2 = e.estimate_slippage(20000, 175.0, 500000, 0.02, SlippageModel.LINEAR)
        assert r2.estimated_slippage_pct > r1.estimated_slippage_pct

    def test_fixed_bps_model(self):
        e = _eng()
        r = e.estimate_slippage(10000, 175.0, 500000, 0.02, SlippageModel.FIXED_BPS, fixed_bps=10.0)
        assert r.estimated_slippage_bps == pytest.approx(10.0, rel=1e-5)

    def test_returns_slippage_estimate(self):
        e = _eng()
        r = e.estimate_slippage(10000, 175.0, 500000, 0.02)
        assert isinstance(r, SlippageEstimate)

    def test_slippage_cost_equals_pct_times_notional(self):
        e = _eng()
        r = e.estimate_slippage(10000, 175.0, 500000, 0.02, SlippageModel.SQRT)
        expected_cost = r.estimated_slippage_pct * 10000 * 175.0
        assert r.estimated_cost_usd == pytest.approx(expected_cost, rel=1e-5)

    def test_volume_adj_model(self):
        e = _eng()
        r = e.estimate_slippage(10000, 175.0, 500000, 0.02, SlippageModel.VOLUME_ADJ)
        assert r.estimated_slippage_bps > 0

    def test_bps_equals_pct_times_10000(self):
        e = _eng()
        r = e.estimate_slippage(10000, 175.0, 500000, 0.02, SlippageModel.SQRT)
        assert r.estimated_slippage_bps == pytest.approx(r.estimated_slippage_pct * 10000, rel=1e-5)


# ---------------------------------------------------------------------------
# estimate_market_impact
# ---------------------------------------------------------------------------

class TestMarketImpact:
    def test_returns_market_impact_estimate(self):
        e = _eng()
        r = e.estimate_market_impact(10000, 500000, 175.0, 0.02)
        assert isinstance(r, MarketImpactEstimate)

    def test_permanent_positive(self):
        e = _eng()
        r = e.estimate_market_impact(10000, 500000, 175.0, 0.02)
        assert r.permanent_impact_bps >= 0

    def test_temporary_positive(self):
        e = _eng()
        r = e.estimate_market_impact(10000, 500000, 175.0, 0.02)
        assert r.temporary_impact_bps >= 0

    def test_total_equals_sum(self):
        e = _eng()
        r = e.estimate_market_impact(10000, 500000, 175.0, 0.02)
        assert r.total_impact_bps == pytest.approx(r.permanent_impact_bps + r.temporary_impact_bps, rel=1e-5)

    def test_larger_order_higher_impact(self):
        e = _eng()
        r1 = e.estimate_market_impact(5000, 500000, 175.0, 0.02)
        r2 = e.estimate_market_impact(50000, 500000, 175.0, 0.02)
        assert r2.total_impact_bps > r1.total_impact_bps

    def test_total_usd_positive(self):
        e = _eng()
        r = e.estimate_market_impact(10000, 500000, 175.0, 0.02)
        assert r.total_impact_usd > 0


# ---------------------------------------------------------------------------
# compute_vwap
# ---------------------------------------------------------------------------

class TestVWAP:
    def test_returns_vwap_result(self):
        e = _eng()
        prices = [100.0, 101.0, 102.0, 101.5, 100.5]
        volumes = [1000, 2000, 1500, 1800, 1200]
        r = e.compute_vwap(prices, volumes)
        assert isinstance(r, VWAPResult)

    def test_vwap_correct_formula(self):
        e = _eng()
        prices = [100.0, 200.0]
        volumes = [100, 100]
        r = e.compute_vwap(prices, volumes)
        assert r.vwap == pytest.approx(150.0, rel=1e-6)

    def test_vwap_weights_higher_volume(self):
        e = _eng()
        prices = [100.0, 200.0]
        volumes = [100, 200]
        r = e.compute_vwap(prices, volumes)
        assert r.vwap > 150.0

    def test_vwap_total_volume(self):
        e = _eng()
        prices = [100.0, 101.0]
        volumes = [500, 500]
        r = e.compute_vwap(prices, volumes)
        assert r.total_volume == 1000

    def test_vwap_n_bars(self):
        e = _eng()
        prices = [100.0, 101.0, 102.0]
        volumes = [100, 100, 100]
        r = e.compute_vwap(prices, volumes)
        assert r.n_bars == 3


# ---------------------------------------------------------------------------
# compute_twap
# ---------------------------------------------------------------------------

class TestTWAP:
    def test_returns_twap_result(self):
        e = _eng()
        prices = [100.0, 102.0, 104.0, 103.0]
        r = e.compute_twap(prices)
        assert isinstance(r, TWAPResult)

    def test_twap_is_arithmetic_mean(self):
        e = _eng()
        prices = [100.0, 110.0, 120.0]
        r = e.compute_twap(prices)
        assert r.twap == pytest.approx(110.0, rel=1e-6)

    def test_twap_single_price(self):
        e = _eng()
        r = e.compute_twap([175.0])
        assert r.twap == pytest.approx(175.0)

    def test_twap_n_bars(self):
        e = _eng()
        r = e.compute_twap([100.0, 102.0, 104.0])
        assert r.n_bars == 3


# ---------------------------------------------------------------------------
# simulate_fill
# ---------------------------------------------------------------------------

class TestSimulateFill:
    def test_returns_simulated_fill(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "BUY", 100, 175.0, 500000, 0.02)
        assert isinstance(r, SimulatedFill)

    def test_market_buy_fills_fully(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "BUY", 100, 175.0, 500000, 0.02)
        assert r.filled_quantity == 100

    def test_fill_rate_partial(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "BUY", 100, 175.0, 500000, 0.02, fill_rate=0.5)
        assert r.filled_quantity == pytest.approx(50.0)

    def test_commission_positive(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "BUY", 100, 175.0, 500000, 0.02)
        assert r.commission_usd > 0

    def test_fill_price_above_arrival_for_buy(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "BUY", 100, 175.0, 500000, 0.02)
        assert r.avg_fill_price > r.arrival_price

    def test_fill_price_below_arrival_for_sell(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "SELL", 100, 175.0, 500000, 0.02)
        assert r.avg_fill_price < r.arrival_price

    def test_is_fully_filled_when_fill_rate_1(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "BUY", 100, 175.0, 500000, 0.02, fill_rate=1.0)
        assert r.is_fully_filled

    def test_not_fully_filled_when_fill_rate_partial(self):
        e = _eng()
        r = e.simulate_fill("AAPL", "BUY", 100, 175.0, 500000, 0.02, fill_rate=0.5)
        assert not r.is_fully_filled


# ---------------------------------------------------------------------------
# implementation_shortfall
# ---------------------------------------------------------------------------

class TestImplementationShortfall:
    def test_returns_is_result(self):
        e = _eng()
        r = e.implementation_shortfall(175.0, 175.10, 175.35, 500, 500, 2.0, is_buy=True)
        assert isinstance(r, ImplementationShortfall)

    def test_spread_cost_positive(self):
        e = _eng()
        r = e.implementation_shortfall(175.0, 175.0, 175.35, 500, 500, 4.0, is_buy=True)
        assert r.spread_cost_bps >= 0

    def test_market_impact_positive_for_buy_above_arrival(self):
        e = _eng()
        r = e.implementation_shortfall(175.0, 175.0, 175.50, 500, 500, 2.0, is_buy=True)
        assert r.market_impact_bps > 0

    def test_total_is_positive_for_unfavourable_buy(self):
        e = _eng()
        r = e.implementation_shortfall(175.0, 175.0, 175.50, 500, 500, 2.0, is_buy=True)
        assert r.total_is_bps > 0

    def test_fill_rate_computed(self):
        e = _eng()
        r = e.implementation_shortfall(175.0, 175.0, 175.35, 1000, 800, 2.0, is_buy=True)
        assert r.fill_rate == pytest.approx(0.8, rel=1e-5)


# ---------------------------------------------------------------------------
# execution_quality
# ---------------------------------------------------------------------------

class TestExecutionQuality:
    def test_quality_score_between_0_100(self):
        e = _eng()
        r = e.execution_quality("AAPL", "BUY", 175.35, 175.0, 500, 2.5)
        assert 0 <= r.score <= 100

    def test_at_benchmark_score_100(self):
        e = _eng()
        r = e.execution_quality("AAPL", "BUY", 175.0, 175.0, 500, 0.0)
        assert r.score == pytest.approx(100.0)

    def test_worse_fill_lower_score(self):
        e = _eng()
        r_good = e.execution_quality("AAPL", "BUY", 175.05, 175.0, 500, 2.5)
        r_bad = e.execution_quality("AAPL", "BUY", 178.0, 175.0, 500, 2.5)
        assert r_good.score > r_bad.score

    def test_returns_execution_quality(self):
        e = _eng()
        r = e.execution_quality("AAPL", "BUY", 175.35, 175.0, 500, 2.5)
        assert isinstance(r, ExecutionQuality)


# ---------------------------------------------------------------------------
# participation_rate / spread_cost / arrival_slippage / commission
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_participation_rate(self):
        e = _eng()
        pr = e.participation_rate(10000, 500000)
        assert pr == pytest.approx(0.02, rel=1e-5)

    def test_participation_rate_zero_adv_raises(self):
        e = _eng()
        with pytest.raises((ValueError, ZeroDivisionError)):
            e.participation_rate(1000, 0)

    def test_spread_cost_half_spread(self):
        e = _eng()
        cost = e.spread_cost(100, 175.0, 4.0)
        expected = 0.5 * (4.0 / 10000) * 175.0 * 100
        assert cost == pytest.approx(expected, rel=1e-5)

    def test_arrival_slippage_buy_adverse(self):
        e = _eng()
        slip = e.arrival_slippage(175.35, 175.0, is_buy=True)
        assert slip > 0

    def test_arrival_slippage_sell_adverse(self):
        e = _eng()
        slip = e.arrival_slippage(174.65, 175.0, is_buy=False)
        assert slip > 0

    def test_compute_commission(self):
        e = _eng()
        comm = e.compute_commission(1000, per_share_rate=0.005)
        assert comm == pytest.approx(1000 * 0.005, rel=1e-5)

    def test_compute_commission_minimum_enforced(self):
        e = _eng()
        comm = e.compute_commission(1, per_share_rate=0.001)
        assert comm >= e.min_commission
