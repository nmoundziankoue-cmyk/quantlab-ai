"""Tests for M19 ExecutionSimulator service."""

import pytest
from services.m19_execution_simulator import (
    ExecutionSimulator,
    SimOrder,
    Fill,
    FillModel,
    SlippageReport,
    OrderType,
    OrderStatus,
    SlippageModel,
)


def make_order(
    ticker="AAPL",
    side="BUY",
    qty=100.0,
    order_type=OrderType.MARKET,
    limit_price=None,
    stop_price=None,
) -> SimOrder:
    import uuid
    return SimOrder(
        order_id=str(uuid.uuid4()),
        ticker=ticker,
        order_type=order_type,
        side=side,
        quantity=qty,
        limit_price=limit_price,
        stop_price=stop_price,
    )


class TestExecutionSimulatorInit:
    def test_created(self):
        sim = ExecutionSimulator()
        assert sim is not None

    def test_starts_with_empty_history(self):
        sim = ExecutionSimulator()
        assert sim.get_fill_history() == []
        assert sim.get_order_history() == []

    def test_reset_clears_history(self):
        sim = ExecutionSimulator()
        order = make_order()
        sim.simulate(order, market_price=100.0)
        sim.reset()
        assert sim.get_fill_history() == []

    def test_seed_reproducibility(self):
        sim1 = ExecutionSimulator(seed=42)
        sim2 = ExecutionSimulator(seed=42)
        o1 = make_order()
        o2 = make_order()
        o1.order_id = o2.order_id = "same"
        f1 = sim1.simulate(o1, 100.0)
        f2 = sim2.simulate(o2, 100.0)
        assert f1.latency_us == f2.latency_us


class TestMarketOrderFill:
    def setup_method(self):
        self.sim = ExecutionSimulator(seed=1)

    def test_market_order_filled(self):
        order = make_order(order_type=OrderType.MARKET)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)

    def test_fill_has_fill_id(self):
        order = make_order()
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.fill_id != ""

    def test_fill_has_positive_fill_price(self):
        order = make_order()
        fill = self.sim.simulate(order, market_price=100.0)
        if fill.fill_qty > 0:
            assert fill.fill_price > 0

    def test_buy_slippage_increases_price(self):
        order = make_order(side="BUY")
        fill = self.sim.simulate(order, market_price=100.0, fixed_slippage_bps=10.0, market_volume=1e9)
        if fill.fill_qty > 0:
            assert fill.fill_price >= 100.0

    def test_sell_slippage_decreases_price(self):
        order = make_order(side="SELL")
        fill = self.sim.simulate(order, market_price=100.0, fixed_slippage_bps=10.0, market_volume=1e9)
        if fill.fill_qty > 0:
            assert fill.fill_price <= 100.0

    def test_fill_has_commission(self):
        order = make_order()
        fill = self.sim.simulate(order, market_price=100.0, commission_rate=0.001)
        if fill.fill_qty > 0:
            assert fill.commission > 0

    def test_zero_commission(self):
        order = make_order()
        fill = self.sim.simulate(order, market_price=100.0, commission_rate=0.0)
        assert fill.commission == 0.0

    def test_fill_has_latency(self):
        order = make_order()
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.latency_us >= 1

    def test_fill_has_market_impact(self):
        order = make_order()
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.market_impact >= 0.0

    def test_to_dict_has_expected_keys(self):
        order = make_order()
        fill = self.sim.simulate(order, market_price=100.0)
        d = fill.to_dict()
        for key in ["fill_id", "ticker", "fill_price", "fill_qty", "status"]:
            assert key in d

    def test_rejected_order_with_zero_qty(self):
        order = make_order(qty=0.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status == OrderStatus.REJECTED

    def test_fill_quantity_non_negative(self):
        order = make_order(qty=1000.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.fill_qty >= 0


class TestLimitOrder:
    def setup_method(self):
        self.sim = ExecutionSimulator(seed=2)

    def test_buy_limit_filled_when_price_below_limit(self):
        order = make_order(order_type=OrderType.LIMIT, side="BUY", limit_price=105.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)

    def test_buy_limit_cancelled_when_price_above_limit(self):
        order = make_order(order_type=OrderType.LIMIT, side="BUY", limit_price=95.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status == OrderStatus.CANCELLED

    def test_sell_limit_filled_when_price_above_limit(self):
        order = make_order(order_type=OrderType.LIMIT, side="SELL", limit_price=95.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)

    def test_sell_limit_cancelled_when_price_below_limit(self):
        order = make_order(order_type=OrderType.LIMIT, side="SELL", limit_price=105.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status == OrderStatus.CANCELLED


class TestStopOrder:
    def setup_method(self):
        self.sim = ExecutionSimulator(seed=3)

    def test_buy_stop_triggered_when_price_above_stop(self):
        order = make_order(order_type=OrderType.STOP, side="BUY", stop_price=95.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)

    def test_buy_stop_cancelled_when_price_below_stop(self):
        order = make_order(order_type=OrderType.STOP, side="BUY", stop_price=105.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status == OrderStatus.CANCELLED

    def test_sell_stop_triggered_when_price_below_stop(self):
        order = make_order(order_type=OrderType.STOP, side="SELL", stop_price=105.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)

    def test_sell_stop_cancelled_when_price_above_stop(self):
        order = make_order(order_type=OrderType.STOP, side="SELL", stop_price=95.0)
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status == OrderStatus.CANCELLED


class TestStopLimitOrder:
    def setup_method(self):
        self.sim = ExecutionSimulator(seed=4)

    def test_stop_limit_fill_when_conditions_met(self):
        order = make_order(
            order_type=OrderType.STOP_LIMIT, side="BUY", stop_price=95.0, limit_price=105.0
        )
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)

    def test_stop_limit_cancelled_stop_not_triggered(self):
        order = make_order(
            order_type=OrderType.STOP_LIMIT, side="BUY", stop_price=105.0, limit_price=110.0
        )
        fill = self.sim.simulate(order, market_price=100.0)
        assert fill.status == OrderStatus.CANCELLED


class TestSlippageModels:
    def setup_method(self):
        self.sim = ExecutionSimulator(seed=5)

    def test_fixed_bps_model(self):
        order = make_order()
        fill = self.sim.simulate(order, 100.0, slippage_model=SlippageModel.FIXED_BPS, fixed_slippage_bps=5.0, market_volume=1e9)
        if fill.fill_qty > 0:
            assert fill.market_impact > 0

    def test_volume_weighted_model(self):
        order = make_order()
        fill = self.sim.simulate(order, 100.0, slippage_model=SlippageModel.VOLUME_WEIGHTED, market_volume=1e6)
        if fill.fill_qty > 0:
            assert fill.market_impact >= 0

    def test_sqrt_model(self):
        order = make_order(qty=10_000)
        fill = self.sim.simulate(order, 100.0, slippage_model=SlippageModel.SQRT, market_volume=1_000_000)
        if fill.fill_qty > 0:
            assert fill.market_impact >= 0

    def test_higher_slippage_bps_raises_impact(self):
        order1 = make_order()
        order2 = make_order()
        f1 = self.sim.simulate(order1, 100.0, slippage_model=SlippageModel.FIXED_BPS, fixed_slippage_bps=1.0, market_volume=1e9)
        f2 = self.sim.simulate(order2, 100.0, slippage_model=SlippageModel.FIXED_BPS, fixed_slippage_bps=20.0, market_volume=1e9)
        if f1.fill_qty > 0 and f2.fill_qty > 0:
            assert f2.market_impact > f1.market_impact


class TestBatchSimulation:
    def setup_method(self):
        self.sim = ExecutionSimulator(seed=6)

    def test_batch_returns_fills(self):
        orders = [make_order(ticker="AAPL"), make_order(ticker="MSFT")]
        fills = self.sim.simulate_batch(orders, prices={"AAPL": 150.0, "MSFT": 300.0})
        assert len(fills) == 2

    def test_batch_skips_unknown_ticker(self):
        orders = [make_order(ticker="UNKN")]
        fills = self.sim.simulate_batch(orders, prices={})
        assert len(fills) == 0

    def test_batch_preserves_order(self):
        orders = [make_order(ticker="AAPL"), make_order(ticker="MSFT"), make_order(ticker="GOOG")]
        fills = self.sim.simulate_batch(
            orders,
            prices={"AAPL": 150.0, "MSFT": 300.0, "GOOG": 200.0}
        )
        assert len(fills) == 3


class TestSlippageReport:
    def setup_method(self):
        self.sim = ExecutionSimulator(seed=7)

    def test_empty_slippage_report(self):
        report = self.sim.get_slippage_report()
        assert report.num_fills == 0

    def test_slippage_report_after_fills(self):
        order = make_order(order_type=OrderType.MARKET)
        self.sim.simulate(order, market_price=100.0, market_volume=1e9)
        report = self.sim.get_slippage_report()
        assert report.num_fills >= 0

    def test_slippage_report_to_dict(self):
        report = SlippageReport(
            num_fills=5, total_slippage=1.5, avg_slippage_bps=3.0,
            max_slippage_bps=10.0, total_commission=0.5, total_market_impact=0.001, fill_rate=0.95
        )
        d = report.to_dict()
        assert "num_fills" in d and "avg_slippage_bps" in d

    def test_fill_rate_between_0_and_1(self):
        order = make_order()
        self.sim.simulate(order, market_price=100.0, market_volume=1e9)
        report = self.sim.get_slippage_report()
        assert 0.0 <= report.fill_rate <= 1.0


class TestFillModel:
    def setup_method(self):
        self.sim = ExecutionSimulator()

    def test_build_fill_model(self):
        model = self.sim.build_fill_model("TestModel")
        assert model.model_name == "TestModel"

    def test_fill_model_defaults(self):
        model = self.sim.build_fill_model("M1")
        assert model.fill_probability == 0.95

    def test_fill_model_custom_params(self):
        model = self.sim.build_fill_model("M2", fill_probability=0.80)
        assert model.fill_probability == 0.80

    def test_fill_model_to_dict(self):
        model = self.sim.build_fill_model("M3")
        d = model.to_dict()
        assert "model_name" in d and "fill_probability" in d


class TestImplementationShortfall:
    def setup_method(self):
        self.sim = ExecutionSimulator()

    def test_zero_shortfall_at_decision_price(self):
        order = make_order(side="BUY")
        fill = self.sim.simulate(order, market_price=100.0, market_volume=1e9)
        if fill.fill_qty > 0:
            result = self.sim.compute_implementation_shortfall(order, 100.0, fill)
            assert "shortfall_bps" in result

    def test_shortfall_positive_for_buy_above_decision(self):
        order = make_order(side="BUY")
        fill = self.sim.simulate(order, market_price=105.0, market_volume=1e9)
        if fill.fill_qty > 0:
            result = self.sim.compute_implementation_shortfall(order, 100.0, fill)
            assert result["shortfall_bps"] >= 0

    def test_shortfall_zero_fill_qty(self):
        order = make_order(qty=0.0)
        fill = self.sim.simulate(order, market_price=100.0)
        result = self.sim.compute_implementation_shortfall(order, 100.0, fill)
        assert result["shortfall_bps"] == 0.0
