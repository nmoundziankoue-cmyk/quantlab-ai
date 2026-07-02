"""Tests for M17 Order Management System (OMSEngine)."""
import pytest
from datetime import datetime, timezone, timedelta
from services.order_management import (
    OMSEngine, OrderType, OrderSide, OrderStatus, TimeInForce, PegType,
    TrailType, Order, Fill,
)


def _oms():
    return OMSEngine()


def _now():
    return datetime.now(timezone.utc)


def _sub(oms, ticker, order_type, side, quantity, **kwargs):
    """Shorthand that passes positional args in the right order."""
    return oms.submit_order(ticker, order_type, side, quantity, **kwargs)


# ---------------------------------------------------------------------------
# submit_order — basic types
# ---------------------------------------------------------------------------

class TestSubmitOrderBasic:
    def test_submit_market_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        assert o.status == OrderStatus.WORKING
        assert o.ticker == "AAPL"
        assert o.quantity == 100

    def test_submit_limit_order(self):
        oms = _oms()
        o = _sub(oms, "MSFT", OrderType.LIMIT, OrderSide.SELL, 50, limit_price=420.0)
        assert o.limit_price == 420.0
        assert o.order_type == OrderType.LIMIT

    def test_submit_stop_order(self):
        oms = _oms()
        o = _sub(oms, "NVDA", OrderType.STOP, OrderSide.SELL, 200, stop_price=800.0)
        assert o.stop_price == 800.0

    def test_submit_stop_limit_order(self):
        oms = _oms()
        o = _sub(oms, "TSLA", OrderType.STOP_LIMIT, OrderSide.BUY, 10, limit_price=250.0, stop_price=248.0)
        assert o.limit_price == 250.0
        assert o.stop_price == 248.0

    def test_submit_assigns_unique_order_ids(self):
        oms = _oms()
        ids = {_sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100).order_id for _ in range(10)}
        assert len(ids) == 10

    def test_submit_returns_order_instance(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        assert isinstance(o, Order)

    def test_submit_market_sell_short(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.SELL_SHORT, 100)
        assert o.side == OrderSide.SELL_SHORT

    def test_submit_buy_to_cover(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY_TO_COVER, 100)
        assert o.side == OrderSide.BUY_TO_COVER

    def test_submit_moc_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MOC, OrderSide.BUY, 100)
        assert o.order_type == OrderType.MOC

    def test_submit_moo_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MOO, OrderSide.BUY, 100)
        assert o.order_type == OrderType.MOO

    def test_submit_loc_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LOC, OrderSide.BUY, 100, limit_price=175.0)
        assert o.order_type == OrderType.LOC

    def test_submit_loo_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LOO, OrderSide.BUY, 100, limit_price=175.0)
        assert o.order_type == OrderType.LOO

    def test_submit_pegged_order_stored(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.PEGGED, OrderSide.BUY, 100, peg_type=PegType.MID)
        assert o.order_type == OrderType.PEGGED

    def test_submit_trailing_stop_amount(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.TRAILING_STOP, OrderSide.SELL, 100, trail_amount=5.0, trail_type=TrailType.AMOUNT)
        assert o.trail_amount == 5.0
        assert o.trail_type == TrailType.AMOUNT

    def test_submit_trailing_stop_pct(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.TRAILING_STOP, OrderSide.SELL, 100, trail_amount=2.0, trail_type=TrailType.PERCENT)
        assert o.trail_type == TrailType.PERCENT

    def test_trailing_stop_without_trail_amount_raises(self):
        oms = _oms()
        with pytest.raises(ValueError):
            _sub(oms, "AAPL", OrderType.TRAILING_STOP, OrderSide.SELL, 100)

    def test_submit_twap_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.TWAP, OrderSide.BUY, 1000)
        assert o.order_type == OrderType.TWAP

    def test_submit_vwap_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.VWAP, OrderSide.BUY, 1000)
        assert o.order_type == OrderType.VWAP

    def test_submit_iceberg_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.ICEBERG, OrderSide.BUY, 10000, iceberg_visible_qty=100)
        assert o.iceberg_visible_qty == 100

    def test_iceberg_without_visible_qty_raises(self):
        oms = _oms()
        with pytest.raises(ValueError):
            _sub(oms, "AAPL", OrderType.ICEBERG, OrderSide.BUY, 10000)

    def test_submit_day_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100, time_in_force=TimeInForce.DAY)
        assert o.time_in_force == TimeInForce.DAY

    def test_submit_gtc_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=170.0, time_in_force=TimeInForce.GTC)
        assert o.time_in_force == TimeInForce.GTC

    def test_submit_gtd_order(self):
        oms = _oms()
        exp = _now() + timedelta(days=5)
        o = _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=170.0, time_in_force=TimeInForce.GTD, expires_at=exp)
        assert o.expires_at == exp

    def test_submit_fok_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.FOK, OrderSide.BUY, 100, limit_price=175.0)
        assert o.order_type == OrderType.FOK

    def test_submit_ioc_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.IOC, OrderSide.BUY, 100, limit_price=175.0)
        assert o.order_type == OrderType.IOC

    def test_submit_hidden_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.HIDDEN, OrderSide.BUY, 100)
        assert o.order_type == OrderType.HIDDEN

    def test_submit_zero_quantity_raises(self):
        oms = _oms()
        with pytest.raises(ValueError):
            _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 0)


# ---------------------------------------------------------------------------
# record_fill
# ---------------------------------------------------------------------------

class TestRecordFill:
    def test_full_fill_sets_filled_status(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        f = oms.record_fill(o.order_id, 100, 175.0)
        assert oms.get_order(o.order_id).status == OrderStatus.FILLED
        assert f.quantity == 100

    def test_partial_fill_sets_partial_status(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0)
        oms.record_fill(o.order_id, 50, 175.0)
        assert oms.get_order(o.order_id).status == OrderStatus.PARTIAL

    def test_partial_then_full_fill(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0)
        oms.record_fill(o.order_id, 60, 175.0)
        oms.record_fill(o.order_id, 40, 175.0)
        assert oms.get_order(o.order_id).status == OrderStatus.FILLED

    def test_fill_updates_filled_quantity(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        oms.record_fill(o.order_id, 75, 175.0)
        assert oms.get_order(o.order_id).filled_quantity == 75

    def test_fill_updates_avg_price(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        oms.record_fill(o.order_id, 50, 174.0)
        oms.record_fill(o.order_id, 50, 176.0)
        assert oms.get_order(o.order_id).avg_fill_price == pytest.approx(175.0)

    def test_fill_returns_fill_instance(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        f = oms.record_fill(o.order_id, 100, 175.0)
        assert isinstance(f, Fill)

    def test_fill_invalid_order_raises(self):
        oms = _oms()
        with pytest.raises((KeyError, ValueError)):
            oms.record_fill("nonexistent", 100, 175.0)


# ---------------------------------------------------------------------------
# cancel / amend / reject
# ---------------------------------------------------------------------------

class TestCancelAmendReject:
    def test_cancel_open_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0)
        oms.cancel_order(o.order_id)
        assert oms.get_order(o.order_id).status == OrderStatus.CANCELLED

    def test_cancel_filled_order_raises(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        oms.record_fill(o.order_id, 100, 175.0)
        with pytest.raises((ValueError, RuntimeError)):
            oms.cancel_order(o.order_id)

    def test_amend_limit_price(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0)
        oms.amend_order(o.order_id, limit_price=180.0)
        assert oms.get_order(o.order_id).limit_price == 180.0

    def test_amend_quantity(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0)
        oms.amend_order(o.order_id, quantity=50)
        assert oms.get_order(o.order_id).quantity == 50

    def test_reject_order(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        oms.reject_order(o.order_id, "Risk limit exceeded")
        assert oms.get_order(o.order_id).status == OrderStatus.REJECTED


# ---------------------------------------------------------------------------
# brackets, OCO, TWAP/VWAP children, trailing stop
# ---------------------------------------------------------------------------

class TestBracketsAndSpecial:
    def test_create_bracket(self):
        oms = _oms()
        r = oms.create_bracket("AAPL", OrderSide.BUY, 100, 175.0, 185.0, 165.0)
        assert r.parent is not None
        assert r.take_profit is not None
        assert r.stop_loss is not None

    def test_create_bracket_parent_is_limit(self):
        oms = _oms()
        r = oms.create_bracket("AAPL", OrderSide.BUY, 100, 175.0, 185.0, 165.0)
        assert r.parent.order_type == OrderType.LIMIT

    def test_create_oco(self):
        oms = _oms()
        r = oms.create_oco("AAPL", OrderSide.SELL, 100, 185.0, 165.0)
        assert r.limit_order is not None
        assert r.stop_order is not None

    def test_generate_twap_children(self):
        oms = _oms()
        parent, children = oms.generate_twap_children("AAPL", OrderSide.BUY, 1000, 5)
        assert len(children) == 5
        total_qty = sum(c.quantity for c in children)
        assert total_qty == 1000

    def test_generate_vwap_children(self):
        oms = _oms()
        profile = [0.1, 0.2, 0.3, 0.25, 0.15]
        parent, children = oms.generate_vwap_children("AAPL", OrderSide.BUY, 1000, profile)
        assert len(children) == 5
        assert sum(c.quantity for c in children) == pytest.approx(1000, abs=1)

    def test_update_trailing_stop_ratchets(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.TRAILING_STOP, OrderSide.SELL, 100, trail_amount=5.0, trail_type=TrailType.AMOUNT)
        oms.update_trailing_stop(o.order_id, 175.0)
        oms.update_trailing_stop(o.order_id, 180.0)
        updated = oms.get_order(o.order_id)
        assert updated.stop_price is not None


# ---------------------------------------------------------------------------
# query methods
# ---------------------------------------------------------------------------

class TestQueryMethods:
    def test_get_orders_returns_all(self):
        oms = _oms()
        for _ in range(5):
            _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        assert len(oms.get_orders()) == 5

    def test_get_open_orders_excludes_filled(self):
        oms = _oms()
        o1 = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        o2 = _sub(oms, "MSFT", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=420.0)
        oms.record_fill(o1.order_id, 100, 175.0)
        open_orders = oms.get_open_orders()
        ids = [o.order_id for o in open_orders]
        assert o1.order_id not in ids
        assert o2.order_id in ids

    def test_get_orders_filter_by_ticker(self):
        oms = _oms()
        _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        _sub(oms, "MSFT", OrderType.MARKET, OrderSide.BUY, 100)
        result = oms.get_orders(ticker="AAPL")
        assert all(o.ticker == "AAPL" for o in result)

    def test_get_orders_filter_by_status(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        oms.record_fill(o.order_id, 100, 175.0)
        _sub(oms, "MSFT", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=420.0)
        result = oms.get_orders(status=OrderStatus.FILLED)
        assert all(x.status == OrderStatus.FILLED for x in result)

    def test_order_summary_counts(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        oms.record_fill(o.order_id, 100, 175.0)
        _sub(oms, "MSFT", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=420.0)
        summary = oms.order_summary()
        assert summary["total_orders"] == 2
        assert summary["by_status"].get("FILLED", 0) == 1
        assert summary["by_status"].get("WORKING", 0) >= 1

    def test_expire_day_orders(self):
        oms = _oms()
        _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0, time_in_force=TimeInForce.DAY)
        expired = oms.expire_day_orders()
        assert len(expired) == 1

    def test_expire_gtd_orders_past_expiry(self):
        oms = _oms()
        past = _now() - timedelta(seconds=1)
        _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0, time_in_force=TimeInForce.GTD, expires_at=past)
        expired = oms.expire_gtd_orders(as_of=_now())
        assert len(expired) == 1

    def test_expire_gtd_orders_future_not_expired(self):
        oms = _oms()
        future = _now() + timedelta(days=5)
        _sub(oms, "AAPL", OrderType.LIMIT, OrderSide.BUY, 100, limit_price=175.0, time_in_force=TimeInForce.GTD, expires_at=future)
        expired = oms.expire_gtd_orders(as_of=_now())
        assert len(expired) == 0

    def test_oco_fill_cancels_sibling(self):
        oms = _oms()
        r = oms.create_oco("AAPL", OrderSide.SELL, 100, 185.0, 165.0)
        oms.record_fill(r.limit_order.order_id, 100, 185.0)
        stop = oms.get_order(r.stop_order.order_id)
        assert stop.status == OrderStatus.CANCELLED

    def test_get_order_by_id(self):
        oms = _oms()
        o = _sub(oms, "AAPL", OrderType.MARKET, OrderSide.BUY, 100)
        retrieved = oms.get_order(o.order_id)
        assert retrieved.order_id == o.order_id
