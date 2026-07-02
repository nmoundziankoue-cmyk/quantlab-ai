"""Tests for M17 Portfolio Accounting Engine."""
import pytest
from services.portfolio_accounting import (
    PortfolioAccountingEngine, LedgerEntryType, CorporateActionType,
    LedgerEntry, PnLSnapshot,
)


def _eng():
    return PortfolioAccountingEngine()


# ---------------------------------------------------------------------------
# deposit / withdraw
# ---------------------------------------------------------------------------

class TestCashOperations:
    def test_deposit_increases_cash(self):
        e = _eng()
        e.deposit(1_000_000, "Initial deposit")
        assert e.nav({}) == pytest.approx(1_000_000.0, rel=1e-6)

    def test_multiple_deposits_accumulate(self):
        e = _eng()
        e.deposit(500_000, "First")
        e.deposit(250_000, "Second")
        assert e.nav({}) == pytest.approx(750_000.0, rel=1e-6)

    def test_withdraw_decreases_cash(self):
        e = _eng()
        e.deposit(1_000_000, "Init")
        e.withdraw(100_000, "Withdrawal")
        assert e.nav({}) == pytest.approx(900_000.0, rel=1e-6)

    def test_withdraw_more_than_cash_raises(self):
        e = _eng()
        e.deposit(100_000, "Init")
        with pytest.raises((ValueError, RuntimeError)):
            e.withdraw(200_000, "Overdraft")

    def test_deposit_returns_ledger_entry(self):
        e = _eng()
        entry = e.deposit(100_000, "Test")
        assert isinstance(entry, LedgerEntry)

    def test_withdraw_returns_ledger_entry(self):
        e = _eng()
        e.deposit(100_000, "Init")
        entry = e.withdraw(50_000, "Test")
        assert isinstance(entry, LedgerEntry)

    def test_deposit_entry_type(self):
        e = _eng()
        entry = e.deposit(100_000, "Test")
        assert entry.entry_type == LedgerEntryType.DEPOSIT

    def test_withdraw_entry_type(self):
        e = _eng()
        e.deposit(200_000, "Init")
        entry = e.withdraw(50_000, "Test")
        assert entry.entry_type == LedgerEntryType.WITHDRAWAL

    def test_deposit_negative_raises(self):
        e = _eng()
        with pytest.raises(ValueError):
            e.deposit(-100, "Bad")

    def test_withdraw_negative_raises(self):
        e = _eng()
        e.deposit(100_000, "Init")
        with pytest.raises(ValueError):
            e.withdraw(-100, "Bad")


# ---------------------------------------------------------------------------
# book_trade
# ---------------------------------------------------------------------------

class TestBookTrade:
    def test_buy_reduces_cash_by_notional(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=0.0)
        snap = e.snapshot({"AAPL": 175.0})
        assert snap.cash == pytest.approx(500_000 - 100 * 175.0, rel=1e-5)

    def test_sell_increases_cash(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=0.0)
        e.book_trade("AAPL", "SELL", 100, 180.0, commission=0.0)
        snap = e.snapshot({})
        assert snap.cash > 500_000 - 100 * 175.0

    def test_book_trade_realised_pnl_on_sell(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 170.0, commission=0.0)
        e.book_trade("AAPL", "SELL", 100, 180.0, commission=0.0)
        snap = e.snapshot({})
        assert snap.realised_pnl == pytest.approx(1000.0, rel=1e-5)

    def test_book_trade_commission_tracked(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=5.0)
        snap = e.snapshot({"AAPL": 175.0})
        assert snap.total_commissions == pytest.approx(5.0, rel=1e-5)

    def test_book_trade_multiple_tickers(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=0.0)
        e.book_trade("MSFT", "BUY", 50, 420.0, commission=0.0)
        nav = e.nav({"AAPL": 175.0, "MSFT": 420.0})
        assert nav == pytest.approx(500_000.0, rel=1e-5)

    def test_buy_position_tracked(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=0.0)
        nav = e.nav({"AAPL": 200.0})
        assert nav > 500_000.0


# ---------------------------------------------------------------------------
# mark_to_market / NAV
# ---------------------------------------------------------------------------

class TestMarkToMarket:
    def test_nav_with_long_position_above_cost(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 170.0, commission=0.0)
        nav = e.nav({"AAPL": 180.0})
        assert nav > 500_000

    def test_nav_with_long_position_below_cost(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 180.0, commission=0.0)
        nav = e.nav({"AAPL": 170.0})
        assert nav < 500_000

    def test_mark_to_market_unrealised_pnl(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 170.0, commission=0.0)
        snap = e.snapshot({"AAPL": 180.0})
        assert snap.unrealised_pnl == pytest.approx(1000.0, rel=1e-5)

    def test_nav_no_positions_equals_cash(self):
        e = _eng()
        e.deposit(1_000_000, "Init")
        assert e.nav({}) == pytest.approx(1_000_000.0)

    def test_snapshot_nav_field(self):
        e = _eng()
        e.deposit(500_000, "Init")
        snap = e.snapshot({})
        assert snap.nav == pytest.approx(500_000.0)


# ---------------------------------------------------------------------------
# corporate actions
# ---------------------------------------------------------------------------

class TestCorporateActions:
    def test_split_doubles_quantity(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 200.0, commission=0.0)
        e.apply_split("AAPL", 2.0)
        nav = e.nav({"AAPL": 100.0})
        assert nav == pytest.approx(500_000 - 100 * 200.0 + 200 * 100.0, rel=1e-5)

    def test_cash_dividend_increases_cash(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=0.0)
        e.apply_cash_dividend("AAPL", 0.25)
        snap = e.snapshot({"AAPL": 175.0})
        assert snap.cash == pytest.approx(500_000 - 100 * 175.0 + 100 * 0.25, rel=1e-5)

    def test_cash_dividend_tracked_in_ledger(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=0.0)
        e.apply_cash_dividend("AAPL", 0.25)
        snap = e.snapshot({"AAPL": 175.0})
        assert snap is not None

    def test_apply_spin_off(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=0.0)
        e.apply_spin_off("AAPL", "SPUN", 0.1, 20.0)
        snap = e.snapshot({"AAPL": 175.0, "SPUN": 20.0})
        assert snap is not None


# ---------------------------------------------------------------------------
# accruals / borrow cost
# ---------------------------------------------------------------------------

class TestAccruals:
    def test_accrue_interest_increases_cash(self):
        e = _eng()
        e.deposit(1_000_000, "Init")
        initial_nav = e.nav({})
        e.accrue_interest(1000.0, "Monthly interest")
        assert e.nav({}) == pytest.approx(initial_nav + 1000.0, rel=1e-6)

    def test_charge_borrow_cost_decreases_cash(self):
        e = _eng()
        e.deposit(500_000, "Init")
        initial_cash = e.nav({})
        e.charge_borrow_cost("AAPL", 50.0)
        assert e.nav({}) == pytest.approx(initial_cash - 50.0, rel=1e-6)


# ---------------------------------------------------------------------------
# snapshot / reset
# ---------------------------------------------------------------------------

class TestSnapshotAndReset:
    def test_snapshot_returns_pnl_snapshot(self):
        e = _eng()
        e.deposit(500_000, "Init")
        snap = e.snapshot({})
        assert isinstance(snap, PnLSnapshot)

    def test_snapshot_cash_correct(self):
        e = _eng()
        e.deposit(500_000, "Init")
        snap = e.snapshot({})
        assert snap.cash == pytest.approx(500_000.0)

    def test_reset_day_zeros_day_pnl(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.reset_day({})
        snap = e.snapshot({})
        assert snap.daily_pnl == pytest.approx(0.0)

    def test_reset_month_zeros_month_pnl(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.reset_month({})
        snap = e.snapshot({})
        assert snap.mtd_pnl == pytest.approx(0.0)

    def test_snapshot_total_commissions(self):
        e = _eng()
        e.deposit(500_000, "Init")
        e.book_trade("AAPL", "BUY", 100, 175.0, commission=5.0)
        e.book_trade("MSFT", "BUY", 50, 420.0, commission=3.0)
        snap = e.snapshot({"AAPL": 175.0, "MSFT": 420.0})
        assert snap.total_commissions == pytest.approx(8.0, rel=1e-5)
