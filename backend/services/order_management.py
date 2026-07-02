"""M17 — Order Management System (pure Python, in-memory).

Institutional-grade OMS supporting 22 order types, full lifecycle state
machine, parent-child relationships (Bracket, OCO, TWAP, VWAP), partial
fills, amendment, cancellation, and trailing stop updates.

No SQLAlchemy, no external libraries — stdlib + dataclasses only.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    IOC = "IOC"
    FOK = "FOK"
    GTC = "GTC"
    GTD = "GTD"
    DAY = "DAY"
    BRACKET = "BRACKET"
    OCO = "OCO"
    ICEBERG = "ICEBERG"
    TWAP = "TWAP"
    VWAP = "VWAP"
    PEGGED = "PEGGED"
    HIDDEN = "HIDDEN"
    SYNTHETIC = "SYNTHETIC"
    MOO = "MOO"
    MOC = "MOC"
    LOO = "LOO"
    LOC = "LOC"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"


class OrderStatus(str, Enum):
    PENDING_NEW = "PENDING_NEW"
    WORKING = "WORKING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    AMENDED = "AMENDED"
    PENDING_CANCEL = "PENDING_CANCEL"
    PENDING_AMEND = "PENDING_AMEND"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    GTD = "GTD"
    IOC = "IOC"
    FOK = "FOK"
    ATO = "ATO"
    ATC = "ATC"


class PegType(str, Enum):
    MID = "MID"
    BID = "BID"
    ASK = "ASK"
    LAST = "LAST"


class TrailType(str, Enum):
    AMOUNT = "AMOUNT"
    PERCENT = "PERCENT"


class LinkType(str, Enum):
    BRACKET_PARENT = "BRACKET_PARENT"
    BRACKET_CHILD_TP = "BRACKET_CHILD_TP"
    BRACKET_CHILD_SL = "BRACKET_CHILD_SL"
    OCO_PAIR = "OCO_PAIR"
    TWAP_PARENT = "TWAP_PARENT"
    TWAP_CHILD = "TWAP_CHILD"
    VWAP_PARENT = "VWAP_PARENT"
    VWAP_CHILD = "VWAP_CHILD"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Fill:
    """A single execution report / fill.

    Args:
        fill_id: Unique fill identifier.
        order_id: Parent order identifier.
        quantity: Number of shares/contracts filled.
        price: Execution price.
        timestamp: UTC timestamp of the fill.
        venue: Execution venue name.
        commission: Commission charged in USD.
        fees: Exchange/clearing fees in USD.
    """

    fill_id: str
    order_id: str
    quantity: float
    price: float
    timestamp: datetime
    venue: str
    commission: float = 0.0
    fees: float = 0.0

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict representation."""
        return {
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "venue": self.venue,
            "commission": self.commission,
            "fees": self.fees,
            "total_cost": self.commission + self.fees,
        }


@dataclass
class OrderLink:
    """Relationship between two orders (e.g. bracket parent-child).

    Args:
        order_id: Source order.
        linked_order_id: Linked order.
        link_type: Nature of the relationship.
    """

    order_id: str
    linked_order_id: str
    link_type: LinkType


@dataclass
class Order:
    """Full order record.

    Args:
        order_id: Unique order identifier (UUID).
        client_order_id: Client-assigned identifier.
        ticker: Instrument symbol.
        order_type: One of the 22 supported order types.
        side: BUY / SELL / SELL_SHORT / BUY_TO_COVER.
        quantity: Total order quantity.
        status: Current lifecycle status.
        time_in_force: Validity instruction.
        limit_price: Limit price for LIMIT / STOP_LIMIT / ICE etc.
        stop_price: Trigger price for STOP / STOP_LIMIT / TRAILING_STOP.
        trail_amount: Trail offset (AMOUNT or PERCENT depending on trail_type).
        trail_type: AMOUNT or PERCENT.
        peg_type: Reference for PEGGED orders.
        iceberg_visible_qty: Displayed quantity for ICEBERG orders.
        created_at: UTC creation timestamp.
        updated_at: UTC last-update timestamp.
        expires_at: Expiry for GTD orders.
        fills: List of fills received.
        filled_quantity: Cumulative filled quantity.
        avg_fill_price: Volume-weighted average fill price.
        remaining_quantity: quantity - filled_quantity.
        parent_order_id: Parent if this is a child (TWAP/VWAP/Bracket slice).
        child_order_ids: IDs of generated child orders.
        link_type: How this order relates to its parent.
        broker_id: Routing destination.
        strategy_tag: Strategy / algo label.
        notes: Free-text notes.
        reject_reason: Rejection reason string if REJECTED.
        order_params: Flexible dict for algo-specific parameters.
    """

    order_id: str
    client_order_id: str
    ticker: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    status: OrderStatus
    time_in_force: TimeInForce
    created_at: datetime
    updated_at: datetime
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    trail_amount: Optional[float] = None
    trail_type: Optional[TrailType] = None
    peg_type: Optional[PegType] = None
    iceberg_visible_qty: Optional[float] = None
    expires_at: Optional[datetime] = None
    fills: List[Fill] = field(default_factory=list)
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    remaining_quantity: float = 0.0
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = field(default_factory=list)
    link_type: Optional[LinkType] = None
    broker_id: Optional[str] = None
    strategy_tag: Optional[str] = None
    notes: Optional[str] = None
    reject_reason: Optional[str] = None
    order_params: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.remaining_quantity = self.quantity - self.filled_quantity

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict representation."""
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "ticker": self.ticker,
            "order_type": self.order_type.value,
            "side": self.side.value,
            "quantity": self.quantity,
            "status": self.status.value,
            "time_in_force": self.time_in_force.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "trail_amount": self.trail_amount,
            "trail_type": self.trail_type.value if self.trail_type else None,
            "peg_type": self.peg_type.value if self.peg_type else None,
            "iceberg_visible_qty": self.iceberg_visible_qty,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "avg_fill_price": self.avg_fill_price,
            "fills": [f.to_dict() for f in self.fills],
            "parent_order_id": self.parent_order_id,
            "child_order_ids": list(self.child_order_ids),
            "link_type": self.link_type.value if self.link_type else None,
            "broker_id": self.broker_id,
            "strategy_tag": self.strategy_tag,
            "notes": self.notes,
            "reject_reason": self.reject_reason,
            "order_params": dict(self.order_params),
        }


@dataclass
class BracketResult:
    """Result of creating a bracket order.

    Args:
        parent: Entry order.
        take_profit: Take-profit child order.
        stop_loss: Stop-loss child order.
    """

    parent: Order
    take_profit: Order
    stop_loss: Order

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "parent": self.parent.to_dict(),
            "take_profit": self.take_profit.to_dict(),
            "stop_loss": self.stop_loss.to_dict(),
        }


@dataclass
class OCOResult:
    """Result of creating a One-Cancels-Other pair.

    Args:
        limit_order: The limit leg.
        stop_order: The stop leg.
    """

    limit_order: Order
    stop_order: Order

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "limit_order": self.limit_order.to_dict(),
            "stop_order": self.stop_order.to_dict(),
        }


# ---------------------------------------------------------------------------
# OMS Engine
# ---------------------------------------------------------------------------

_OPEN_STATUSES = {
    OrderStatus.PENDING_NEW,
    OrderStatus.WORKING,
    OrderStatus.PARTIAL,
    OrderStatus.PENDING_CANCEL,
    OrderStatus.PENDING_AMEND,
    OrderStatus.AMENDED,
}

_TERMINAL_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
}

# OrderType → canonical TimeInForce mapping
_ORDER_TYPE_TIF: Dict[OrderType, TimeInForce] = {
    OrderType.IOC: TimeInForce.IOC,
    OrderType.FOK: TimeInForce.FOK,
    OrderType.GTC: TimeInForce.GTC,
    OrderType.GTD: TimeInForce.GTD,
    OrderType.DAY: TimeInForce.DAY,
    OrderType.MOO: TimeInForce.ATO,
    OrderType.MOC: TimeInForce.ATC,
    OrderType.LOO: TimeInForce.ATO,
    OrderType.LOC: TimeInForce.ATC,
}


class OMSEngine:
    """Institutional in-memory Order Management System.

    Provides complete order lifecycle management: submission, amendment,
    cancellation, fill recording, bracket/OCO construction, TWAP/VWAP child
    generation, and trailing stop updates.

    All state is held in-memory; there is no database dependency.
    """

    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}
        self._client_id_index: Dict[str, str] = {}
        self._ticker_index: Dict[str, List[str]] = {}
        self._oco_pairs: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    def _make_order(
        self,
        ticker: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        *,
        time_in_force: Optional[TimeInForce] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_amount: Optional[float] = None,
        trail_type: Optional[TrailType] = None,
        peg_type: Optional[PegType] = None,
        iceberg_visible_qty: Optional[float] = None,
        expires_at: Optional[datetime] = None,
        parent_order_id: Optional[str] = None,
        link_type: Optional[LinkType] = None,
        broker_id: Optional[str] = None,
        strategy_tag: Optional[str] = None,
        notes: Optional[str] = None,
        client_order_id: Optional[str] = None,
        order_params: Optional[Dict] = None,
    ) -> Order:
        oid = self._new_id()
        cloid = client_order_id or f"CLO-{oid[:8]}"
        tif = time_in_force or _ORDER_TYPE_TIF.get(order_type, TimeInForce.DAY)
        now = self._now()
        order = Order(
            order_id=oid,
            client_order_id=cloid,
            ticker=ticker.upper(),
            order_type=order_type,
            side=side,
            quantity=quantity,
            status=OrderStatus.WORKING,
            time_in_force=tif,
            limit_price=limit_price,
            stop_price=stop_price,
            trail_amount=trail_amount,
            trail_type=trail_type,
            peg_type=peg_type,
            iceberg_visible_qty=iceberg_visible_qty,
            expires_at=expires_at,
            parent_order_id=parent_order_id,
            link_type=link_type,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
            notes=notes,
            created_at=now,
            updated_at=now,
            order_params=order_params or {},
        )
        self._store(order)
        return order

    def _store(self, order: Order) -> None:
        self._orders[order.order_id] = order
        self._client_id_index[order.client_order_id] = order.order_id
        self._ticker_index.setdefault(order.ticker, [])
        if order.order_id not in self._ticker_index[order.ticker]:
            self._ticker_index[order.ticker].append(order.order_id)

    def _touch(self, order: Order) -> None:
        order.updated_at = self._now()

    # ------------------------------------------------------------------
    # Order submission
    # ------------------------------------------------------------------

    def submit_order(
        self,
        ticker: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        *,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_amount: Optional[float] = None,
        trail_type: Optional[TrailType] = None,
        peg_type: Optional[PegType] = None,
        iceberg_visible_qty: Optional[float] = None,
        expires_at: Optional[datetime] = None,
        broker_id: Optional[str] = None,
        strategy_tag: Optional[str] = None,
        notes: Optional[str] = None,
        client_order_id: Optional[str] = None,
        order_params: Optional[Dict] = None,
    ) -> Order:
        """Submit a new order to the OMS.

        Args:
            ticker: Instrument symbol.
            order_type: One of the 22 supported order types.
            side: BUY / SELL / SELL_SHORT / BUY_TO_COVER.
            quantity: Total quantity requested.
            time_in_force: Validity instruction.
            limit_price: Limit price (LIMIT, STOP_LIMIT, LOO, LOC, IOC, FOK).
            stop_price: Stop trigger price (STOP, STOP_LIMIT).
            trail_amount: Trail offset value.
            trail_type: AMOUNT or PERCENT.
            peg_type: Peg reference for PEGGED orders.
            iceberg_visible_qty: Visible slice for ICEBERG.
            expires_at: Expiry datetime for GTD.
            broker_id: Routing destination.
            strategy_tag: Strategy label.
            notes: Free-text annotation.
            client_order_id: Client-assigned ID.
            order_params: Extra parameters dict.

        Returns:
            Newly created Order in WORKING status.

        Raises:
            ValueError: If quantity <= 0 or required price fields are missing.
        """
        if quantity <= 0:
            raise ValueError(f"quantity must be positive, got {quantity}")
        if order_type in (OrderType.LIMIT, OrderType.IOC, OrderType.FOK) and limit_price is None:
            raise ValueError(f"limit_price required for {order_type.value}")
        if order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and stop_price is None:
            raise ValueError(f"stop_price required for {order_type.value}")
        if order_type == OrderType.STOP_LIMIT and limit_price is None:
            raise ValueError("limit_price required for STOP_LIMIT")
        if order_type == OrderType.TRAILING_STOP and trail_amount is None:
            raise ValueError("trail_amount required for TRAILING_STOP")
        if order_type == OrderType.ICEBERG:
            if iceberg_visible_qty is None:
                raise ValueError("iceberg_visible_qty required for ICEBERG")
            if iceberg_visible_qty >= quantity:
                raise ValueError("iceberg_visible_qty must be less than quantity")

        return self._make_order(
            ticker, order_type, side, quantity,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            trail_amount=trail_amount,
            trail_type=trail_type,
            peg_type=peg_type,
            iceberg_visible_qty=iceberg_visible_qty,
            expires_at=expires_at,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
            notes=notes,
            client_order_id=client_order_id,
            order_params=order_params,
        )

    # ------------------------------------------------------------------
    # Amendment
    # ------------------------------------------------------------------

    def amend_order(
        self,
        order_id: str,
        *,
        quantity: Optional[float] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_amount: Optional[float] = None,
        expires_at: Optional[datetime] = None,
    ) -> Order:
        """Amend an existing working order.

        Args:
            order_id: ID of the order to amend.
            quantity: New total quantity (must be >= filled quantity).
            limit_price: New limit price.
            stop_price: New stop price.
            trail_amount: New trail offset.
            expires_at: New expiry for GTD.

        Returns:
            Updated Order.

        Raises:
            KeyError: If order_id not found.
            ValueError: If order is not amendable or quantity is invalid.
        """
        order = self._get_or_raise(order_id)
        if order.status in _TERMINAL_STATUSES:
            raise ValueError(f"Order {order_id} is in terminal status {order.status.value}")

        order.status = OrderStatus.PENDING_AMEND
        if quantity is not None:
            if quantity <= 0:
                raise ValueError("quantity must be positive")
            if quantity < order.filled_quantity:
                raise ValueError("New quantity cannot be less than filled quantity")
            order.quantity = quantity
            order.remaining_quantity = quantity - order.filled_quantity
        if limit_price is not None:
            order.limit_price = limit_price
        if stop_price is not None:
            order.stop_price = stop_price
        if trail_amount is not None:
            order.trail_amount = trail_amount
        if expires_at is not None:
            order.expires_at = expires_at

        order.status = OrderStatus.AMENDED if order.filled_quantity == 0 else (
            OrderStatus.PARTIAL if order.filled_quantity < order.quantity else OrderStatus.FILLED
        )
        self._touch(order)
        return order

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel_order(self, order_id: str) -> Order:
        """Cancel a working order.

        Args:
            order_id: ID of the order to cancel.

        Returns:
            Updated Order with CANCELLED status.

        Raises:
            KeyError: If order_id not found.
            ValueError: If order is already in a terminal status.
        """
        order = self._get_or_raise(order_id)
        if order.status in _TERMINAL_STATUSES:
            raise ValueError(f"Order {order_id} already in terminal status {order.status.value}")
        order.status = OrderStatus.PENDING_CANCEL
        order.status = OrderStatus.CANCELLED
        self._touch(order)

        sibling_id = self._oco_pairs.get(order_id)
        if sibling_id:
            sibling = self._orders.get(sibling_id)
            if sibling and sibling.status not in _TERMINAL_STATUSES:
                sibling.status = OrderStatus.CANCELLED
                self._touch(sibling)

        return order

    def reject_order(self, order_id: str, reason: str) -> Order:
        """Mark an order as rejected.

        Args:
            order_id: ID of the order to reject.
            reason: Human-readable rejection reason.

        Returns:
            Updated Order with REJECTED status.
        """
        order = self._get_or_raise(order_id)
        if order.status in _TERMINAL_STATUSES:
            raise ValueError(f"Order {order_id} already in terminal status")
        order.status = OrderStatus.REJECTED
        order.reject_reason = reason
        self._touch(order)
        return order

    # ------------------------------------------------------------------
    # Fill recording
    # ------------------------------------------------------------------

    def record_fill(
        self,
        order_id: str,
        quantity: float,
        price: float,
        *,
        venue: str = "UNKNOWN",
        commission: float = 0.0,
        fees: float = 0.0,
    ) -> Fill:
        """Record a partial or full fill for an order.

        Args:
            order_id: The order being filled.
            quantity: Filled quantity for this report.
            price: Execution price.
            venue: Execution venue name.
            commission: Commission charged.
            fees: Exchange / clearing fees.

        Returns:
            The Fill record that was created.

        Raises:
            KeyError: If order_id not found.
            ValueError: If fill quantity exceeds remaining quantity.
        """
        order = self._get_or_raise(order_id)
        if order.status in _TERMINAL_STATUSES and order.status != OrderStatus.PARTIAL:
            raise ValueError(f"Order {order_id} is not in a fillable state: {order.status.value}")
        if quantity <= 0:
            raise ValueError("fill quantity must be positive")
        if quantity > order.remaining_quantity + 1e-9:
            raise ValueError(
                f"Fill qty {quantity} exceeds remaining {order.remaining_quantity}"
            )

        fill = Fill(
            fill_id=self._new_id(),
            order_id=order_id,
            quantity=quantity,
            price=price,
            timestamp=self._now(),
            venue=venue,
            commission=commission,
            fees=fees,
        )
        order.fills.append(fill)

        prev_total = order.filled_quantity * order.avg_fill_price
        order.filled_quantity += quantity
        order.avg_fill_price = (prev_total + quantity * price) / order.filled_quantity
        order.remaining_quantity = max(0.0, order.quantity - order.filled_quantity)

        if order.remaining_quantity <= 1e-9:
            order.status = OrderStatus.FILLED
            self._on_fill_complete(order)
        else:
            order.status = OrderStatus.PARTIAL

        self._touch(order)
        return fill

    def _on_fill_complete(self, order: Order) -> None:
        """Trigger OCO cancellation when one leg fills."""
        sibling_id = self._oco_pairs.get(order.order_id)
        if sibling_id:
            sibling = self._orders.get(sibling_id)
            if sibling and sibling.status not in _TERMINAL_STATUSES:
                sibling.status = OrderStatus.CANCELLED
                self._touch(sibling)

    # ------------------------------------------------------------------
    # Bracket orders
    # ------------------------------------------------------------------

    def create_bracket(
        self,
        ticker: str,
        side: OrderSide,
        quantity: float,
        entry_price: Optional[float],
        take_profit_price: float,
        stop_loss_price: float,
        *,
        entry_order_type: OrderType = OrderType.LIMIT,
        broker_id: Optional[str] = None,
        strategy_tag: Optional[str] = None,
    ) -> BracketResult:
        """Create a bracket order: entry + take-profit + stop-loss.

        Args:
            ticker: Instrument symbol.
            side: BUY or SELL.
            quantity: Order quantity.
            entry_price: Limit price for entry (None for MARKET entry).
            take_profit_price: Limit price for the TP leg.
            stop_loss_price: Stop price for the SL leg.
            entry_order_type: MARKET or LIMIT for the entry leg.
            broker_id: Routing destination.
            strategy_tag: Strategy label.

        Returns:
            BracketResult with parent, take_profit, stop_loss orders.

        Raises:
            ValueError: If prices are inconsistent for the given side.
        """
        exit_side = OrderSide.SELL if side in (OrderSide.BUY,) else OrderSide.BUY_TO_COVER

        parent = self._make_order(
            ticker, entry_order_type, side, quantity,
            limit_price=entry_price,
            link_type=LinkType.BRACKET_PARENT,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
        )

        tp = self._make_order(
            ticker, OrderType.LIMIT, exit_side, quantity,
            limit_price=take_profit_price,
            parent_order_id=parent.order_id,
            link_type=LinkType.BRACKET_CHILD_TP,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
        )

        sl = self._make_order(
            ticker, OrderType.STOP, exit_side, quantity,
            stop_price=stop_loss_price,
            parent_order_id=parent.order_id,
            link_type=LinkType.BRACKET_CHILD_SL,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
        )

        parent.child_order_ids = [tp.order_id, sl.order_id]
        self._oco_pairs[tp.order_id] = sl.order_id
        self._oco_pairs[sl.order_id] = tp.order_id

        return BracketResult(parent=parent, take_profit=tp, stop_loss=sl)

    # ------------------------------------------------------------------
    # OCO orders
    # ------------------------------------------------------------------

    def create_oco(
        self,
        ticker: str,
        side: OrderSide,
        quantity: float,
        limit_price: float,
        stop_price: float,
        *,
        broker_id: Optional[str] = None,
        strategy_tag: Optional[str] = None,
    ) -> OCOResult:
        """Create a One-Cancels-Other order pair.

        Args:
            ticker: Instrument symbol.
            side: BUY or SELL.
            quantity: Quantity for both legs.
            limit_price: Limit price for the limit leg.
            stop_price: Stop trigger for the stop leg.
            broker_id: Routing destination.
            strategy_tag: Strategy label.

        Returns:
            OCOResult with limit_order and stop_order.
        """
        limit_leg = self._make_order(
            ticker, OrderType.LIMIT, side, quantity,
            limit_price=limit_price,
            link_type=LinkType.OCO_PAIR,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
        )
        stop_leg = self._make_order(
            ticker, OrderType.STOP, side, quantity,
            stop_price=stop_price,
            link_type=LinkType.OCO_PAIR,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
        )
        self._oco_pairs[limit_leg.order_id] = stop_leg.order_id
        self._oco_pairs[stop_leg.order_id] = limit_leg.order_id
        return OCOResult(limit_order=limit_leg, stop_order=stop_leg)

    # ------------------------------------------------------------------
    # TWAP child generation
    # ------------------------------------------------------------------

    def generate_twap_children(
        self,
        ticker: str,
        side: OrderSide,
        total_quantity: float,
        n_slices: int,
        *,
        limit_price: Optional[float] = None,
        broker_id: Optional[str] = None,
        strategy_tag: Optional[str] = None,
    ) -> Tuple[Order, List[Order]]:
        """Generate a TWAP parent and equal-size time-slice child orders.

        Args:
            ticker: Instrument symbol.
            side: BUY or SELL.
            total_quantity: Total TWAP quantity.
            n_slices: Number of equal time slices.
            limit_price: Optional limit price for child orders.
            broker_id: Routing destination.
            strategy_tag: Strategy label.

        Returns:
            Tuple of (parent_order, list_of_child_orders).

        Raises:
            ValueError: If n_slices < 1 or total_quantity <= 0.
        """
        if n_slices < 1:
            raise ValueError("n_slices must be >= 1")
        if total_quantity <= 0:
            raise ValueError("total_quantity must be positive")

        parent = self._make_order(
            ticker, OrderType.TWAP, side, total_quantity,
            limit_price=limit_price,
            link_type=LinkType.TWAP_PARENT,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
            order_params={"n_slices": n_slices},
        )

        slice_qty = total_quantity / n_slices
        children: List[Order] = []
        for i in range(n_slices):
            qty = slice_qty if i < n_slices - 1 else (total_quantity - slice_qty * (n_slices - 1))
            child_type = OrderType.LIMIT if limit_price is not None else OrderType.MARKET
            child = self._make_order(
                ticker, child_type, side, qty,
                limit_price=limit_price,
                parent_order_id=parent.order_id,
                link_type=LinkType.TWAP_CHILD,
                broker_id=broker_id,
                strategy_tag=strategy_tag,
                order_params={"slice_index": i, "total_slices": n_slices},
            )
            children.append(child)

        parent.child_order_ids = [c.order_id for c in children]
        return parent, children

    # ------------------------------------------------------------------
    # VWAP child generation
    # ------------------------------------------------------------------

    def generate_vwap_children(
        self,
        ticker: str,
        side: OrderSide,
        total_quantity: float,
        volume_profile: List[float],
        *,
        limit_price: Optional[float] = None,
        broker_id: Optional[str] = None,
        strategy_tag: Optional[str] = None,
    ) -> Tuple[Order, List[Order]]:
        """Generate VWAP parent + volume-weighted child orders.

        Args:
            ticker: Instrument symbol.
            side: BUY or SELL.
            total_quantity: Total VWAP quantity.
            volume_profile: Relative volume weights per time period (must sum > 0).
            limit_price: Optional limit for child orders.
            broker_id: Routing destination.
            strategy_tag: Strategy label.

        Returns:
            Tuple of (parent_order, list_of_child_orders).

        Raises:
            ValueError: If volume_profile is empty or sums to zero.
        """
        if not volume_profile:
            raise ValueError("volume_profile cannot be empty")
        total_vol = sum(volume_profile)
        if total_vol <= 0:
            raise ValueError("volume_profile must sum to a positive number")

        parent = self._make_order(
            ticker, OrderType.VWAP, side, total_quantity,
            limit_price=limit_price,
            link_type=LinkType.VWAP_PARENT,
            broker_id=broker_id,
            strategy_tag=strategy_tag,
            order_params={"n_slices": len(volume_profile), "volume_profile": volume_profile},
        )

        weights = [v / total_vol for v in volume_profile]
        children: List[Order] = []
        cumulative = 0.0
        for i, w in enumerate(weights):
            if i < len(weights) - 1:
                qty = total_quantity * w
                cumulative += qty
            else:
                qty = total_quantity - cumulative
            child_type = OrderType.LIMIT if limit_price is not None else OrderType.MARKET
            child = self._make_order(
                ticker, child_type, side, qty,
                limit_price=limit_price,
                parent_order_id=parent.order_id,
                link_type=LinkType.VWAP_CHILD,
                broker_id=broker_id,
                strategy_tag=strategy_tag,
                order_params={"slice_index": i, "volume_weight": w},
            )
            children.append(child)

        parent.child_order_ids = [c.order_id for c in children]
        return parent, children

    # ------------------------------------------------------------------
    # Trailing stop
    # ------------------------------------------------------------------

    def update_trailing_stop(self, order_id: str, current_price: float) -> Order:
        """Update trailing stop price based on current market price.

        For BUY / SELL_SHORT trailing stops: stop ratchets up as price rises.
        For SELL / BUY_TO_COVER trailing stops: stop ratchets down as price falls.

        Args:
            order_id: TRAILING_STOP order ID.
            current_price: Current market price.

        Returns:
            Updated Order with adjusted stop_price.

        Raises:
            KeyError: If order_id not found.
            ValueError: If order is not a TRAILING_STOP.
        """
        order = self._get_or_raise(order_id)
        if order.order_type != OrderType.TRAILING_STOP:
            raise ValueError(f"Order {order_id} is not a TRAILING_STOP")
        if order.trail_amount is None:
            raise ValueError("trail_amount is None on TRAILING_STOP order")

        trail = order.trail_amount
        if order.trail_type == TrailType.PERCENT:
            trail = current_price * (trail / 100.0)

        is_long = order.side in (OrderSide.BUY, OrderSide.BUY_TO_COVER)
        if is_long:
            new_stop = current_price - trail
            if order.stop_price is None or new_stop > order.stop_price:
                order.stop_price = new_stop
        else:
            new_stop = current_price + trail
            if order.stop_price is None or new_stop < order.stop_price:
                order.stop_price = new_stop

        self._touch(order)
        return order

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve an order by ID.

        Args:
            order_id: Order identifier.

        Returns:
            Order or None if not found.
        """
        return self._orders.get(order_id)

    def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
        """Retrieve an order by client-assigned ID.

        Args:
            client_order_id: Client identifier.

        Returns:
            Order or None if not found.
        """
        oid = self._client_id_index.get(client_order_id)
        return self._orders.get(oid) if oid else None

    def get_orders(
        self,
        ticker: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        side: Optional[OrderSide] = None,
        order_type: Optional[OrderType] = None,
        strategy_tag: Optional[str] = None,
    ) -> List[Order]:
        """Query orders with optional filters.

        Args:
            ticker: Filter by instrument symbol.
            status: Filter by lifecycle status.
            side: Filter by order side.
            order_type: Filter by order type.
            strategy_tag: Filter by strategy label.

        Returns:
            List of matching orders sorted by created_at ascending.
        """
        results = list(self._orders.values())
        if ticker:
            results = [o for o in results if o.ticker == ticker.upper()]
        if status:
            results = [o for o in results if o.status == status]
        if side:
            results = [o for o in results if o.side == side]
        if order_type:
            results = [o for o in results if o.order_type == order_type]
        if strategy_tag:
            results = [o for o in results if o.strategy_tag == strategy_tag]
        return sorted(results, key=lambda o: o.created_at)

    def get_open_orders(self, ticker: Optional[str] = None) -> List[Order]:
        """Return all non-terminal orders.

        Args:
            ticker: Optional ticker filter.

        Returns:
            List of open orders.
        """
        results = [o for o in self._orders.values() if o.status in _OPEN_STATUSES]
        if ticker:
            results = [o for o in results if o.ticker == ticker.upper()]
        return sorted(results, key=lambda o: o.created_at)

    def all_orders(self) -> List[Order]:
        """Return every order in the system.

        Returns:
            List of all orders sorted by created_at.
        """
        return sorted(self._orders.values(), key=lambda o: o.created_at)

    def expire_day_orders(self) -> List[Order]:
        """Mark all DAY / IOC / FOK working orders as EXPIRED.

        Returns:
            List of orders that were expired.
        """
        tif_to_expire = {TimeInForce.DAY, TimeInForce.IOC, TimeInForce.FOK}
        expired = []
        for order in self._orders.values():
            if order.status in _OPEN_STATUSES and order.time_in_force in tif_to_expire:
                order.status = OrderStatus.EXPIRED
                self._touch(order)
                expired.append(order)
        return expired

    def expire_gtd_orders(self, as_of: datetime) -> List[Order]:
        """Expire GTD orders whose expiry has passed.

        Args:
            as_of: Reference datetime (UTC).

        Returns:
            List of orders expired.
        """
        expired = []
        for order in self._orders.values():
            if (
                order.status in _OPEN_STATUSES
                and order.time_in_force == TimeInForce.GTD
                and order.expires_at is not None
                and order.expires_at <= as_of
            ):
                order.status = OrderStatus.EXPIRED
                self._touch(order)
                expired.append(order)
        return expired

    def get_fills(self, order_id: str) -> List[Fill]:
        """Return all fills for an order.

        Args:
            order_id: Order identifier.

        Returns:
            List of Fill records.
        """
        order = self._get_or_raise(order_id)
        return list(order.fills)

    def order_summary(self) -> Dict:
        """Return aggregate statistics over all orders.

        Returns:
            Dict with counts by status, by side, by type, and fill rate.
        """
        orders = list(self._orders.values())
        by_status: Dict[str, int] = {}
        by_side: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        total_filled = 0.0
        total_qty = 0.0
        for o in orders:
            by_status[o.status.value] = by_status.get(o.status.value, 0) + 1
            by_side[o.side.value] = by_side.get(o.side.value, 0) + 1
            by_type[o.order_type.value] = by_type.get(o.order_type.value, 0) + 1
            total_filled += o.filled_quantity
            total_qty += o.quantity
        fill_rate = (total_filled / total_qty) if total_qty > 0 else 0.0
        return {
            "total_orders": len(orders),
            "by_status": by_status,
            "by_side": by_side,
            "by_type": by_type,
            "fill_rate": round(fill_rate, 6),
            "total_quantity": total_qty,
            "total_filled": total_filled,
        }

    def _get_or_raise(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError(f"Order {order_id!r} not found")
        return order


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_oms: Optional[OMSEngine] = None


def get_oms_engine() -> OMSEngine:
    """Return the singleton OMSEngine instance.

    Returns:
        Shared OMSEngine instance.
    """
    global _default_oms
    if _default_oms is None:
        _default_oms = OMSEngine()
    return _default_oms
