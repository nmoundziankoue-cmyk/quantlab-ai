"""Tests for M9 Phase 8 — Enhanced execution engine."""
import pytest
from services.execution_enhanced import (
    Order, OrderType, OrderSide, OrderStatus,
    OrderBookSimulator, RiskLimits, ExecutionEngine,
    run_pre_trade_risk_checks, smart_route, get_execution_engine,
)


# ---------------------------------------------------------------------------
# OrderBookSimulator
# ---------------------------------------------------------------------------

class TestOrderBookSimulator:
    def test_ask_above_bid(self):
        b = OrderBookSimulator(100.0, 5.0)
        assert b.best_ask() > b.best_bid()

    def test_mid_is_midpoint(self):
        b = OrderBookSimulator(100.0, 10.0)
        assert (b.best_ask() + b.best_bid()) / 2 == pytest.approx(100.0, abs=0.01)

    def test_buy_fills_at_ask(self):
        b = OrderBookSimulator(100.0, 0.0)
        price = b.estimate_fill_price("buy", 1)
        assert price >= 100.0

    def test_sell_fills_at_bid(self):
        b = OrderBookSimulator(100.0, 0.0)
        price = b.estimate_fill_price("sell", 1)
        assert price <= 100.0

    def test_large_order_higher_impact(self):
        b = OrderBookSimulator(100.0, 5.0)
        small = b.estimate_fill_price("buy", 10)
        large = b.estimate_fill_price("buy", 10000)
        assert large > small

    def test_vwap_returns_float(self):
        b = OrderBookSimulator(100.0)
        price = b.simulate_vwap("buy", 1000)
        assert isinstance(price, float)

    def test_to_dict(self):
        b = OrderBookSimulator(100.0, 5.0)
        d = b.to_dict()
        assert "mid" in d and "best_ask" in d and "best_bid" in d


# ---------------------------------------------------------------------------
# Risk checks
# ---------------------------------------------------------------------------

class TestRiskChecks:
    def _order(self, qty=100, otype=OrderType.MARKET):
        return Order(ticker="AAPL", side=OrderSide.BUY, order_type=otype, quantity=qty)

    def test_passes_normal_order(self):
        ok, msg = run_pre_trade_risk_checks(self._order(100), 150.0, RiskLimits())
        assert ok
        assert msg == "OK"

    def test_rejects_large_notional(self):
        ok, msg = run_pre_trade_risk_checks(self._order(10000), 200.0, RiskLimits(max_order_notional=100))
        assert not ok
        assert "notional" in msg.lower()

    def test_rejects_large_quantity(self):
        ok, msg = run_pre_trade_risk_checks(self._order(99999), 1.0, RiskLimits(max_order_qty=1000))
        assert not ok
        assert "quantity" in msg.lower()

    def test_rejects_large_position_pct(self):
        ok, msg = run_pre_trade_risk_checks(self._order(1000), 200.0, RiskLimits(portfolio_value=100, max_position_pct=0.05))
        assert not ok
        assert "position" in msg.lower()


# ---------------------------------------------------------------------------
# Smart routing
# ---------------------------------------------------------------------------

class TestSmartRoute:
    def test_large_market_order_dark_pool(self):
        o = Order(ticker="IBM", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=6000)
        assert smart_route(o, 100) == "DARK_POOL"

    def test_nasdaq_for_big_tech(self):
        o = Order(ticker="AAPL", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10)
        assert smart_route(o, 100) == "NASDAQ"

    def test_iex_for_limit(self):
        o = Order(ticker="IBM", side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=10, limit_price=100)
        assert smart_route(o, 100) == "IEX"


# ---------------------------------------------------------------------------
# ExecutionEngine
# ---------------------------------------------------------------------------

class TestExecutionEngine:
    def setup_method(self):
        self.engine = ExecutionEngine()

    def _order(self, otype=OrderType.MARKET, qty=100, ticker="AAPL"):
        return Order(ticker=ticker, side=OrderSide.BUY, order_type=otype, quantity=qty)

    def test_market_order_fills(self):
        o = self._order(OrderType.MARKET)
        result = self.engine.submit_order(o, 150.0)
        assert result["status"] == "filled"
        assert result["fill_price"] > 0

    def test_limit_order_stays_open(self):
        o = self._order(OrderType.LIMIT)
        o.limit_price = 140.0
        result = self.engine.submit_order(o, 150.0)
        assert result["status"] == "open"

    def test_vwap_order_fills(self):
        o = self._order(OrderType.VWAP)
        result = self.engine.submit_order(o, 150.0)
        assert result["status"] == "filled"

    def test_twap_order_fills(self):
        o = self._order(OrderType.TWAP)
        result = self.engine.submit_order(o, 150.0)
        assert result["status"] == "filled"

    def test_rejected_order_stored(self):
        o = self._order(qty=999999)
        result = self.engine.submit_order(o, 1000.0)
        assert result["status"] == "rejected"

    def test_cancel_open_order(self):
        o = self._order(OrderType.LIMIT)
        o.limit_price = 100.0
        self.engine.submit_order(o, 200.0)
        assert self.engine.cancel_order(o.id)
        assert self.engine.get_order(o.id).status == OrderStatus.CANCELLED

    def test_cancel_nonexistent(self):
        assert not self.engine.cancel_order("fake-id")

    def test_list_orders(self):
        self.engine.submit_order(self._order(OrderType.MARKET), 150.0)
        orders = self.engine.list_orders()
        assert len(orders) >= 1

    def test_list_orders_by_status(self):
        o = self._order(OrderType.LIMIT)
        o.limit_price = 100.0
        self.engine.submit_order(o, 200.0)
        open_orders = self.engine.list_orders(status="open")
        assert all(ord["status"] == "open" for ord in open_orders)

    def test_list_orders_by_ticker(self):
        self.engine.submit_order(self._order(ticker="AAPL"), 150.0)
        aapl = self.engine.list_orders(ticker="AAPL")
        assert all(o["ticker"] == "AAPL" for o in aapl)

    def test_execution_report_created(self):
        self.engine.submit_order(self._order(), 150.0)
        reports = self.engine.execution_reports()
        assert len(reports) >= 1

    def test_latency_stats_after_fill(self):
        self.engine.submit_order(self._order(), 150.0)
        stats = self.engine.latency_stats()
        assert "avg_ms" in stats
        assert stats["avg_ms"] >= 0

    def test_bracket_creates_child_orders(self):
        o = self._order(OrderType.BRACKET)
        o.take_profit_price = 160.0
        o.stop_loss_price = 140.0
        o.limit_price = None
        self.engine.submit_order(o, 150.0)
        # bracket stays open (parent not a market order in strict sense — check children created)
        assert "tp_order" in o.metadata or "sl_order" in o.metadata

    def test_oco_cancels_pair(self):
        o1 = self._order(OrderType.LIMIT)
        o1.limit_price = 100.0
        o2 = self._order(OrderType.LIMIT)
        o2.limit_price = 100.0
        self.engine.submit_order(o1, 200.0)
        self.engine.submit_order(o2, 200.0)
        # Manually set oco pair
        o1.oco_pair_id = o2.id
        self.engine._orders[o1.id] = o1
        self.engine._fill_order(o1.id, 100.0)
        assert self.engine.get_order(o2.id).status == OrderStatus.CANCELLED

    def test_singleton(self):
        e1 = get_execution_engine()
        e2 = get_execution_engine()
        assert e1 is e2
