"""Tests for the Paper Trading Engine.

Uses the running PostgreSQL container via the conftest ``db`` fixture.
Each test runs inside a rolled-back transaction — no data persists.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from models.trading import (
    CommissionTypeEnum,
    Order,
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    PaperAccount,
)
from schemas.trading import OrderCreate
from services import oms as oms_service
from services import paper_trading as paper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_account(db, initial_cash=Decimal("100000"), slippage_bps=10) -> PaperAccount:
    return paper.create_account(
        db,
        name=f"Test Account {uuid.uuid4().hex[:6]}",
        initial_cash=initial_cash,
        commission_type=CommissionTypeEnum.FLAT,
        commission_rate=Decimal("1.00"),
        min_commission=Decimal("0"),
        slippage_bps=slippage_bps,
    )


def _market_order_create(ticker="AAPL", side="BUY", qty="100") -> OrderCreate:
    return OrderCreate(
        ticker=ticker,
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum(side),
        quantity=Decimal(qty),
    )


def _limit_order_create(ticker="AAPL", side="BUY", qty="100", limit="150") -> OrderCreate:
    return OrderCreate(
        ticker=ticker,
        order_type=OrderTypeEnum.LIMIT,
        side=OrderSideEnum(side),
        quantity=Decimal(qty),
        limit_price=Decimal(limit),
    )


def _stop_order_create(ticker="AAPL", side="SELL", qty="100", stop="145") -> OrderCreate:
    return OrderCreate(
        ticker=ticker,
        order_type=OrderTypeEnum.STOP,
        side=OrderSideEnum(side),
        quantity=Decimal(qty),
        stop_price=Decimal(stop),
    )


# ---------------------------------------------------------------------------
# TestAccountManagement
# ---------------------------------------------------------------------------


class TestAccountManagement:
    def test_create_account(self, db):
        account = _create_account(db)
        assert account.id is not None
        assert account.cash_balance == Decimal("100000")
        assert account.total_equity == Decimal("100000")
        assert account.is_active is True

    def test_get_account(self, db):
        account = _create_account(db)
        fetched = paper.get_account(db, account.id)
        assert fetched.id == account.id

    def test_get_nonexistent_returns_none(self, db):
        assert paper.get_account(db, uuid.uuid4()) is None

    def test_list_accounts_active_only(self, db):
        a1 = _create_account(db)
        a2 = _create_account(db)
        a2.is_active = False
        db.commit()
        active = paper.list_accounts(db, active_only=True)
        ids = [a.id for a in active]
        assert a1.id in ids
        assert a2.id not in ids

    def test_account_summary(self, db):
        account = _create_account(db)
        summary = paper.get_account_summary(db, account.id)
        assert summary["account"].id == account.id
        assert summary["open_orders_count"] == 0
        assert summary["total_trades"] == 0


# ---------------------------------------------------------------------------
# TestCommissionModel
# ---------------------------------------------------------------------------


class TestCommissionModel:
    def test_flat_commission(self):
        comm = paper.compute_commission(Decimal("100"), Decimal("150"), "FLAT", Decimal("1.00"), Decimal("0"))
        assert comm == Decimal("1.00")

    def test_per_share_commission(self):
        comm = paper.compute_commission(Decimal("100"), Decimal("150"), "PER_SHARE", Decimal("0.005"), Decimal("1.00"))
        # 100 * 0.005 = 0.50 → min applied → 1.00
        assert comm == Decimal("1.00")

    def test_per_share_cap_applied(self):
        # 10000 shares @ $0.005 = $50; value = 10000*$150=$1,500,000; 0.5% cap = $7,500
        comm = paper.compute_commission(Decimal("10000"), Decimal("150"), "PER_SHARE", Decimal("0.005"), Decimal("1.00"))
        assert comm == Decimal("50.00")

    def test_percent_commission(self):
        # 0.1% of $15,000 = $15
        comm = paper.compute_commission(Decimal("100"), Decimal("150"), "PERCENT", Decimal("0.001"), Decimal("0"))
        assert comm == Decimal("15.00")

    def test_slippage_cost(self):
        cost = paper.compute_slippage_cost(Decimal("100"), Decimal("150"), 10)
        # 100 * 150 * 10/10000 = 15.00
        assert cost == Decimal("15.0000")


# ---------------------------------------------------------------------------
# TestFillPriceLogic
# ---------------------------------------------------------------------------


class TestFillPriceLogic:
    def test_market_buy_slips_up(self):
        price = paper.compute_fill_price("MARKET", "BUY", Decimal("100"), None, None, 10)
        assert price > Decimal("100")

    def test_market_sell_slips_down(self):
        price = paper.compute_fill_price("MARKET", "SELL", Decimal("100"), None, None, 10)
        assert price < Decimal("100")

    def test_limit_buy_fills_when_market_below(self):
        price = paper.compute_fill_price("LIMIT", "BUY", Decimal("95"), Decimal("100"), None, 0)
        assert price is not None

    def test_limit_buy_no_fill_when_market_above(self):
        price = paper.compute_fill_price("LIMIT", "BUY", Decimal("105"), Decimal("100"), None, 0)
        assert price is None

    def test_limit_sell_fills_when_market_above(self):
        price = paper.compute_fill_price("LIMIT", "SELL", Decimal("105"), Decimal("100"), None, 0)
        assert price is not None

    def test_limit_sell_no_fill_when_market_below(self):
        price = paper.compute_fill_price("LIMIT", "SELL", Decimal("95"), Decimal("100"), None, 0)
        assert price is None

    def test_stop_buy_triggers_when_market_above_stop(self):
        price = paper.compute_fill_price("STOP", "BUY", Decimal("110"), None, Decimal("105"), 0)
        assert price is not None

    def test_stop_sell_triggers_when_market_below_stop(self):
        price = paper.compute_fill_price("STOP", "SELL", Decimal("95"), None, Decimal("100"), 0)
        assert price is not None

    def test_stop_sell_no_trigger_when_above_stop(self):
        price = paper.compute_fill_price("STOP", "SELL", Decimal("110"), None, Decimal("100"), 0)
        assert price is None

    def test_stop_limit_triggers_then_checks_limit(self):
        # stop=100 reached (market=105), limit=108; market(105) < limit(108) → fills
        price = paper.compute_fill_price("STOP_LIMIT", "BUY", Decimal("105"), Decimal("108"), Decimal("100"), 0)
        assert price is not None

    def test_stop_limit_triggered_but_limit_not_met(self):
        # stop=100 reached, but market=115 > limit=108 for a buy → no fill
        price = paper.compute_fill_price("STOP_LIMIT", "BUY", Decimal("115"), Decimal("108"), Decimal("100"), 0)
        assert price is None


# ---------------------------------------------------------------------------
# TestPaperOrderExecution
# ---------------------------------------------------------------------------


class TestPaperOrderExecution:
    def _make_order(self, db, account, oc: OrderCreate) -> Order:
        order = oms_service.create_order(db, oc, paper_account_id=account.id)
        oms_service.mark_submitted(db, order)
        return order

    def test_market_buy_fills(self, db):
        account = _create_account(db)
        oc = _market_order_create(ticker="AAPL", qty="10")
        order = self._make_order(db, account, oc)
        trade = paper.execute_paper_order(db, order, market_price=Decimal("150"))
        assert trade is not None
        assert trade.fill_price > Decimal("150") * Decimal("0.99")  # slippage applied

    def test_market_buy_reduces_cash(self, db):
        account = _create_account(db, initial_cash=Decimal("50000"))
        initial_cash = account.cash_balance
        oc = _market_order_create(qty="10")
        order = self._make_order(db, account, oc)
        paper.execute_paper_order(db, order, market_price=Decimal("100"))
        db.refresh(account)
        assert account.cash_balance < initial_cash

    def test_market_buy_creates_position(self, db):
        account = _create_account(db)
        oc = _market_order_create(ticker="NVDA", qty="5")
        order = self._make_order(db, account, oc)
        paper.execute_paper_order(db, order, market_price=Decimal("500"))
        position = paper.get_position(db, account.id, "NVDA")
        assert position is not None
        assert position.quantity == Decimal("5")

    def test_market_sell_reduces_position(self, db):
        account = _create_account(db)
        # Buy first
        buy_oc = _market_order_create(ticker="SELL_TEST", qty="20")
        buy_order = self._make_order(db, account, buy_oc)
        paper.execute_paper_order(db, buy_order, market_price=Decimal("100"))
        # Now sell
        sell_oc = _market_order_create(ticker="SELL_TEST", side="SELL", qty="10")
        sell_order = self._make_order(db, account, sell_oc)
        paper.execute_paper_order(db, sell_order, market_price=Decimal("110"))
        position = paper.get_position(db, account.id, "SELL_TEST")
        assert position.quantity == Decimal("10")

    def test_sell_computes_realized_pnl(self, db):
        account = _create_account(db)
        oc_buy = _market_order_create(ticker="PNL_TEST", qty="10")
        buy_order = self._make_order(db, account, oc_buy)
        # Buy at ~100 (no slippage)
        from unittest.mock import patch
        with patch.object(paper, "apply_slippage_to_price", side_effect=lambda price, side, bps: price):
            paper.execute_paper_order(db, buy_order, market_price=Decimal("100"))
        # Sell at 120 (no slippage)
        oc_sell = _market_order_create(ticker="PNL_TEST", side="SELL", qty="10")
        sell_order = self._make_order(db, account, oc_sell)
        with patch.object(paper, "apply_slippage_to_price", side_effect=lambda price, side, bps: price):
            trade = paper.execute_paper_order(db, sell_order, market_price=Decimal("120"))
        assert trade.realized_pnl > 0

    def test_limit_order_no_fill_when_not_triggered(self, db):
        account = _create_account(db)
        oc = _limit_order_create(ticker="LIMIT_NO_FILL", qty="10", limit="90")
        order = self._make_order(db, account, oc)
        trade = paper.execute_paper_order(db, order, market_price=Decimal("100"))
        assert trade is None  # limit buy not filled when market is above

    def test_insufficient_funds_rejects_order(self, db):
        account = _create_account(db, initial_cash=Decimal("100"))
        oc = _market_order_create(qty="100")  # would cost ~$15,000
        order = self._make_order(db, account, oc)
        trade = paper.execute_paper_order(db, order, market_price=Decimal("150"))
        assert trade is None
        db.refresh(order)
        assert order.status.value == "REJECTED"

    def test_avco_cost_basis(self, db):
        account = _create_account(db)
        # Buy 10 @ $100
        o1 = oms_service.create_order(db, _market_order_create(ticker="AVCO_TEST", qty="10"), paper_account_id=account.id)
        oms_service.mark_submitted(db, o1)
        with patch.object(paper, "apply_slippage_to_price", side_effect=lambda p, s, b: p):
            paper.execute_paper_order(db, o1, market_price=Decimal("100"))
        # Buy 10 more @ $120
        o2 = oms_service.create_order(db, _market_order_create(ticker="AVCO_TEST", qty="10"), paper_account_id=account.id)
        oms_service.mark_submitted(db, o2)
        with patch.object(paper, "apply_slippage_to_price", side_effect=lambda p, s, b: p):
            paper.execute_paper_order(db, o2, market_price=Decimal("120"))
        position = paper.get_position(db, account.id, "AVCO_TEST")
        assert position.quantity == Decimal("20")
        assert position.average_cost == Decimal("110")  # (10*100 + 10*120) / 20

    def test_list_trades_returns_history(self, db):
        account = _create_account(db)
        oc = _market_order_create(ticker="HISTORY_TEST", qty="5")
        order = self._make_order(db, account, oc)
        paper.execute_paper_order(db, order, market_price=Decimal("200"))
        trades, total = paper.list_trades(db, account.id)
        assert total >= 1
