"""Tests for the Order Management System (OMS).

Uses the running PostgreSQL container via the conftest ``db``, ``test_portfolio``,
and ``test_paper_account`` fixtures. Each test runs inside a rolled-back transaction.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from models.trading import (
    AuditEventEnum,
    LinkTypeEnum,
    Order,
    OrderAuditLog,
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    TimeInForceEnum,
)
from schemas.trading import OrderCreate, OrderModify
from services import oms as oms_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _market_order(ticker="AAPL", side="BUY", qty="100") -> OrderCreate:
    return OrderCreate(
        ticker=ticker,
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum(side),
        quantity=Decimal(qty),
    )


def _limit_order(ticker="AAPL", side="BUY", qty="100", limit="150.00") -> OrderCreate:
    return OrderCreate(
        ticker=ticker,
        order_type=OrderTypeEnum.LIMIT,
        side=OrderSideEnum(side),
        quantity=Decimal(qty),
        limit_price=Decimal(limit),
    )


# ---------------------------------------------------------------------------
# TestOrderCreation
# ---------------------------------------------------------------------------


class TestOrderCreation:
    def test_create_market_order(self, db, test_portfolio):
        oc = _market_order()
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        assert order.id is not None
        assert order.ticker == "AAPL"
        assert order.quantity == Decimal("100")
        assert order.status.value == "PENDING"
        assert order.filled_quantity == Decimal("0")

    def test_create_limit_order(self, db, test_portfolio):
        oc = _limit_order()
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        assert order.limit_price == Decimal("150.00")
        assert order.order_type.value == "LIMIT"

    def test_create_order_writes_audit_log(self, db, test_portfolio):
        oc = _market_order(ticker="MSFT")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        logs = oms_service.get_audit_log(db, order.id)
        assert len(logs) >= 1
        assert logs[0].event_type.value == AuditEventEnum.CREATED.value

    def test_ticker_uppercased(self, db, test_portfolio):
        oc = OrderCreate(
            ticker="aapl",
            order_type=OrderTypeEnum.MARKET,
            side=OrderSideEnum.BUY,
            quantity=Decimal("10"),
        )
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        assert order.ticker == "AAPL"

    def test_create_with_paper_account(self, db, test_paper_account):
        oc = _market_order()
        order = oms_service.create_order(db, oc, paper_account_id=test_paper_account.id)
        assert order.paper_account_id == test_paper_account.id
        assert order.portfolio_id is None


# ---------------------------------------------------------------------------
# TestOrderRetrieval
# ---------------------------------------------------------------------------


class TestOrderRetrieval:
    def test_get_existing_order(self, db, test_portfolio):
        oc = _market_order(ticker="NVDA")
        created = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        fetched = oms_service.get_order(db, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_nonexistent_order_returns_none(self, db):
        result = oms_service.get_order(db, uuid.uuid4())
        assert result is None

    def test_list_orders_by_portfolio(self, db, test_portfolio):
        for ticker in ["AAPL", "GOOG", "TSLA"]:
            oms_service.create_order(db, _market_order(ticker=ticker), portfolio_id=test_portfolio.id)
        orders, total = oms_service.list_orders(db, portfolio_id=test_portfolio.id)
        assert total >= 3
        assert len(orders) >= 3

    def test_list_orders_by_status(self, db, test_portfolio):
        oms_service.create_order(db, _market_order(ticker="IBM"), portfolio_id=test_portfolio.id)
        orders, total = oms_service.list_orders(db, portfolio_id=test_portfolio.id, status="PENDING")
        assert total >= 1

    def test_list_orders_pagination(self, db, test_portfolio):
        for i in range(5):
            oms_service.create_order(db, _market_order(ticker=f"T{i:02d}"), portfolio_id=test_portfolio.id)
        orders, total = oms_service.list_orders(db, portfolio_id=test_portfolio.id, page=1, page_size=2)
        assert len(orders) == 2
        assert total >= 5


# ---------------------------------------------------------------------------
# TestOrderModification
# ---------------------------------------------------------------------------


class TestOrderModification:
    def test_modify_quantity(self, db, test_portfolio):
        oc = _limit_order()
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        modified = oms_service.modify_order(db, order.id, OrderModify(quantity=Decimal("200")))
        assert modified.quantity == Decimal("200")

    def test_modify_limit_price(self, db, test_portfolio):
        oc = _limit_order(limit="100.00")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        modified = oms_service.modify_order(db, order.id, OrderModify(limit_price=Decimal("120.00")))
        assert modified.limit_price == Decimal("120.00")

    def test_modify_writes_audit_event(self, db, test_portfolio):
        oc = _limit_order()
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        oms_service.modify_order(db, order.id, OrderModify(quantity=Decimal("50")))
        logs = oms_service.get_audit_log(db, order.id)
        event_types = [e.event_type.value for e in logs]
        assert AuditEventEnum.MODIFIED.value in event_types

    def test_modify_nonexistent_raises(self, db):
        with pytest.raises(ValueError, match="not found"):
            oms_service.modify_order(db, uuid.uuid4(), OrderModify(quantity=Decimal("10")))

    def test_modify_filled_order_raises(self, db, test_portfolio):
        oc = _market_order()
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        order.status = OrderStatusEnum.FILLED
        db.flush()
        with pytest.raises(ValueError):
            oms_service.modify_order(db, order.id, OrderModify(quantity=Decimal("10")))


# ---------------------------------------------------------------------------
# TestOrderCancellation
# ---------------------------------------------------------------------------


class TestOrderCancellation:
    def test_cancel_pending_order(self, db, test_portfolio):
        oc = _market_order(ticker="CANCELLED_TEST")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        cancelled = oms_service.cancel_order(db, order.id, reason="Test cancel")
        assert cancelled.status.value == "CANCELLED"
        assert cancelled.cancelled_at is not None

    def test_cancel_writes_audit_events(self, db, test_portfolio):
        oc = _market_order(ticker="AUDIT_CANCEL")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        oms_service.cancel_order(db, order.id)
        logs = oms_service.get_audit_log(db, order.id)
        event_types = [e.event_type.value for e in logs]
        assert AuditEventEnum.CANCELLED.value in event_types

    def test_cancel_filled_raises(self, db, test_portfolio):
        oc = _market_order()
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        order.status = OrderStatusEnum.FILLED
        db.flush()
        with pytest.raises(ValueError):
            oms_service.cancel_order(db, order.id)

    def test_cancel_nonexistent_raises(self, db):
        with pytest.raises(ValueError, match="not found"):
            oms_service.cancel_order(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# TestOrderValidation
# ---------------------------------------------------------------------------


class TestOrderValidation:
    def test_market_order_valid(self):
        oc = _market_order()
        is_valid, errors = oms_service.validate_order(oc, Decimal("50000"), Decimal("150"))
        assert is_valid
        assert errors == []

    def test_limit_market_is_valid(self):
        oc = OrderCreate(
            ticker="AAPL",
            order_type=OrderTypeEnum.MARKET,
            side=OrderSideEnum.BUY,
            quantity=Decimal("1"),
        )
        is_valid, errors = oms_service.validate_order(oc, Decimal("10000"), Decimal("150"))
        assert is_valid

    def test_insufficient_buying_power(self):
        oc = _market_order(qty="10000")
        is_valid, errors = oms_service.validate_order(oc, Decimal("100"), Decimal("200"))
        assert not is_valid
        assert any("Insufficient" in e for e in errors)

    def test_negative_quantity_invalid(self):
        with pytest.raises(Exception):  # pydantic validation
            OrderCreate(
                ticker="AAPL",
                order_type=OrderTypeEnum.MARKET,
                side=OrderSideEnum.BUY,
                quantity=Decimal("-1"),
            )


# ---------------------------------------------------------------------------
# TestOrderSimulation
# ---------------------------------------------------------------------------


class TestOrderSimulation:
    def test_simulate_market_order(self):
        oc = _market_order(qty="100")
        result = oms_service.simulate_order(oc, market_price=Decimal("150"))
        assert result["market_price"] == Decimal("150")
        assert result["is_valid"] is True
        assert result["estimated_commission"] > 0

    def test_simulate_limit_order_price(self):
        oc = _limit_order(limit="145.00")
        result = oms_service.simulate_order(oc, market_price=Decimal("150"))
        assert result["estimated_price"] == Decimal("145.00")

    def test_simulate_buy_has_buying_power(self):
        oc = _market_order(side="BUY", qty="100")
        result = oms_service.simulate_order(oc, market_price=Decimal("150"))
        assert result["buying_power_required"] is not None
        assert result["buying_power_required"] > 0

    def test_simulate_sell_no_buying_power(self):
        oc = _market_order(side="SELL", qty="100")
        result = oms_service.simulate_order(oc, market_price=Decimal("150"))
        assert result["buying_power_required"] is None


# ---------------------------------------------------------------------------
# TestMarkSubmitted
# ---------------------------------------------------------------------------


class TestMarkSubmitted:
    def test_mark_submitted_changes_status(self, db, test_portfolio):
        oc = _market_order(ticker="SUBMIT_TEST")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        submitted = oms_service.mark_submitted(db, order)
        assert submitted.status.value == "SUBMITTED"
        assert submitted.submitted_at is not None

    def test_mark_submitted_with_broker_id(self, db, test_portfolio):
        oc = _market_order(ticker="BROKER_ID_TEST")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        submitted = oms_service.mark_submitted(db, order, broker_order_id="EXT-123456")
        assert submitted.broker_order_id == "EXT-123456"


# ---------------------------------------------------------------------------
# TestPartialFill
# ---------------------------------------------------------------------------


class TestPartialFill:
    def test_partial_fill_updates_quantity(self, db, test_portfolio):
        oc = _market_order(qty="100")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        oms_service.mark_submitted(db, order)
        oms_service.record_partial_fill(
            db, order,
            fill_qty=Decimal("50"),
            fill_price=Decimal("150"),
            commission=Decimal("1"),
            slippage=Decimal("0.01"),
        )
        db.refresh(order)
        assert order.filled_quantity == Decimal("50")
        assert order.status.value == "PARTIALLY_FILLED"

    def test_full_fill_marks_filled(self, db, test_portfolio):
        oc = _market_order(qty="100")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        oms_service.mark_submitted(db, order)
        oms_service.record_partial_fill(
            db, order,
            fill_qty=Decimal("100"),
            fill_price=Decimal("155"),
            commission=Decimal("1"),
            slippage=Decimal("0.01"),
        )
        db.refresh(order)
        assert order.status.value == "FILLED"
        assert order.filled_at is not None

    def test_average_fill_price_calculated(self, db, test_portfolio):
        oc = _market_order(qty="100")
        order = oms_service.create_order(db, oc, portfolio_id=test_portfolio.id)
        oms_service.record_partial_fill(db, order, Decimal("50"), Decimal("150"), Decimal("0.5"), Decimal("0"))
        oms_service.record_partial_fill(db, order, Decimal("50"), Decimal("160"), Decimal("0.5"), Decimal("0"))
        db.refresh(order)
        assert order.average_fill_price == Decimal("155")


# ---------------------------------------------------------------------------
# TestBasketOrders
# ---------------------------------------------------------------------------


class TestBasketOrders:
    def test_create_basket_assigns_same_basket_id(self, db, test_portfolio):
        items = [_market_order(ticker=t) for t in ["AAPL", "MSFT", "GOOG"]]
        basket_id, orders = oms_service.create_basket_order(db, items, portfolio_id=test_portfolio.id)
        assert all(o.basket_id == basket_id for o in orders)
        assert len(orders) == 3

    def test_list_basket_orders(self, db, test_portfolio):
        items = [_market_order(ticker="META"), _market_order(ticker="AMZN")]
        basket_id, _ = oms_service.create_basket_order(db, items, portfolio_id=test_portfolio.id)
        basket_orders = oms_service.list_basket_orders(db, basket_id)
        assert len(basket_orders) == 2
