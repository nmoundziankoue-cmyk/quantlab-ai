"""Order Management System (OMS).

Handles the complete order lifecycle:
  - Order creation and validation
  - Submission to broker / paper engine
  - Modification and cancellation
  - Audit trail logging
  - OCO / OTO / Bracket cascade logic
  - Basket (bulk) order submission

All business logic lives here.  Routers only marshal HTTP ↔ service calls.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.trading import (
    Alert,
    AlertTypeEnum,
    AuditEventEnum,
    Execution,
    LinkTypeEnum,
    Order,
    OrderAuditLog,
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    TimeInForceEnum,
)
from schemas.trading import OrderCreate, OrderModify


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log_event(
    db: Session,
    order: Order,
    event_type: AuditEventEnum,
    payload: Dict[str, Any] | None = None,
    message: str | None = None,
) -> None:
    entry = OrderAuditLog(
        order_id=order.id,
        event_type=event_type,
        from_status=order.status.value if hasattr(order.status, "value") else order.status,
        payload=payload or {},
        message=message,
    )
    db.add(entry)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_order(
    order_create: OrderCreate,
    account_cash: Decimal,
    market_price: Optional[Decimal],
) -> Tuple[bool, List[str]]:
    """Run pre-submission validation checks.

    Returns (is_valid, error_list).
    """
    errors: List[str] = []

    ot = OrderTypeEnum(order_create.order_type) if isinstance(order_create.order_type, str) else order_create.order_type
    side = OrderSideEnum(order_create.side) if isinstance(order_create.side, str) else order_create.side

    if order_create.quantity <= 0:
        errors.append("quantity must be positive")

    if ot == OrderTypeEnum.LIMIT and order_create.limit_price is None:
        errors.append("LIMIT orders require limit_price")

    if ot == OrderTypeEnum.STOP and order_create.stop_price is None:
        errors.append("STOP orders require stop_price")

    if ot == OrderTypeEnum.STOP_LIMIT:
        if order_create.limit_price is None:
            errors.append("STOP_LIMIT orders require limit_price")
        if order_create.stop_price is None:
            errors.append("STOP_LIMIT orders require stop_price")

    if ot == OrderTypeEnum.TRAILING_STOP and order_create.trail_amount is None:
        errors.append("TRAILING_STOP orders require trail_amount")

    # Buying power check for buy orders
    if market_price is not None and side in (OrderSideEnum.BUY, OrderSideEnum.BUY_TO_COVER):
        est_price = order_create.limit_price or market_price
        est_value = order_create.quantity * est_price
        if est_value > account_cash:
            errors.append(
                f"Insufficient buying power: need ${est_value:.2f}, have ${account_cash:.2f}"
            )

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Order CRUD
# ---------------------------------------------------------------------------


def create_order(
    db: Session,
    order_create: OrderCreate,
    portfolio_id: Optional[uuid.UUID] = None,
    paper_account_id: Optional[uuid.UUID] = None,
    broker_connection_id: Optional[uuid.UUID] = None,
) -> Order:
    """Persist a new order in PENDING status and write the CREATE audit event."""
    order = Order(
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        broker_connection_id=broker_connection_id,
        basket_id=order_create.basket_id,
        parent_order_id=order_create.parent_order_id,
        link_type=order_create.link_type,
        ticker=order_create.ticker.upper(),
        asset_class=order_create.asset_class.upper(),
        order_type=order_create.order_type,
        side=order_create.side,
        time_in_force=order_create.time_in_force,
        quantity=order_create.quantity,
        filled_quantity=Decimal("0"),
        limit_price=order_create.limit_price,
        stop_price=order_create.stop_price,
        trail_amount=order_create.trail_amount,
        trail_type=order_create.trail_type,
        exec_algo=order_create.exec_algo,
        exec_algo_params=order_create.exec_algo_params,
        status=OrderStatusEnum.PENDING,
        strategy_tag=order_create.strategy_tag,
        tags=order_create.tags,
        notes=order_create.notes,
        expires_at=order_create.expires_at,
    )
    db.add(order)
    db.flush()  # get id without committing

    _log_event(db, order, AuditEventEnum.CREATED, message="Order created")
    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: uuid.UUID) -> Optional[Order]:
    return db.query(Order).filter(Order.id == order_id).first()


def list_orders(
    db: Session,
    portfolio_id: Optional[uuid.UUID] = None,
    paper_account_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    ticker: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Order], int]:
    q = db.query(Order)
    if portfolio_id:
        q = q.filter(Order.portfolio_id == portfolio_id)
    if paper_account_id:
        q = q.filter(Order.paper_account_id == paper_account_id)
    if status:
        q = q.filter(Order.status == status)
    if ticker:
        q = q.filter(Order.ticker == ticker.upper())
    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return orders, total


def modify_order(
    db: Session,
    order_id: uuid.UUID,
    modify: OrderModify,
) -> Order:
    """Modify a PENDING or SUBMITTED order."""
    order = get_order(db, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")

    status = order.status.value if hasattr(order.status, "value") else order.status
    if status not in (OrderStatusEnum.PENDING.value, OrderStatusEnum.SUBMITTED.value, OrderStatusEnum.ACCEPTED.value):
        raise ValueError(f"Cannot modify order in status {status}")

    old_vals: Dict[str, Any] = {}
    if modify.quantity is not None:
        old_vals["quantity"] = str(order.quantity)
        order.quantity = modify.quantity
    if modify.limit_price is not None:
        old_vals["limit_price"] = str(order.limit_price)
        order.limit_price = modify.limit_price
    if modify.stop_price is not None:
        old_vals["stop_price"] = str(order.stop_price)
        order.stop_price = modify.stop_price
    if modify.trail_amount is not None:
        old_vals["trail_amount"] = str(order.trail_amount)
        order.trail_amount = modify.trail_amount
    if modify.time_in_force is not None:
        old_vals["time_in_force"] = order.time_in_force.value if hasattr(order.time_in_force, "value") else order.time_in_force
        order.time_in_force = modify.time_in_force
    if modify.notes is not None:
        order.notes = modify.notes

    _log_event(db, order, AuditEventEnum.MODIFIED, payload={"old": old_vals}, message="Order modified")
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order_id: uuid.UUID, reason: str = "User requested") -> Order:
    """Request cancellation of an open order."""
    order = get_order(db, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")

    status = order.status.value if hasattr(order.status, "value") else order.status
    if status in (OrderStatusEnum.FILLED.value, OrderStatusEnum.CANCELLED.value,
                   OrderStatusEnum.REJECTED.value, OrderStatusEnum.EXPIRED.value):
        raise ValueError(f"Cannot cancel order in terminal status {status}")

    _log_event(db, order, AuditEventEnum.CANCELLATION_REQUESTED, message=reason)
    order.status = OrderStatusEnum.CANCELLED
    order.cancelled_at = _now()

    _log_event(db, order, AuditEventEnum.CANCELLED, message=reason)

    # OCO cascade: cancel the linked order
    if order.linked_order_id and order.link_type in (
        LinkTypeEnum.OCO_PRIMARY, LinkTypeEnum.OCO_SECONDARY
    ):
        linked = get_order(db, order.linked_order_id)
        if linked is not None:
            linked_status = linked.status.value if hasattr(linked.status, "value") else linked.status
            if linked_status not in (
                OrderStatusEnum.FILLED.value, OrderStatusEnum.CANCELLED.value,
                OrderStatusEnum.REJECTED.value
            ):
                linked.status = OrderStatusEnum.CANCELLED
                linked.cancelled_at = _now()
                _log_event(db, linked, AuditEventEnum.CANCELLED, message="OCO cascade cancel")

    db.commit()
    db.refresh(order)
    return order


def get_audit_log(db: Session, order_id: uuid.UUID) -> List[OrderAuditLog]:
    return (
        db.query(OrderAuditLog)
        .filter(OrderAuditLog.order_id == order_id)
        .order_by(OrderAuditLog.created_at.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Submission & Fill (used by paper engine and broker adapters)
# ---------------------------------------------------------------------------


def mark_submitted(db: Session, order: Order, broker_order_id: Optional[str] = None) -> Order:
    order.status = OrderStatusEnum.SUBMITTED
    order.submitted_at = _now()
    if broker_order_id:
        order.broker_order_id = broker_order_id
    _log_event(db, order, AuditEventEnum.SUBMITTED, message="Submitted to execution engine")
    db.commit()
    db.refresh(order)
    return order


def record_partial_fill(
    db: Session,
    order: Order,
    fill_qty: Decimal,
    fill_price: Decimal,
    commission: Decimal,
    slippage: Decimal,
    venue: str = "PAPER",
    broker: str = "PAPER",
    latency_ms: Optional[int] = None,
) -> Execution:
    """Record a partial or full fill on an order."""
    execution = Execution(
        order_id=order.id,
        ticker=order.ticker,
        side=order.side.value if hasattr(order.side, "value") else order.side,
        quantity=fill_qty,
        fill_price=fill_price,
        market_price_at_fill=fill_price,
        slippage=slippage,
        commission=commission,
        venue=venue,
        broker=broker,
        latency_ms=latency_ms,
        execution_time=_now(),
    )
    db.add(execution)

    # Update running totals on the order
    total_filled = order.filled_quantity + fill_qty
    # Weighted average fill price
    if order.average_fill_price is not None:
        old_value = order.filled_quantity * order.average_fill_price
        new_value = fill_qty * fill_price
        order.average_fill_price = (old_value + new_value) / total_filled
    else:
        order.average_fill_price = fill_price

    order.filled_quantity = total_filled
    order.commission += commission
    order.total_slippage += slippage

    remaining = order.quantity - order.filled_quantity
    if remaining <= Decimal("1e-8"):
        order.status = OrderStatusEnum.FILLED
        order.filled_at = _now()
        _log_event(db, order, AuditEventEnum.FILLED, payload={"fill_price": str(fill_price)})
    else:
        order.status = OrderStatusEnum.PARTIALLY_FILLED
        _log_event(db, order, AuditEventEnum.PARTIALLY_FILLED, payload={
            "filled": str(total_filled),
            "remaining": str(remaining),
        })

    db.flush()
    db.commit()
    db.refresh(execution)

    # Trigger OTO cascade: if this was an OTO trigger order that just filled,
    # the secondary order should become PENDING (submitted to execution).
    if order.status == OrderStatusEnum.FILLED:
        _handle_post_fill_cascade(db, order)

    return execution


def _handle_post_fill_cascade(db: Session, filled_order: Order) -> None:
    """Handle linked-order logic when an order fills."""
    lt = filled_order.link_type.value if hasattr(filled_order.link_type, "value") else filled_order.link_type

    # OCO: cancel the sibling
    if lt in (LinkTypeEnum.OCO_PRIMARY.value, LinkTypeEnum.OCO_SECONDARY.value):
        if filled_order.linked_order_id:
            sibling = get_order(db, filled_order.linked_order_id)
            if sibling:
                s_status = sibling.status.value if hasattr(sibling.status, "value") else sibling.status
                if s_status not in (OrderStatusEnum.FILLED.value, OrderStatusEnum.CANCELLED.value):
                    sibling.status = OrderStatusEnum.CANCELLED
                    sibling.cancelled_at = _now()
                    _log_event(db, sibling, AuditEventEnum.CANCELLED, message="OCO sibling filled")

    # OTO: submit the secondary
    if lt == LinkTypeEnum.OTO_TRIGGER.value:
        # find the secondary
        secondary = db.query(Order).filter(
            Order.parent_order_id == filled_order.id,
            Order.link_type == LinkTypeEnum.OTO_SECONDARY,
        ).first()
        if secondary:
            secondary.status = OrderStatusEnum.SUBMITTED
            secondary.submitted_at = _now()
            _log_event(db, secondary, AuditEventEnum.SUBMITTED, message="OTO trigger filled — secondary activated")


# ---------------------------------------------------------------------------
# Simulation / Preview
# ---------------------------------------------------------------------------


def simulate_order(
    order_create: OrderCreate,
    market_price: Decimal,
    commission_rate: Decimal = Decimal("1.00"),
    slippage_bps: int = 10,
) -> Dict[str, Any]:
    """Return an estimated fill preview without touching the database."""
    ot = OrderTypeEnum(order_create.order_type) if isinstance(order_create.order_type, str) else order_create.order_type
    side = OrderSideEnum(order_create.side) if isinstance(order_create.side, str) else order_create.side

    # Determine estimated fill price
    if ot == OrderTypeEnum.MARKET:
        est_price = market_price
    elif ot == OrderTypeEnum.LIMIT:
        est_price = order_create.limit_price
    elif ot == OrderTypeEnum.STOP:
        est_price = order_create.stop_price
    elif ot == OrderTypeEnum.STOP_LIMIT:
        est_price = order_create.limit_price
    else:
        est_price = market_price

    # Slippage only applies to MARKET orders; LIMIT/STOP fills happen at the stated price
    if ot == OrderTypeEnum.MARKET:
        slip = (est_price * Decimal(slippage_bps) / Decimal("10000")) if est_price else Decimal("0")
        if side == OrderSideEnum.BUY:
            fill_price = est_price + slip if est_price else None
        else:
            fill_price = est_price - slip if est_price else None
    else:
        slip = Decimal("0")
        fill_price = est_price

    est_value = order_create.quantity * fill_price if fill_price else None

    # Commission estimate
    est_commission = max(commission_rate, est_value * Decimal("0.005") / Decimal("100")) if est_value else commission_rate

    return {
        "ticker": order_create.ticker,
        "side": order_create.side,
        "quantity": order_create.quantity,
        "order_type": order_create.order_type,
        "estimated_price": fill_price,
        "estimated_value": est_value,
        "estimated_commission": est_commission,
        "estimated_slippage": slip * order_create.quantity if slip else Decimal("0"),
        "estimated_total_cost": (est_value + est_commission) if est_value else None,
        "market_price": market_price,
        "buying_power_required": est_value if side == OrderSideEnum.BUY else None,
        "is_valid": True,
        "validation_errors": [],
    }


# ---------------------------------------------------------------------------
# Basket Orders
# ---------------------------------------------------------------------------


def create_basket_order(
    db: Session,
    items: List[OrderCreate],
    portfolio_id: Optional[uuid.UUID] = None,
    paper_account_id: Optional[uuid.UUID] = None,
    broker_connection_id: Optional[uuid.UUID] = None,
) -> Tuple[uuid.UUID, List[Order]]:
    basket_id = uuid.uuid4()
    orders: List[Order] = []
    for item in items:
        item_with_basket = item.model_copy(update={"basket_id": basket_id})
        o = create_order(
            db, item_with_basket,
            portfolio_id=portfolio_id,
            paper_account_id=paper_account_id,
            broker_connection_id=broker_connection_id,
        )
        orders.append(o)
    return basket_id, orders


def list_basket_orders(db: Session, basket_id: uuid.UUID) -> List[Order]:
    return db.query(Order).filter(Order.basket_id == basket_id).all()
