"""M17 — Portfolio Accounting (pure Python, in-memory).

Institutional P&L engine: cash ledger, mark-to-market PnL (unrealised,
realised, daily, MTD, YTD), corporate-action handling (splits, dividends,
spin-offs), fee/commission accrual, NAV computation.

No SQLAlchemy, no external libraries — stdlib + dataclasses only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class LedgerEntryType(str, Enum):
    TRADE_BUY = "TRADE_BUY"
    TRADE_SELL = "TRADE_SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    COMMISSION = "COMMISSION"
    FEE = "FEE"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    SPLIT_ADJUSTMENT = "SPLIT_ADJUSTMENT"
    SPIN_OFF = "SPIN_OFF"
    MARGIN_CALL = "MARGIN_CALL"
    REALISED_PNL = "REALISED_PNL"


class CorporateActionType(str, Enum):
    STOCK_SPLIT = "STOCK_SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    SPIN_OFF = "SPIN_OFF"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    MERGER = "MERGER"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LedgerEntry:
    """A single cash-book entry.

    Args:
        entry_id: Unique identifier.
        entry_type: Type of cash flow event.
        amount: Dollar amount (positive = cash in, negative = cash out).
        timestamp: UTC datetime of the event.
        ticker: Associated instrument (None for deposits/withdrawals).
        description: Human-readable description.
        reference_id: Order or fill ID for trade-related entries.
    """

    entry_id: str
    entry_type: LedgerEntryType
    amount: float
    timestamp: datetime
    ticker: Optional[str] = None
    description: str = ""
    reference_id: Optional[str] = None

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "amount": round(self.amount, 4),
            "timestamp": self.timestamp.isoformat(),
            "ticker": self.ticker,
            "description": self.description,
            "reference_id": self.reference_id,
        }


@dataclass
class CorporateAction:
    """A corporate action event applied to positions.

    Args:
        action_id: Unique identifier.
        action_type: Type of corporate action.
        ticker: Affected instrument.
        ex_date: Ex-dividend / record date.
        ratio: Split ratio (e.g. 2.0 for 2-for-1 split), or per-share amount for dividends.
        new_ticker: New symbol for spin-offs and mergers.
        cash_amount: Cash component (per share dividend, spin-off cash, etc.).
        description: Free-text description.
    """

    action_id: str
    action_type: CorporateActionType
    ticker: str
    ex_date: date
    ratio: float = 1.0
    new_ticker: Optional[str] = None
    cash_amount: float = 0.0
    description: str = ""

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "ticker": self.ticker,
            "ex_date": self.ex_date.isoformat(),
            "ratio": self.ratio,
            "new_ticker": self.new_ticker,
            "cash_amount": self.cash_amount,
            "description": self.description,
        }


@dataclass
class PnLSnapshot:
    """Point-in-time P&L snapshot.

    Args:
        as_of: Reference datetime.
        cash: Current cash balance.
        unrealised_pnl: Mark-to-market gain/loss on open positions.
        realised_pnl: Booked gains/losses from closed trades.
        daily_pnl: Net P&L for the current calendar day.
        mtd_pnl: Month-to-date P&L.
        ytd_pnl: Year-to-date P&L.
        total_commissions: Cumulative commissions paid.
        total_fees: Cumulative exchange/clearing fees paid.
        nav: Net asset value = cash + market_value.
        gross_market_value: Abs sum of position market values.
        net_market_value: Algebraic sum of position market values.
    """

    as_of: datetime
    cash: float
    unrealised_pnl: float
    realised_pnl: float
    daily_pnl: float
    mtd_pnl: float
    ytd_pnl: float
    total_commissions: float
    total_fees: float
    nav: float
    gross_market_value: float
    net_market_value: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "as_of": self.as_of.isoformat(),
            "cash": round(self.cash, 4),
            "unrealised_pnl": round(self.unrealised_pnl, 4),
            "realised_pnl": round(self.realised_pnl, 4),
            "daily_pnl": round(self.daily_pnl, 4),
            "mtd_pnl": round(self.mtd_pnl, 4),
            "ytd_pnl": round(self.ytd_pnl, 4),
            "total_commissions": round(self.total_commissions, 4),
            "total_fees": round(self.total_fees, 4),
            "nav": round(self.nav, 4),
            "gross_market_value": round(self.gross_market_value, 4),
            "net_market_value": round(self.net_market_value, 4),
        }


# ---------------------------------------------------------------------------
# Portfolio Accounting Engine
# ---------------------------------------------------------------------------

import uuid as _uuid_mod


class PortfolioAccountingEngine:
    """Institutional portfolio accounting engine (pure Python, in-memory).

    Tracks the full P&L lifecycle from trade booking through corporate actions
    to final NAV computation.  Uses FIFO cost basis for realised P&L.

    All monetary values are in USD unless otherwise noted.
    """

    def __init__(self, initial_cash: float = 0.0) -> None:
        """Initialise with a starting cash balance.

        Args:
            initial_cash: Starting cash in USD.
        """
        self._cash: float = initial_cash
        self._ledger: List[LedgerEntry] = []
        self._corporate_actions: List[CorporateAction] = []

        # Per-instrument accounting
        self._cost_basis: Dict[str, float] = {}
        self._quantity: Dict[str, float] = {}

        # Realised P&L per instrument
        self._realised_pnl: Dict[str, float] = {}

        # Total commissions / fees
        self._total_commissions: float = 0.0
        self._total_fees: float = 0.0

        # Periodic PnL anchors
        self._day_start_nav: float = initial_cash
        self._month_start_nav: float = initial_cash
        self._year_start_nav: float = initial_cash
        self._last_period_date: Optional[date] = None

    # ------------------------------------------------------------------
    # Cash operations
    # ------------------------------------------------------------------

    def deposit(self, amount: float, description: str = "Deposit") -> LedgerEntry:
        """Credit cash to the account.

        Args:
            amount: USD amount to deposit (must be positive).
            description: Free-text note.

        Returns:
            Created LedgerEntry.

        Raises:
            ValueError: If amount <= 0.
        """
        if amount <= 0:
            raise ValueError("deposit amount must be positive")
        return self._add_entry(LedgerEntryType.DEPOSIT, amount, description=description)

    def withdraw(self, amount: float, description: str = "Withdrawal") -> LedgerEntry:
        """Debit cash from the account.

        Args:
            amount: USD amount to withdraw (must be positive).
            description: Free-text note.

        Returns:
            Created LedgerEntry.

        Raises:
            ValueError: If amount <= 0 or exceeds available cash.
        """
        if amount <= 0:
            raise ValueError("withdrawal amount must be positive")
        if amount > self._cash:
            raise ValueError(f"Insufficient cash: have {self._cash:.2f}, need {amount:.2f}")
        return self._add_entry(LedgerEntryType.WITHDRAWAL, -amount, description=description)

    # ------------------------------------------------------------------
    # Trade booking
    # ------------------------------------------------------------------

    def book_trade(
        self,
        ticker: str,
        side: str,
        quantity: float,
        avg_price: float,
        commission: float = 0.0,
        fees: float = 0.0,
        reference_id: Optional[str] = None,
    ) -> LedgerEntry:
        """Book a completed trade and update cash and cost basis.

        Args:
            ticker: Instrument symbol.
            side: "BUY", "BUY_TO_COVER", "SELL", or "SELL_SHORT".
            quantity: Filled quantity (positive number).
            avg_price: Volume-weighted average fill price.
            commission: Commission charged.
            fees: Exchange/clearing fees.
            reference_id: Fill or order ID for audit trail.

        Returns:
            Primary LedgerEntry for the trade.

        Raises:
            ValueError: If quantity <= 0 or avg_price <= 0.
        """
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if avg_price <= 0:
            raise ValueError("avg_price must be positive")

        is_buy = side.upper() in ("BUY", "BUY_TO_COVER")
        gross_value = quantity * avg_price
        net_cost = gross_value + commission + fees if is_buy else gross_value - commission - fees

        self._total_commissions += commission
        self._total_fees += fees

        if is_buy:
            self._cash -= gross_value + commission + fees
            prev_qty = self._quantity.get(ticker, 0.0)
            prev_cb = self._cost_basis.get(ticker, 0.0)
            new_qty = prev_qty + quantity
            self._quantity[ticker] = new_qty
            self._cost_basis[ticker] = (prev_cb * prev_qty + avg_price * quantity) / new_qty if new_qty else 0.0
            entry_type = LedgerEntryType.TRADE_BUY
            cash_delta = -(gross_value + commission + fees)
        else:
            # FIFO realised P&L
            cost = self._cost_basis.get(ticker, avg_price)
            realised = (avg_price - cost) * quantity - commission - fees
            self._realised_pnl[ticker] = self._realised_pnl.get(ticker, 0.0) + realised
            self._quantity[ticker] = max(0.0, self._quantity.get(ticker, 0.0) - quantity)
            self._cash += gross_value - commission - fees
            entry_type = LedgerEntryType.TRADE_SELL
            cash_delta = gross_value - commission - fees

        entry = self._add_entry(
            entry_type,
            cash_delta,
            ticker=ticker,
            description=f"{side.upper()} {quantity} {ticker} @ {avg_price:.4f}",
            reference_id=reference_id,
        )

        if commission > 0:
            self._add_entry(LedgerEntryType.COMMISSION, -commission, ticker=ticker,
                           description=f"Commission for {reference_id or ticker}")
        if fees > 0:
            self._add_entry(LedgerEntryType.FEE, -fees, ticker=ticker,
                           description=f"Fees for {reference_id or ticker}")

        return entry

    # ------------------------------------------------------------------
    # Corporate actions
    # ------------------------------------------------------------------

    def apply_split(
        self,
        ticker: str,
        ratio: float,
        action_id: Optional[str] = None,
        ex_date: Optional[date] = None,
    ) -> CorporateAction:
        """Apply a stock split (or reverse split if ratio < 1).

        Args:
            ticker: Instrument symbol.
            ratio: Split ratio (e.g. 2.0 for 2-for-1, 0.5 for reverse 1-for-2).
            action_id: Optional identifier for the corporate action.
            ex_date: Ex-date; defaults to today.

        Returns:
            Applied CorporateAction record.

        Raises:
            ValueError: If ratio <= 0.
        """
        if ratio <= 0:
            raise ValueError("split ratio must be positive")
        aid = action_id or str(_uuid_mod.uuid4())
        exd = ex_date or datetime.now(timezone.utc).date()
        action_type = CorporateActionType.STOCK_SPLIT if ratio >= 1.0 else CorporateActionType.REVERSE_SPLIT
        ca = CorporateAction(
            action_id=aid,
            action_type=action_type,
            ticker=ticker,
            ex_date=exd,
            ratio=ratio,
            description=f"Split {ratio}:1 for {ticker}",
        )
        if ticker in self._quantity:
            self._quantity[ticker] *= ratio
            if ratio != 0:
                self._cost_basis[ticker] = self._cost_basis.get(ticker, 0.0) / ratio
        self._corporate_actions.append(ca)
        self._add_entry(
            LedgerEntryType.SPLIT_ADJUSTMENT, 0.0,
            ticker=ticker,
            description=ca.description,
            reference_id=aid,
        )
        return ca

    def apply_cash_dividend(
        self,
        ticker: str,
        per_share_amount: float,
        action_id: Optional[str] = None,
        ex_date: Optional[date] = None,
    ) -> CorporateAction:
        """Credit a cash dividend to the account.

        Args:
            ticker: Instrument paying the dividend.
            per_share_amount: Dividend per share in USD.
            action_id: Optional identifier.
            ex_date: Ex-dividend date.

        Returns:
            Applied CorporateAction record.

        Raises:
            ValueError: If per_share_amount <= 0.
        """
        if per_share_amount <= 0:
            raise ValueError("per_share_amount must be positive")
        aid = action_id or str(_uuid_mod.uuid4())
        exd = ex_date or datetime.now(timezone.utc).date()
        qty = self._quantity.get(ticker, 0.0)
        total_div = qty * per_share_amount
        ca = CorporateAction(
            action_id=aid,
            action_type=CorporateActionType.CASH_DIVIDEND,
            ticker=ticker,
            ex_date=exd,
            cash_amount=per_share_amount,
            description=f"Cash dividend ${per_share_amount:.4f}/share for {ticker}",
        )
        self._corporate_actions.append(ca)
        if total_div > 0:
            self._add_entry(
                LedgerEntryType.DIVIDEND,
                total_div,
                ticker=ticker,
                description=ca.description,
                reference_id=aid,
            )
        return ca

    def apply_spin_off(
        self,
        parent_ticker: str,
        child_ticker: str,
        shares_per_parent: float,
        child_cost_basis: float,
        action_id: Optional[str] = None,
        ex_date: Optional[date] = None,
    ) -> CorporateAction:
        """Apply a spin-off, issuing shares in a new child entity.

        Args:
            parent_ticker: Parent company symbol.
            child_ticker: Spun-off entity symbol.
            shares_per_parent: Number of child shares received per parent share.
            child_cost_basis: Cost basis per child share (allocated from parent).
            action_id: Optional identifier.
            ex_date: Record/ex date.

        Returns:
            Applied CorporateAction record.
        """
        aid = action_id or str(_uuid_mod.uuid4())
        exd = ex_date or datetime.now(timezone.utc).date()
        parent_qty = self._quantity.get(parent_ticker, 0.0)
        child_qty = parent_qty * shares_per_parent
        ca = CorporateAction(
            action_id=aid,
            action_type=CorporateActionType.SPIN_OFF,
            ticker=parent_ticker,
            new_ticker=child_ticker,
            ex_date=exd,
            ratio=shares_per_parent,
            description=f"Spin-off {child_ticker} from {parent_ticker}, {shares_per_parent} shares/parent share",
        )
        self._corporate_actions.append(ca)
        if child_qty > 0:
            self._quantity[child_ticker] = self._quantity.get(child_ticker, 0.0) + child_qty
            self._cost_basis[child_ticker] = child_cost_basis
            self._add_entry(
                LedgerEntryType.SPIN_OFF,
                0.0,
                ticker=child_ticker,
                description=ca.description,
                reference_id=aid,
            )
        return ca

    # ------------------------------------------------------------------
    # Interest accrual
    # ------------------------------------------------------------------

    def accrue_interest(self, amount: float, description: str = "Interest income") -> LedgerEntry:
        """Credit interest income to cash.

        Args:
            amount: Interest amount in USD.
            description: Description of the interest source.

        Returns:
            Created LedgerEntry.
        """
        return self._add_entry(LedgerEntryType.INTEREST, amount, description=description)

    def charge_borrow_cost(self, ticker: str, amount: float) -> LedgerEntry:
        """Charge securities borrow cost for short positions.

        Args:
            ticker: Shorted instrument.
            amount: Borrow cost in USD (positive number, will be debited).

        Returns:
            Created LedgerEntry.
        """
        debit = abs(amount)
        self._cash -= debit
        self._total_fees += debit
        return self._add_entry(
            LedgerEntryType.FEE,
            -debit,
            ticker=ticker,
            description=f"Borrow cost for short {ticker}",
        )

    # ------------------------------------------------------------------
    # Mark-to-market & NAV
    # ------------------------------------------------------------------

    def mark_to_market(self, prices: Dict[str, float]) -> Dict[str, float]:
        """Compute unrealised P&L for all open positions.

        Args:
            prices: Dict mapping ticker → current market price.

        Returns:
            Dict mapping ticker → unrealised_pnl.
        """
        result: Dict[str, float] = {}
        for ticker, qty in self._quantity.items():
            if qty == 0.0:
                result[ticker] = 0.0
                continue
            px = prices.get(ticker)
            if px is None:
                result[ticker] = 0.0
                continue
            cb = self._cost_basis.get(ticker, 0.0)
            result[ticker] = (px - cb) * qty
        return result

    def nav(self, prices: Dict[str, float]) -> float:
        """Compute Net Asset Value = cash + sum(position × price).

        Args:
            prices: Dict mapping ticker → current market price.

        Returns:
            NAV in USD.
        """
        market_value = sum(
            qty * prices.get(ticker, 0.0)
            for ticker, qty in self._quantity.items()
        )
        return self._cash + market_value

    def snapshot(
        self,
        prices: Dict[str, float],
        as_of: Optional[datetime] = None,
    ) -> PnLSnapshot:
        """Generate a full P&L snapshot.

        Args:
            prices: Current market prices.
            as_of: Reference timestamp; defaults to now.

        Returns:
            PnLSnapshot with all P&L components.
        """
        now = as_of or datetime.now(timezone.utc)
        unrealised_by_ticker = self.mark_to_market(prices)
        unrealised_total = sum(unrealised_by_ticker.values())
        realised_total = sum(self._realised_pnl.values())

        market_values = [
            qty * prices.get(ticker, 0.0)
            for ticker, qty in self._quantity.items()
        ]
        gross_mv = sum(abs(v) for v in market_values)
        net_mv = sum(market_values)
        current_nav = self._cash + net_mv

        daily_pnl = current_nav - self._day_start_nav
        mtd_pnl = current_nav - self._month_start_nav
        ytd_pnl = current_nav - self._year_start_nav

        return PnLSnapshot(
            as_of=now,
            cash=self._cash,
            unrealised_pnl=unrealised_total,
            realised_pnl=realised_total,
            daily_pnl=daily_pnl,
            mtd_pnl=mtd_pnl,
            ytd_pnl=ytd_pnl,
            total_commissions=self._total_commissions,
            total_fees=self._total_fees,
            nav=current_nav,
            gross_market_value=gross_mv,
            net_market_value=net_mv,
        )

    # ------------------------------------------------------------------
    # Period resets
    # ------------------------------------------------------------------

    def reset_day(self, prices: Dict[str, float]) -> None:
        """Record the start-of-day NAV for daily P&L computation.

        Args:
            prices: Current prices for mark-to-market.
        """
        self._day_start_nav = self.nav(prices)

    def reset_month(self, prices: Dict[str, float]) -> None:
        """Record the start-of-month NAV for MTD P&L computation.

        Args:
            prices: Current prices for mark-to-market.
        """
        self._month_start_nav = self.nav(prices)

    def reset_year(self, prices: Dict[str, float]) -> None:
        """Record the start-of-year NAV for YTD P&L computation.

        Args:
            prices: Current prices for mark-to-market.
        """
        self._year_start_nav = self.nav(prices)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def cash(self) -> float:
        """Current cash balance."""
        return self._cash

    def position_qty(self, ticker: str) -> float:
        """Return current position size for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            Quantity (positive = long, negative = short, 0 = flat).
        """
        return self._quantity.get(ticker, 0.0)

    def cost_basis(self, ticker: str) -> float:
        """Return average cost basis per share for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            Average cost basis per share.
        """
        return self._cost_basis.get(ticker, 0.0)

    def realised_pnl(self, ticker: Optional[str] = None) -> float:
        """Return realised P&L for a ticker or across all positions.

        Args:
            ticker: If provided, return P&L for this ticker only; else total.

        Returns:
            Realised P&L in USD.
        """
        if ticker:
            return self._realised_pnl.get(ticker, 0.0)
        return sum(self._realised_pnl.values())

    def get_ledger(self, ticker: Optional[str] = None) -> List[LedgerEntry]:
        """Return ledger entries, optionally filtered by ticker.

        Args:
            ticker: Instrument filter.

        Returns:
            List of LedgerEntry sorted by timestamp.
        """
        entries = self._ledger
        if ticker:
            entries = [e for e in entries if e.ticker == ticker]
        return sorted(entries, key=lambda e: e.timestamp)

    def get_corporate_actions(self, ticker: Optional[str] = None) -> List[CorporateAction]:
        """Return corporate actions, optionally filtered by ticker.

        Args:
            ticker: Instrument filter.

        Returns:
            List of CorporateAction sorted by ex_date.
        """
        actions = self._corporate_actions
        if ticker:
            actions = [a for a in actions if a.ticker == ticker or a.new_ticker == ticker]
        return sorted(actions, key=lambda a: a.ex_date)

    def all_positions(self) -> Dict[str, float]:
        """Return all non-zero positions.

        Returns:
            Dict mapping ticker → quantity.
        """
        return {t: q for t, q in self._quantity.items() if q != 0.0}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_entry(
        self,
        entry_type: LedgerEntryType,
        amount: float,
        *,
        ticker: Optional[str] = None,
        description: str = "",
        reference_id: Optional[str] = None,
    ) -> LedgerEntry:
        entry = LedgerEntry(
            entry_id=str(_uuid_mod.uuid4()),
            entry_type=entry_type,
            amount=amount,
            timestamp=datetime.now(timezone.utc),
            ticker=ticker,
            description=description,
            reference_id=reference_id,
        )
        if entry_type not in (
            LedgerEntryType.COMMISSION, LedgerEntryType.FEE,
            LedgerEntryType.SPLIT_ADJUSTMENT, LedgerEntryType.SPIN_OFF,
        ):
            # Only direct-cash entries adjust the running balance
            # (commission / fees are already accounted for in book_trade)
            if entry_type in (LedgerEntryType.DIVIDEND, LedgerEntryType.INTEREST,
                              LedgerEntryType.DEPOSIT):
                self._cash += amount
            elif entry_type == LedgerEntryType.WITHDRAWAL:
                self._cash += amount  # amount is already negative
            elif entry_type in (LedgerEntryType.TRADE_BUY, LedgerEntryType.TRADE_SELL):
                pass  # cash adjusted in book_trade directly
        self._ledger.append(entry)
        return entry


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_portfolio_accounting: Optional[PortfolioAccountingEngine] = None


def get_portfolio_accounting_engine() -> PortfolioAccountingEngine:
    """Return the singleton PortfolioAccountingEngine instance.

    Returns:
        Shared PortfolioAccountingEngine instance.
    """
    global _default_portfolio_accounting
    if _default_portfolio_accounting is None:
        _default_portfolio_accounting = PortfolioAccountingEngine()
    return _default_portfolio_accounting
