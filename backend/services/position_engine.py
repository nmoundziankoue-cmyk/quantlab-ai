"""M17 — Position Engine (pure Python, in-memory).

Institutional position management: long/short tracking, FIFO / LIFO /
specific-lot cost basis, average cost, exposure, leverage, position aging,
open/closed/historical snapshots.

No SQLAlchemy, no external libraries — stdlib + dataclasses only.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CostBasisMethod(str, Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"
    AVERAGE_COST = "AVERAGE_COST"
    SPECIFIC_LOT = "SPECIFIC_LOT"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Lot:
    """A single acquisition lot (one buy trade).

    Args:
        lot_id: Unique lot identifier.
        ticker: Instrument symbol.
        quantity: Quantity in this lot (positive).
        cost_per_share: Per-share cost at acquisition.
        acquired_date: Date of acquisition.
        acquired_datetime: Full UTC datetime of acquisition.
        remaining_quantity: Quantity not yet disposed.
        is_closed: True when the entire lot has been disposed.
    """

    lot_id: str
    ticker: str
    quantity: float
    cost_per_share: float
    acquired_date: date
    acquired_datetime: datetime
    remaining_quantity: float = 0.0
    is_closed: bool = False

    def __post_init__(self) -> None:
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = self.quantity

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "lot_id": self.lot_id,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "cost_per_share": round(self.cost_per_share, 6),
            "acquired_date": self.acquired_date.isoformat(),
            "acquired_datetime": self.acquired_datetime.isoformat(),
            "remaining_quantity": self.remaining_quantity,
            "is_closed": self.is_closed,
            "total_cost": round(self.quantity * self.cost_per_share, 4),
        }


@dataclass
class ClosedLot:
    """A disposed lot portion (partial or full close).

    Args:
        close_id: Unique identifier.
        lot_id: Source lot identifier.
        ticker: Instrument.
        quantity: Disposed quantity.
        cost_per_share: Per-share cost basis.
        proceeds_per_share: Sell price per share.
        realised_pnl: (proceeds - cost) * quantity.
        opened_date: Original acquisition date.
        closed_datetime: Close datetime.
        holding_days: Number of calendar days held.
    """

    close_id: str
    lot_id: str
    ticker: str
    quantity: float
    cost_per_share: float
    proceeds_per_share: float
    realised_pnl: float
    opened_date: date
    closed_datetime: datetime
    holding_days: int

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "close_id": self.close_id,
            "lot_id": self.lot_id,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "cost_per_share": round(self.cost_per_share, 6),
            "proceeds_per_share": round(self.proceeds_per_share, 6),
            "realised_pnl": round(self.realised_pnl, 4),
            "opened_date": self.opened_date.isoformat(),
            "closed_datetime": self.closed_datetime.isoformat(),
            "holding_days": self.holding_days,
        }


@dataclass
class Position:
    """Aggregated position view for an instrument.

    Args:
        ticker: Instrument symbol.
        side: LONG, SHORT, or FLAT.
        quantity: Net signed quantity (positive=long, negative=short, 0=flat).
        avg_cost: Average cost per share (AVCO of open lots).
        market_price: Latest market price used for MTM.
        unrealised_pnl: mark-to-market gain/loss.
        market_value: quantity * market_price.
        open_lots: Number of open acquisition lots.
        oldest_lot_date: Acquisition date of the oldest open lot.
        holding_days: Calendar days the position has been held (oldest lot).
    """

    ticker: str
    side: PositionSide
    quantity: float
    avg_cost: float
    market_price: float
    unrealised_pnl: float
    market_value: float
    open_lots: int
    oldest_lot_date: Optional[date]
    holding_days: int

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "side": self.side.value,
            "quantity": self.quantity,
            "avg_cost": round(self.avg_cost, 6),
            "market_price": self.market_price,
            "unrealised_pnl": round(self.unrealised_pnl, 4),
            "market_value": round(self.market_value, 4),
            "open_lots": self.open_lots,
            "oldest_lot_date": self.oldest_lot_date.isoformat() if self.oldest_lot_date else None,
            "holding_days": self.holding_days,
        }


@dataclass
class ExposureReport:
    """Portfolio exposure and leverage summary.

    Args:
        gross_exposure: Abs sum of all position market values.
        net_exposure: Algebraic sum (long_mv - abs(short_mv)).
        long_exposure: Total long market value.
        short_exposure: Total absolute short market value.
        leverage: gross_exposure / nav.
        net_leverage: abs(net_exposure) / nav.
        nav: Net asset value used for leverage computation.
        position_count: Number of non-flat positions.
        long_count: Number of long positions.
        short_count: Number of short positions.
    """

    gross_exposure: float
    net_exposure: float
    long_exposure: float
    short_exposure: float
    leverage: float
    net_leverage: float
    nav: float
    position_count: int
    long_count: int
    short_count: int

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "gross_exposure": round(self.gross_exposure, 4),
            "net_exposure": round(self.net_exposure, 4),
            "long_exposure": round(self.long_exposure, 4),
            "short_exposure": round(self.short_exposure, 4),
            "leverage": round(self.leverage, 4),
            "net_leverage": round(self.net_leverage, 4),
            "nav": round(self.nav, 4),
            "position_count": self.position_count,
            "long_count": self.long_count,
            "short_count": self.short_count,
        }


# ---------------------------------------------------------------------------
# Position Engine
# ---------------------------------------------------------------------------

class PositionEngine:
    """Institutional position management engine (pure Python, in-memory).

    Supports FIFO, LIFO, average cost, and specific-lot cost basis methods.
    Tracks open lots, closed lots, realised P&L, and computes exposure /
    leverage given a NAV estimate.
    """

    def __init__(self, method: CostBasisMethod = CostBasisMethod.FIFO) -> None:
        """Initialise with a cost basis method.

        Args:
            method: Cost basis method for realised P&L computation.
        """
        self.method = method
        self._lots: Dict[str, List[Lot]] = {}
        self._closed_lots: List[ClosedLot] = []
        self._realised_pnl: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Trade processing
    # ------------------------------------------------------------------

    def open_position(
        self,
        ticker: str,
        quantity: float,
        price: float,
        *,
        acquired_datetime: Optional[datetime] = None,
    ) -> Lot:
        """Record a new acquisition lot (BUY trade).

        Args:
            ticker: Instrument symbol.
            quantity: Number of shares purchased (must be positive).
            price: Purchase price per share.
            acquired_datetime: UTC datetime of acquisition; defaults to now.

        Returns:
            The newly created Lot.

        Raises:
            ValueError: If quantity <= 0 or price <= 0.
        """
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if price <= 0:
            raise ValueError("price must be positive")

        now = acquired_datetime or datetime.now(timezone.utc)
        lot = Lot(
            lot_id=str(uuid.uuid4()),
            ticker=ticker.upper(),
            quantity=quantity,
            cost_per_share=price,
            acquired_date=now.date(),
            acquired_datetime=now,
        )
        self._lots.setdefault(ticker.upper(), []).append(lot)
        return lot

    def close_position(
        self,
        ticker: str,
        quantity: float,
        price: float,
        *,
        lot_id: Optional[str] = None,
        closed_datetime: Optional[datetime] = None,
    ) -> Tuple[List[ClosedLot], float]:
        """Reduce or close a position using the configured cost basis method.

        Args:
            ticker: Instrument symbol.
            quantity: Quantity to sell (must be positive).
            price: Sale price per share.
            lot_id: For SPECIFIC_LOT method — select this lot only.
            closed_datetime: UTC datetime of the close.

        Returns:
            Tuple of (list of ClosedLot records, total realised P&L).

        Raises:
            ValueError: If quantity exceeds total open position.
        """
        ticker = ticker.upper()
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if price <= 0:
            raise ValueError("price must be positive")

        open_lots = self._open_lots(ticker)
        total_open = sum(lot.remaining_quantity for lot in open_lots)
        if quantity > total_open + 1e-9:
            raise ValueError(
                f"Cannot close {quantity} of {ticker}: only {total_open} open"
            )

        now = closed_datetime or datetime.now(timezone.utc)
        lots_to_process = self._select_lots(open_lots, lot_id)
        closed_lot_records: List[ClosedLot] = []
        remaining = quantity
        total_realised = 0.0

        for lot in lots_to_process:
            if remaining <= 1e-9:
                break
            take = min(lot.remaining_quantity, remaining)
            realised = (price - lot.cost_per_share) * take
            total_realised += realised
            holding_days = (now.date() - lot.acquired_date).days

            cl = ClosedLot(
                close_id=str(uuid.uuid4()),
                lot_id=lot.lot_id,
                ticker=ticker,
                quantity=take,
                cost_per_share=lot.cost_per_share,
                proceeds_per_share=price,
                realised_pnl=realised,
                opened_date=lot.acquired_date,
                closed_datetime=now,
                holding_days=holding_days,
            )
            closed_lot_records.append(cl)
            self._closed_lots.append(cl)

            lot.remaining_quantity -= take
            remaining -= take
            if lot.remaining_quantity <= 1e-9:
                lot.remaining_quantity = 0.0
                lot.is_closed = True

        self._realised_pnl[ticker] = self._realised_pnl.get(ticker, 0.0) + total_realised
        return closed_lot_records, total_realised

    def _select_lots(self, open_lots: List[Lot], lot_id: Optional[str]) -> List[Lot]:
        """Return lots in the order dictated by the cost basis method."""
        if lot_id:
            specific = [l for l in open_lots if l.lot_id == lot_id]
            if not specific:
                raise ValueError(f"Lot {lot_id!r} not found or already closed")
            return specific
        if self.method == CostBasisMethod.FIFO:
            return sorted(open_lots, key=lambda l: l.acquired_datetime)
        elif self.method == CostBasisMethod.LIFO:
            return sorted(open_lots, key=lambda l: l.acquired_datetime, reverse=True)
        else:
            return sorted(open_lots, key=lambda l: l.acquired_datetime)

    def _open_lots(self, ticker: str) -> List[Lot]:
        return [l for l in self._lots.get(ticker, []) if not l.is_closed and l.remaining_quantity > 0]

    # ------------------------------------------------------------------
    # Position view
    # ------------------------------------------------------------------

    def get_position(self, ticker: str, market_price: float) -> Position:
        """Return the current position view for a ticker.

        Args:
            ticker: Instrument symbol.
            market_price: Current market price for MTM.

        Returns:
            Position dataclass.
        """
        ticker = ticker.upper()
        open_lots = self._open_lots(ticker)
        total_qty = sum(l.remaining_quantity for l in open_lots)

        if total_qty < 1e-9:
            return Position(
                ticker=ticker,
                side=PositionSide.FLAT,
                quantity=0.0,
                avg_cost=0.0,
                market_price=market_price,
                unrealised_pnl=0.0,
                market_value=0.0,
                open_lots=0,
                oldest_lot_date=None,
                holding_days=0,
            )

        avg_cost = sum(l.remaining_quantity * l.cost_per_share for l in open_lots) / total_qty
        market_value = total_qty * market_price
        unrealised = (market_price - avg_cost) * total_qty
        oldest = min(open_lots, key=lambda l: l.acquired_date)
        holding_days = (datetime.now(timezone.utc).date() - oldest.acquired_date).days

        return Position(
            ticker=ticker,
            side=PositionSide.LONG if total_qty > 0 else PositionSide.SHORT,
            quantity=total_qty,
            avg_cost=avg_cost,
            market_price=market_price,
            unrealised_pnl=unrealised,
            market_value=market_value,
            open_lots=len(open_lots),
            oldest_lot_date=oldest.acquired_date,
            holding_days=holding_days,
        )

    def all_positions(self, prices: Dict[str, float]) -> List[Position]:
        """Return Position for every ticker with an open position.

        Args:
            prices: Dict mapping ticker → current market price.

        Returns:
            List of Position objects for all non-flat tickers.
        """
        result = []
        for ticker in self._lots:
            price = prices.get(ticker, 0.0)
            pos = self.get_position(ticker, price)
            if pos.side != PositionSide.FLAT:
                result.append(pos)
        return sorted(result, key=lambda p: p.ticker)

    # ------------------------------------------------------------------
    # Lot queries
    # ------------------------------------------------------------------

    def get_open_lots(self, ticker: Optional[str] = None) -> List[Lot]:
        """Return all open lots, optionally filtered by ticker.

        Args:
            ticker: Optional filter.

        Returns:
            Sorted list of open Lot objects.
        """
        if ticker:
            return sorted(self._open_lots(ticker.upper()), key=lambda l: l.acquired_datetime)
        result = []
        for t in self._lots:
            result.extend(self._open_lots(t))
        return sorted(result, key=lambda l: l.acquired_datetime)

    def get_closed_lots(self, ticker: Optional[str] = None) -> List[ClosedLot]:
        """Return closed lot records, optionally filtered by ticker.

        Args:
            ticker: Optional filter.

        Returns:
            List of ClosedLot sorted by closed_datetime.
        """
        closed = self._closed_lots
        if ticker:
            closed = [c for c in closed if c.ticker == ticker.upper()]
        return sorted(closed, key=lambda c: c.closed_datetime)

    # ------------------------------------------------------------------
    # Realised P&L
    # ------------------------------------------------------------------

    def realised_pnl(self, ticker: Optional[str] = None) -> float:
        """Return total realised P&L, optionally per ticker.

        Args:
            ticker: Instrument filter.

        Returns:
            Realised P&L in USD.
        """
        if ticker:
            return self._realised_pnl.get(ticker.upper(), 0.0)
        return sum(self._realised_pnl.values())

    # ------------------------------------------------------------------
    # Exposure and leverage
    # ------------------------------------------------------------------

    def exposure_report(self, prices: Dict[str, float], nav: float) -> ExposureReport:
        """Compute portfolio exposure and leverage.

        Args:
            prices: Dict mapping ticker → current price.
            nav: Net asset value for leverage denominator.

        Returns:
            ExposureReport.

        Raises:
            ValueError: If nav <= 0.
        """
        if nav <= 0:
            raise ValueError("nav must be positive for leverage computation")

        positions = self.all_positions(prices)
        long_mv = sum(p.market_value for p in positions if p.side == PositionSide.LONG)
        short_mv = sum(abs(p.market_value) for p in positions if p.side == PositionSide.SHORT)
        gross_exp = long_mv + short_mv
        net_exp = long_mv - short_mv
        leverage = gross_exp / nav
        net_lev = abs(net_exp) / nav

        return ExposureReport(
            gross_exposure=gross_exp,
            net_exposure=net_exp,
            long_exposure=long_mv,
            short_exposure=short_mv,
            leverage=leverage,
            net_leverage=net_lev,
            nav=nav,
            position_count=len(positions),
            long_count=sum(1 for p in positions if p.side == PositionSide.LONG),
            short_count=sum(1 for p in positions if p.side == PositionSide.SHORT),
        )

    # ------------------------------------------------------------------
    # Position aging
    # ------------------------------------------------------------------

    def aged_positions(
        self,
        prices: Dict[str, float],
        min_holding_days: int = 0,
    ) -> List[Position]:
        """Return positions that have been held for at least min_holding_days.

        Args:
            prices: Current prices.
            min_holding_days: Minimum holding period filter.

        Returns:
            Filtered list of Position objects.
        """
        return [
            p for p in self.all_positions(prices)
            if p.holding_days >= min_holding_days
        ]

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self, prices: Dict[str, float]) -> Dict:
        """Return a full portfolio snapshot as a JSON-serialisable dict.

        Args:
            prices: Current market prices.

        Returns:
            Dict with positions, realised P&L, and aggregate stats.
        """
        positions = self.all_positions(prices)
        total_unrealised = sum(p.unrealised_pnl for p in positions)
        total_market_value = sum(p.market_value for p in positions)
        return {
            "positions": [p.to_dict() for p in positions],
            "total_positions": len(positions),
            "total_market_value": round(total_market_value, 4),
            "total_unrealised_pnl": round(total_unrealised, 4),
            "total_realised_pnl": round(self.realised_pnl(), 4),
            "realised_by_ticker": {t: round(v, 4) for t, v in self._realised_pnl.items()},
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_position_engine: Optional[PositionEngine] = None


def get_position_engine() -> PositionEngine:
    """Return the singleton PositionEngine instance.

    Returns:
        Shared PositionEngine instance.
    """
    global _default_position_engine
    if _default_position_engine is None:
        _default_position_engine = PositionEngine()
    return _default_position_engine
