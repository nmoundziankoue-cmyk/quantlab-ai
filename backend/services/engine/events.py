"""M11 Phase 1 — Typed event objects for the event-driven backtesting engine.

Event hierarchy (in dispatch priority order):
  0  MarketEvent   — a new OHLCV bar arrived
  1  SignalEvent   — a strategy produced a trading signal
  2  OrderEvent    — a validated order is ready to route
  3  FillEvent     — an order was executed (filled)
  4  PortfolioEvent — portfolio state was updated (mark-to-market)

All events are immutable dataclasses.  The ``event_type`` field is a
string constant on each class so handlers can dispatch without isinstance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Priority constants — used by EventQueue to order events within a timestamp
# ---------------------------------------------------------------------------

PRIORITY_MARKET: int = 0
PRIORITY_SIGNAL: int = 1
PRIORITY_ORDER: int = 2
PRIORITY_FILL: int = 3
PRIORITY_PORTFOLIO: int = 4


# ---------------------------------------------------------------------------
# Event dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MarketEvent:
    """A new OHLCV bar has been received for *ticker* at *timestamp*.

    ``timestamp`` is an ISO-8601 date string (``YYYY-MM-DD``) for daily bars.
    """

    event_type: str = field(default="MARKET", init=False, repr=False)
    priority: int = field(default=PRIORITY_MARKET, init=False, repr=False)

    ticker: str = ""
    timestamp: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", "MARKET")
        object.__setattr__(self, "priority", PRIORITY_MARKET)


@dataclass
class SignalEvent:
    """A strategy has generated a directional signal for *ticker*.

    ``signal`` is a ``services.strategy.Signal`` enum value or its string
    representation (``"BUY"`` / ``"SELL"`` / ``"HOLD"``).

    ``strength`` is a normalised conviction in [0, 1].  A value of 1.0
    means full conviction (deploy ``position_size_pct`` of equity).

    ``source`` is an optional label identifying the originating strategy.
    """

    event_type: str = field(default="SIGNAL", init=False, repr=False)
    priority: int = field(default=PRIORITY_SIGNAL, init=False, repr=False)

    ticker: str = ""
    timestamp: str = ""
    signal: str = "HOLD"
    strength: float = 1.0
    source: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", "SIGNAL")
        object.__setattr__(self, "priority", PRIORITY_SIGNAL)


@dataclass
class OrderEvent:
    """A validated order is ready to be routed to the execution layer.

    ``order_type`` is one of: ``"MARKET"``, ``"LIMIT"``, ``"STOP"``,
    ``"STOP_LIMIT"``, ``"TWAP"``, ``"VWAP"``.

    ``quantity`` is the number of shares (positive = buy, negative = sell).

    ``limit_price`` and ``stop_price`` are only relevant for LIMIT, STOP,
    and STOP_LIMIT orders.
    """

    event_type: str = field(default="ORDER", init=False, repr=False)
    priority: int = field(default=PRIORITY_ORDER, init=False, repr=False)

    ticker: str = ""
    timestamp: str = ""
    direction: str = "BUY"
    order_type: str = "MARKET"
    quantity: float = 0.0
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", "ORDER")
        object.__setattr__(self, "priority", PRIORITY_ORDER)


@dataclass
class FillEvent:
    """An order has been executed at *fill_price*.

    ``commission`` is the absolute dollar cost of the trade.
    ``slippage`` is the signed dollar amount of price impact
    (positive = cost to buyer, negative = benefit to seller).
    ``partial`` is True when only part of the requested quantity was filled.
    """

    event_type: str = field(default="FILL", init=False, repr=False)
    priority: int = field(default=PRIORITY_FILL, init=False, repr=False)

    ticker: str = ""
    timestamp: str = ""
    direction: str = "BUY"
    quantity: float = 0.0
    fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    partial: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", "FILL")
        object.__setattr__(self, "priority", PRIORITY_FILL)

    @property
    def gross_value(self) -> float:
        """Total gross trade value (unsigned)."""
        return self.quantity * self.fill_price

    @property
    def net_value(self) -> float:
        """Net cash impact — positive = cash spent (buy), negative = cash received (sell)."""
        sign = 1.0 if self.direction == "BUY" else -1.0
        return sign * (self.quantity * self.fill_price + sign * self.commission)


@dataclass
class PortfolioEvent:
    """Portfolio state snapshot after mark-to-market at *timestamp*.

    Emitted once per bar after all fills for that bar are processed.
    """

    event_type: str = field(default="PORTFOLIO", init=False, repr=False)
    priority: int = field(default=PRIORITY_PORTFOLIO, init=False, repr=False)

    timestamp: str = ""
    equity: float = 0.0
    cash: float = 0.0
    position_value: float = 0.0
    drawdown_pct: float = 0.0
    peak_equity: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", "PORTFOLIO")
        object.__setattr__(self, "priority", PRIORITY_PORTFOLIO)
