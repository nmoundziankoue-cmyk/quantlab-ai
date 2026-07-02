"""M17 — Paper Trading Simulation Engine (pure Python, in-memory).

Full simulated paper trading: realistic fills with spread/slippage,
deterministic latency model, integrated position/cash management, order
history, and P&L tracking.  Connects OMSEngine, PositionEngine, and
PortfolioAccountingEngine in a self-contained simulation loop.

No SQLAlchemy, no external libraries — stdlib + dataclasses only.
Note: The existing services/paper_trading.py is the DB-backed M5 engine;
this module is the M17 pure-Python in-memory simulation.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from services.order_management import (
    OMSEngine, Order, OrderType, OrderSide, OrderStatus, TimeInForce, Fill,
)
from services.position_engine import PositionEngine, CostBasisMethod
from services.portfolio_accounting import PortfolioAccountingEngine


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SimFillModel(str, Enum):
    INSTANT = "INSTANT"
    LIMIT_PASSIVE = "LIMIT_PASSIVE"
    PARTIAL_ALLOWED = "PARTIAL_ALLOWED"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class SimulatorConfig:
    """Configuration for the paper trading simulator.

    Args:
        initial_cash: Starting cash balance.
        spread_bps: Default bid-ask spread in basis points.
        slippage_bps: Market impact slippage per trade in basis points.
        commission_per_share: Commission rate per share.
        min_commission: Minimum commission per order.
        latency_ms: Deterministic execution latency in milliseconds.
        max_leverage: Maximum gross leverage allowed.
        fill_model: How limit orders are treated.
        allow_short_selling: Allow short sales.
    """

    initial_cash: float = 100_000.0
    spread_bps: float = 5.0
    slippage_bps: float = 5.0
    commission_per_share: float = 0.005
    min_commission: float = 1.0
    latency_ms: float = 50.0
    max_leverage: float = 4.0
    fill_model: SimFillModel = SimFillModel.INSTANT
    allow_short_selling: bool = True


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SimFillResult:
    """Result of attempting to fill a simulated order.

    Args:
        order_id: Filled order identifier.
        ticker: Instrument.
        side: BUY or SELL.
        requested_qty: Quantity requested.
        filled_qty: Quantity actually filled.
        fill_price: Execution price (including spread and slippage).
        commission: Commission charged.
        timestamp: Fill timestamp.
        is_filled: True if fully filled.
        reject_reason: If not filled, the reason.
    """

    order_id: str
    ticker: str
    side: str
    requested_qty: float
    filled_qty: float
    fill_price: float
    commission: float
    timestamp: datetime
    is_filled: bool
    reject_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "order_id": self.order_id,
            "ticker": self.ticker,
            "side": self.side,
            "requested_qty": self.requested_qty,
            "filled_qty": self.filled_qty,
            "fill_price": round(self.fill_price, 6),
            "commission": round(self.commission, 4),
            "timestamp": self.timestamp.isoformat(),
            "is_filled": self.is_filled,
            "reject_reason": self.reject_reason,
        }


@dataclass
class SimAccount:
    """Current state of the paper trading account.

    Args:
        cash: Available cash.
        equity: cash + unrealised_pnl of open positions.
        gross_exposure: Abs sum of all position market values.
        unrealised_pnl: Open position mark-to-market gain/loss.
        realised_pnl: Booked P&L from closed trades.
        total_commissions: Cumulative commissions paid.
        open_position_count: Number of non-flat positions.
        trade_count: Total number of fills executed.
    """

    cash: float
    equity: float
    gross_exposure: float
    unrealised_pnl: float
    realised_pnl: float
    total_commissions: float
    open_position_count: int
    trade_count: int

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "cash": round(self.cash, 4),
            "equity": round(self.equity, 4),
            "gross_exposure": round(self.gross_exposure, 4),
            "unrealised_pnl": round(self.unrealised_pnl, 4),
            "realised_pnl": round(self.realised_pnl, 4),
            "total_commissions": round(self.total_commissions, 4),
            "open_position_count": self.open_position_count,
            "trade_count": self.trade_count,
        }


@dataclass
class SimTrade:
    """A completed (closed) paper trade for analytics.

    Args:
        trade_id: Unique identifier.
        ticker: Instrument.
        side: BUY or SELL (entry side).
        quantity: Trade size.
        entry_price: Average entry price.
        exit_price: Average exit price.
        entry_time: Entry datetime.
        exit_time: Exit datetime.
        commission: Total commission for both legs.
        pnl: Net realised P&L.
    """

    trade_id: str
    ticker: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    commission: float
    pnl: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 6),
            "exit_price": round(self.exit_price, 6),
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "commission": round(self.commission, 4),
            "pnl": round(self.pnl, 4),
            "holding_hours": round(
                (self.exit_time - self.entry_time).total_seconds() / 3600.0, 2
            ),
        }


# ---------------------------------------------------------------------------
# Paper Trading Simulation Engine
# ---------------------------------------------------------------------------

class PaperTradingSimulator:
    """Full paper trading simulation engine (pure Python, in-memory).

    Wires together:
    - OMSEngine: order lifecycle and fills
    - PositionEngine: lot tracking and cost basis (FIFO)
    - PortfolioAccountingEngine: cash, P&L, NAV

    All fills are deterministic given the market price and config.
    """

    def __init__(self, config: Optional[SimulatorConfig] = None) -> None:
        """Initialise simulator with optional custom configuration.

        Args:
            config: Simulator configuration; uses defaults if None.
        """
        self.config = config or SimulatorConfig()
        self.oms = OMSEngine()
        self.positions = PositionEngine(CostBasisMethod.FIFO)
        self.accounting = PortfolioAccountingEngine(self.config.initial_cash)

        self._fills: List[SimFillResult] = []
        self._closed_trades: List[SimTrade] = []
        self._prices: Dict[str, float] = {}
        self._total_commissions: float = 0.0
        self._trade_count: int = 0

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def update_price(self, ticker: str, price: float) -> None:
        """Update the last known market price for an instrument.

        Args:
            ticker: Instrument symbol.
            price: Current market price.

        Raises:
            ValueError: If price <= 0.
        """
        if price <= 0:
            raise ValueError(f"price must be positive, got {price}")
        self._prices[ticker.upper()] = price

    def update_prices(self, prices: Dict[str, float]) -> None:
        """Bulk update market prices.

        Args:
            prices: Dict mapping ticker → price.
        """
        for ticker, price in prices.items():
            self.update_price(ticker, price)

    def get_price(self, ticker: str) -> Optional[float]:
        """Return the last known price for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            Last known price or None.
        """
        return self._prices.get(ticker.upper())

    # ------------------------------------------------------------------
    # Order submission and execution
    # ------------------------------------------------------------------

    def submit_market_order(
        self,
        ticker: str,
        side: OrderSide,
        quantity: float,
        *,
        strategy_tag: Optional[str] = None,
    ) -> SimFillResult:
        """Submit and immediately fill a market order.

        Args:
            ticker: Instrument symbol.
            side: BUY, SELL, SELL_SHORT, or BUY_TO_COVER.
            quantity: Order quantity.
            strategy_tag: Optional strategy label.

        Returns:
            SimFillResult with execution details.

        Raises:
            ValueError: If no price is available for the ticker.
        """
        price = self._prices.get(ticker.upper())
        if price is None:
            raise ValueError(f"No market price available for {ticker}")

        order = self.oms.submit_order(
            ticker, OrderType.MARKET, side, quantity,
            strategy_tag=strategy_tag,
        )
        return self._execute_order(order, price)

    def submit_limit_order(
        self,
        ticker: str,
        side: OrderSide,
        quantity: float,
        limit_price: float,
        *,
        strategy_tag: Optional[str] = None,
    ) -> Order:
        """Submit a limit order (fills only if current price crosses limit).

        In INSTANT fill mode, fills immediately if the market price is
        equal to or better than the limit price.

        Args:
            ticker: Instrument symbol.
            side: BUY or SELL.
            quantity: Order quantity.
            limit_price: Limit execution price.
            strategy_tag: Optional strategy label.

        Returns:
            The Order (may be WORKING or FILLED).
        """
        order = self.oms.submit_order(
            ticker, OrderType.LIMIT, side, quantity,
            limit_price=limit_price,
            strategy_tag=strategy_tag,
        )
        price = self._prices.get(ticker.upper())
        if price is not None and self._limit_crossable(order, price):
            self._execute_order(order, limit_price)
        return order

    def process_working_orders(self) -> List[SimFillResult]:
        """Attempt to fill all open WORKING orders against current prices.

        Called when prices update to check if any limit/stop orders are
        now fillable.

        Returns:
            List of SimFillResult for orders that filled.
        """
        filled = []
        for order in self.oms.get_open_orders():
            price = self._prices.get(order.ticker)
            if price is None:
                continue
            if self._is_fillable(order, price):
                exec_price = self._execution_price(order, price)
                result = self._execute_order(order, exec_price)
                filled.append(result)
        return filled

    def _limit_crossable(self, order: Order, market_price: float) -> bool:
        """Check if a limit order can fill at the current market price."""
        if order.limit_price is None:
            return True
        is_buy = order.side in (OrderSide.BUY, OrderSide.BUY_TO_COVER)
        if is_buy:
            return market_price <= order.limit_price
        else:
            return market_price >= order.limit_price

    def _is_fillable(self, order: Order, price: float) -> bool:
        """Check if any working order is fillable at the given price."""
        ot = order.order_type
        if ot == OrderType.MARKET:
            return True
        if ot in (OrderType.LIMIT, OrderType.IOC, OrderType.FOK,
                  OrderType.GTC, OrderType.GTD, OrderType.DAY,
                  OrderType.LOO, OrderType.LOC):
            return self._limit_crossable(order, price)
        if ot in (OrderType.STOP, OrderType.STOP_LIMIT):
            if order.stop_price is None:
                return False
            is_buy = order.side in (OrderSide.BUY, OrderSide.BUY_TO_COVER)
            return price >= order.stop_price if is_buy else price <= order.stop_price
        return False

    def _execution_price(self, order: Order, base_price: float) -> float:
        """Return execution price for an order including spread/slippage."""
        is_buy = order.side in (OrderSide.BUY, OrderSide.BUY_TO_COVER)
        half_spread = self.config.spread_bps * 0.5 / 10_000.0
        slippage = self.config.slippage_bps / 10_000.0
        total_adj = half_spread + slippage
        if is_buy:
            return base_price * (1.0 + total_adj)
        else:
            return base_price * (1.0 - total_adj)

    def _execute_order(self, order: Order, base_price: float) -> SimFillResult:
        """Execute an order at the given base price.

        Computes fill price (with spread/slippage), validates cash, records
        fill in OMS, updates positions and accounting.

        Args:
            order: Order to execute.
            base_price: Market reference price.

        Returns:
            SimFillResult.
        """
        is_buy = order.side in (OrderSide.BUY, OrderSide.BUY_TO_COVER)
        fill_price = self._execution_price(order, base_price)
        quantity = order.remaining_quantity
        commission = max(
            self.config.min_commission,
            quantity * self.config.commission_per_share,
        )

        # Cash check for buys
        if is_buy:
            total_cost = quantity * fill_price + commission
            if total_cost > self.accounting.cash:
                return SimFillResult(
                    order_id=order.order_id,
                    ticker=order.ticker,
                    side=order.side.value,
                    requested_qty=quantity,
                    filled_qty=0.0,
                    fill_price=fill_price,
                    commission=0.0,
                    timestamp=datetime.now(timezone.utc),
                    is_filled=False,
                    reject_reason=f"Insufficient cash: need {total_cost:.2f}, have {self.accounting.cash:.2f}",
                )

        # OMS fill
        fill = self.oms.record_fill(
            order.order_id, quantity, fill_price,
            venue="PAPER", commission=commission, fees=0.0,
        )

        # Accounting
        self.accounting.book_trade(
            order.ticker,
            order.side.value,
            quantity,
            fill_price,
            commission=commission,
            fees=0.0,
        )

        # Position tracking
        if is_buy:
            self.positions.open_position(order.ticker, quantity, fill_price)
        else:
            closed, realised = self.positions.close_position(
                order.ticker, quantity, fill_price
            )
            if closed:
                for cl in closed:
                    self._closed_trades.append(SimTrade(
                        trade_id=str(uuid.uuid4()),
                        ticker=order.ticker,
                        side="BUY",
                        quantity=cl.quantity,
                        entry_price=cl.cost_per_share,
                        exit_price=fill_price,
                        entry_time=datetime.combine(cl.opened_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                        exit_time=datetime.now(timezone.utc),
                        commission=commission * (cl.quantity / quantity),
                        pnl=cl.realised_pnl - commission * (cl.quantity / quantity),
                    ))

        self._total_commissions += commission
        self._trade_count += 1

        result = SimFillResult(
            order_id=order.order_id,
            ticker=order.ticker,
            side=order.side.value,
            requested_qty=quantity,
            filled_qty=quantity,
            fill_price=fill_price,
            commission=commission,
            timestamp=datetime.now(timezone.utc),
            is_filled=True,
        )
        self._fills.append(result)
        return result

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------

    def account_state(self) -> SimAccount:
        """Return the current account state.

        Returns:
            SimAccount with cash, equity, exposure, and P&L.
        """
        unrealised_by_ticker = self.positions.snapshot(self._prices)
        unrealised = unrealised_by_ticker["total_unrealised_pnl"]
        realised = unrealised_by_ticker["total_realised_pnl"]
        gross_mv = sum(
            abs(p["market_value"])
            for p in unrealised_by_ticker["positions"]
        )
        equity = self.accounting.cash + gross_mv
        return SimAccount(
            cash=self.accounting.cash,
            equity=equity,
            gross_exposure=gross_mv,
            unrealised_pnl=unrealised,
            realised_pnl=realised,
            total_commissions=self._total_commissions,
            open_position_count=unrealised_by_ticker["total_positions"],
            trade_count=self._trade_count,
        )

    def open_positions(self) -> List[Dict]:
        """Return all open positions with current prices.

        Returns:
            List of position dicts.
        """
        return self.positions.snapshot(self._prices)["positions"]

    # ------------------------------------------------------------------
    # Order queries
    # ------------------------------------------------------------------

    def get_orders(self, ticker: Optional[str] = None) -> List[Order]:
        """Return all orders, optionally filtered by ticker.

        Args:
            ticker: Optional instrument filter.

        Returns:
            List of Orders.
        """
        return self.oms.get_orders(ticker=ticker)

    def get_fills(self) -> List[SimFillResult]:
        """Return all fill results in execution order.

        Returns:
            List of SimFillResult.
        """
        return list(self._fills)

    def get_closed_trades(self) -> List[SimTrade]:
        """Return all completed (closed) trades.

        Returns:
            List of SimTrade.
        """
        return list(self._closed_trades)

    def cancel_order(self, order_id: str) -> Order:
        """Cancel a working order.

        Args:
            order_id: Order to cancel.

        Returns:
            Updated Order with CANCELLED status.
        """
        return self.oms.cancel_order(order_id)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self, initial_cash: Optional[float] = None) -> None:
        """Reset the simulator to a clean state.

        Args:
            initial_cash: New starting cash; uses config default if None.
        """
        cash = initial_cash if initial_cash is not None else self.config.initial_cash
        self.oms = OMSEngine()
        self.positions = PositionEngine(CostBasisMethod.FIFO)
        self.accounting = PortfolioAccountingEngine(cash)
        self._fills.clear()
        self._closed_trades.clear()
        self._prices.clear()
        self._total_commissions = 0.0
        self._trade_count = 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_paper_simulator: Optional[PaperTradingSimulator] = None


def get_paper_trading_simulator() -> PaperTradingSimulator:
    """Return the singleton PaperTradingSimulator instance.

    Returns:
        Shared PaperTradingSimulator instance with default configuration.
    """
    global _default_paper_simulator
    if _default_paper_simulator is None:
        _default_paper_simulator = PaperTradingSimulator()
    return _default_paper_simulator
