"""M9 Phase 8 — Enhanced Execution Engine.

Adds: Bracket Orders, OCO (One-Cancels-Other), Trailing Stop, smart order routing,
VWAP/TWAP simulation, Iceberg orders, risk checks, execution/latency/order book simulators.
"""
from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    BRACKET = "bracket"
    OCO = "oco"
    TRAILING_STOP = "trailing_stop"
    VWAP = "vwap"
    TWAP = "twap"
    ICEBERG = "iceberg"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    TRIGGERED = "triggered"


@dataclass
class Order:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    trail_amount: Optional[float] = None
    trail_pct: Optional[float] = None
    time_in_force: str = "DAY"
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    filled_at: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # Related orders (bracket/OCO)
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    oco_pair_id: Optional[str] = None


@dataclass
class ExecutionReport:
    order_id: str
    ticker: str
    side: str
    quantity: float
    fill_price: float
    fill_time: str
    latency_ms: float
    venue: str
    slippage_bps: float


# ---------------------------------------------------------------------------
# Simulated order book
# ---------------------------------------------------------------------------

class OrderBookSimulator:
    """Minimal LOB simulator for execution testing."""

    def __init__(self, mid_price: float = 100.0, spread_bps: float = 5.0) -> None:
        self.mid = mid_price
        self.half_spread = mid_price * spread_bps / 20000

    def best_ask(self) -> float:
        return self.mid + self.half_spread

    def best_bid(self) -> float:
        return self.mid - self.half_spread

    def estimate_fill_price(self, side: str, quantity: float) -> float:
        market_impact_bps = min(quantity / 1000 * 2, 50)  # cap at 50bps
        if side == "buy":
            return self.best_ask() * (1 + market_impact_bps / 10000)
        return self.best_bid() * (1 - market_impact_bps / 10000)

    def simulate_vwap(self, side: str, quantity: float, slices: int = 10) -> float:
        fills = []
        for i in range(slices):
            slice_qty = quantity / slices
            noise = (0.999 + i * 0.0002)  # slight trend
            price = self.estimate_fill_price(side, slice_qty) * noise
            fills.append(price)
        return sum(fills) / len(fills)

    def simulate_twap(self, side: str, quantity: float, duration_min: float = 60, slices: int = 10) -> float:
        return self.simulate_vwap(side, quantity, slices)  # same logic for demo

    def to_dict(self) -> dict:
        return {
            "mid": round(self.mid, 4),
            "best_ask": round(self.best_ask(), 4),
            "best_bid": round(self.best_bid(), 4),
            "spread_bps": round(self.half_spread * 2 / self.mid * 10000, 2),
        }


# ---------------------------------------------------------------------------
# Risk checks
# ---------------------------------------------------------------------------

@dataclass
class RiskLimits:
    max_order_notional: float = 1_000_000.0
    max_position_pct: float = 0.20         # 20% of portfolio
    max_daily_loss: float = 50_000.0
    max_order_qty: float = 10_000.0
    portfolio_value: float = 500_000.0


def run_pre_trade_risk_checks(order: Order, price: float, limits: RiskLimits) -> Tuple[bool, str]:
    notional = order.quantity * price
    if notional > limits.max_order_notional:
        return False, f"Order notional {notional:.0f} exceeds limit {limits.max_order_notional:.0f}"
    if order.quantity > limits.max_order_qty:
        return False, f"Order quantity {order.quantity} exceeds limit {limits.max_order_qty}"
    position_pct = notional / limits.portfolio_value
    if position_pct > limits.max_position_pct:
        return False, f"Position {position_pct:.1%} exceeds max {limits.max_position_pct:.1%}"
    return True, "OK"


# ---------------------------------------------------------------------------
# Smart order router
# ---------------------------------------------------------------------------

VENUES = ["NYSE", "NASDAQ", "BATS", "IEX", "DARK_POOL"]

def smart_route(order: Order, price: float) -> str:
    """Return best venue based on order characteristics."""
    if order.order_type == OrderType.MARKET and order.quantity > 5000:
        return "DARK_POOL"
    if order.ticker in ("AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"):
        return "NASDAQ"
    if order.order_type == OrderType.LIMIT:
        return "IEX"
    return "NYSE"


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------

class ExecutionEngine:
    """Simulated execution engine with full order lifecycle management."""

    def __init__(self, risk_limits: Optional[RiskLimits] = None) -> None:
        self._orders: Dict[str, Order] = {}
        self._reports: List[ExecutionReport] = []
        self._risk = risk_limits or RiskLimits()
        self._daily_pnl: float = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Order submission
    # ------------------------------------------------------------------

    def submit_order(self, order: Order, market_price: float) -> dict:
        ok, reason = run_pre_trade_risk_checks(order, market_price, self._risk)
        if not ok:
            order.status = OrderStatus.REJECTED
            order.metadata["reject_reason"] = reason
            with self._lock:
                self._orders[order.id] = order
            return {"order_id": order.id, "status": "rejected", "reason": reason}

        order.status = OrderStatus.OPEN

        if order.order_type == OrderType.BRACKET:
            child_tp = Order(
                ticker=order.ticker, side=OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY,
                order_type=OrderType.LIMIT, quantity=order.quantity,
                limit_price=order.take_profit_price, metadata={"parent": order.id},
            )
            child_sl = Order(
                ticker=order.ticker, side=OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY,
                order_type=OrderType.STOP, quantity=order.quantity,
                stop_price=order.stop_loss_price, metadata={"parent": order.id},
            )
            with self._lock:
                self._orders[child_tp.id] = child_tp
                self._orders[child_sl.id] = child_sl
                order.metadata["tp_order"] = child_tp.id
                order.metadata["sl_order"] = child_sl.id

        elif order.order_type == OrderType.TRAILING_STOP:
            if order.trail_pct:
                order.stop_price = market_price * (1 - order.trail_pct) if order.side == OrderSide.SELL else market_price * (1 + order.trail_pct)
            elif order.trail_amount:
                order.stop_price = market_price - order.trail_amount if order.side == OrderSide.SELL else market_price + order.trail_amount

        with self._lock:
            self._orders[order.id] = order

        # Immediate fill for market orders
        if order.order_type in (OrderType.MARKET, OrderType.VWAP, OrderType.TWAP):
            return self._fill_order(order.id, market_price)

        return {"order_id": order.id, "status": "open"}

    def _fill_order(self, order_id: str, fill_price: float) -> dict:
        order = self._orders.get(order_id)
        if not order or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return {"order_id": order_id, "status": "not_found"}

        t0 = time.monotonic()
        book = OrderBookSimulator(fill_price)
        venue = smart_route(order, fill_price)

        if order.order_type == OrderType.VWAP:
            actual_price = book.simulate_vwap(order.side.value, order.quantity)
        elif order.order_type == OrderType.TWAP:
            actual_price = book.simulate_twap(order.side.value, order.quantity)
        else:
            actual_price = book.estimate_fill_price(order.side.value, order.quantity)

        latency_ms = (time.monotonic() - t0) * 1000 + 0.5
        slippage_bps = abs(actual_price - fill_price) / fill_price * 10000

        with self._lock:
            order.status = OrderStatus.FILLED
            order.filled_qty = order.quantity
            order.avg_fill_price = round(actual_price, 4)
            order.filled_at = datetime.now(timezone.utc).isoformat()

            report = ExecutionReport(
                order_id=order.id,
                ticker=order.ticker,
                side=order.side.value,
                quantity=order.quantity,
                fill_price=round(actual_price, 4),
                fill_time=order.filled_at,
                latency_ms=round(latency_ms, 3),
                venue=venue,
                slippage_bps=round(slippage_bps, 2),
            )
            self._reports.append(report)

            # Cancel OCO pair if applicable
            if order.oco_pair_id and order.oco_pair_id in self._orders:
                self._orders[order.oco_pair_id].status = OrderStatus.CANCELLED

        return {"order_id": order.id, "status": "filled", "fill_price": order.avg_fill_price,
                "venue": venue, "latency_ms": round(latency_ms, 3)}

    def cancel_order(self, order_id: str) -> bool:
        with self._lock:
            order = self._orders.get(order_id)
            if order and order.status == OrderStatus.OPEN:
                order.status = OrderStatus.CANCELLED
                return True
        return False

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def list_orders(self, status: Optional[str] = None, ticker: Optional[str] = None) -> List[dict]:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status.value == status]
        if ticker:
            orders = [o for o in orders if o.ticker == ticker]
        return [self._order_to_dict(o) for o in orders]

    def execution_reports(self, limit: int = 50) -> List[dict]:
        return [r.__dict__ for r in self._reports[-limit:]]

    def latency_stats(self) -> dict:
        if not self._reports:
            return {}
        latencies = [r.latency_ms for r in self._reports]
        sorted_l = sorted(latencies)
        return {
            "avg_ms": round(sum(latencies) / len(latencies), 3),
            "p50_ms": sorted_l[len(sorted_l) // 2],
            "p95_ms": sorted_l[int(len(sorted_l) * 0.95)],
            "p99_ms": sorted_l[int(len(sorted_l) * 0.99)],
            "total_fills": len(self._reports),
        }

    def _order_to_dict(self, order: Order) -> dict:
        return {
            "id": order.id,
            "ticker": order.ticker,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "limit_price": order.limit_price,
            "stop_price": order.stop_price,
            "status": order.status.value,
            "filled_qty": order.filled_qty,
            "avg_fill_price": order.avg_fill_price,
            "created_at": order.created_at,
            "filled_at": order.filled_at,
            "metadata": order.metadata,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_engine: Optional[ExecutionEngine] = None


def get_execution_engine() -> ExecutionEngine:
    global _engine
    if _engine is None:
        _engine = ExecutionEngine()
    return _engine
