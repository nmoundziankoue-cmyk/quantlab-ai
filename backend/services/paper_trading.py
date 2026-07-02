"""Paper Trading Engine.

Simulates realistic order execution for a virtual (paper) broker account:
  - MARKET orders fill instantly at current market price + slippage
  - LIMIT orders fill if market price crosses the limit
  - STOP orders convert to MARKET when stop price is touched
  - STOP_LIMIT orders convert to LIMIT when stop is touched
  - Position accounting uses AVCO (Average Cost) method
  - Commission model: $0.005/share, minimum $1.00, max 0.5% of trade value
  - Slippage model: configurable basis points (default 10 bps)
  - Latency model: random uniform 5–50 ms (paper, no real network)

PnL is computed and stored in real time on every fill.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.trading import (
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    PaperAccount,
    PaperPosition,
    PaperTrade,
)
from services import oms as oms_service
from services.oms import Order


# ---------------------------------------------------------------------------
# Commission / Slippage / Latency models
# ---------------------------------------------------------------------------


def compute_commission(quantity: Decimal, fill_price: Decimal, commission_type: str, rate: Decimal, min_comm: Decimal) -> Decimal:
    """Compute commission for a fill.

    Supported commission_type values:
      FLAT       — fixed dollar amount per trade (rate = fixed $)
      PER_SHARE  — rate per share; min applied; max capped at 0.5% of value
      PERCENT    — rate is a percentage of trade value (e.g. 0.001 = 0.1%)
    """
    gross_value = quantity * fill_price
    if commission_type == "PER_SHARE":
        raw = quantity * rate
        raw = max(raw, min_comm)
        cap = gross_value * Decimal("0.005")  # 0.5% cap
        return min(raw, cap).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif commission_type == "PERCENT":
        raw = gross_value * rate
        raw = max(raw, min_comm)
        return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:  # FLAT
        return rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_slippage_cost(quantity: Decimal, fill_price: Decimal, slippage_bps: int) -> Decimal:
    """Slippage as dollar cost: qty × price × bps / 10000."""
    return (quantity * fill_price * Decimal(slippage_bps) / Decimal("10000")).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


def apply_slippage_to_price(price: Decimal, side: str, slippage_bps: int) -> Decimal:
    """Return price after slippage is applied in the adverse direction."""
    slip_fraction = Decimal(slippage_bps) / Decimal("10000")
    if side in (OrderSideEnum.BUY.value, "BUY", "BUY_TO_COVER"):
        return price * (1 + slip_fraction)
    return price * (1 - slip_fraction)


def simulate_latency_ms() -> int:
    return random.randint(5, 50)


# ---------------------------------------------------------------------------
# Fill price logic
# ---------------------------------------------------------------------------


def compute_fill_price(
    order_type: str,
    side: str,
    market_price: Decimal,
    limit_price: Optional[Decimal],
    stop_price: Optional[Decimal],
    slippage_bps: int,
) -> Optional[Decimal]:
    """Determine whether an order fills and at what price.

    Returns fill_price if the order should fill, or None if it should not.
    """
    ot = OrderTypeEnum(order_type) if isinstance(order_type, str) else order_type

    if ot == OrderTypeEnum.MARKET:
        return apply_slippage_to_price(market_price, side, slippage_bps)

    if ot == OrderTypeEnum.LIMIT:
        if limit_price is None:
            return None
        is_buy = side in (OrderSideEnum.BUY.value, "BUY", "BUY_TO_COVER")
        # Buy limit fills if market ≤ limit
        if is_buy and market_price <= limit_price:
            return min(limit_price, apply_slippage_to_price(market_price, side, slippage_bps))
        # Sell limit fills if market ≥ limit
        if not is_buy and market_price >= limit_price:
            return max(limit_price, apply_slippage_to_price(market_price, side, slippage_bps))
        return None

    if ot == OrderTypeEnum.STOP:
        if stop_price is None:
            return None
        is_buy = side in (OrderSideEnum.BUY.value, "BUY", "BUY_TO_COVER")
        if is_buy and market_price >= stop_price:
            return apply_slippage_to_price(market_price, side, slippage_bps)
        if not is_buy and market_price <= stop_price:
            return apply_slippage_to_price(market_price, side, slippage_bps)
        return None

    if ot == OrderTypeEnum.STOP_LIMIT:
        if stop_price is None or limit_price is None:
            return None
        is_buy = side in (OrderSideEnum.BUY.value, "BUY", "BUY_TO_COVER")
        stop_triggered = (is_buy and market_price >= stop_price) or (not is_buy and market_price <= stop_price)
        if not stop_triggered:
            return None
        # Now check limit
        if is_buy and market_price <= limit_price:
            return apply_slippage_to_price(market_price, side, slippage_bps)
        if not is_buy and market_price >= limit_price:
            return apply_slippage_to_price(market_price, side, slippage_bps)
        return None

    # MARKET fallback for other types
    return apply_slippage_to_price(market_price, side, slippage_bps)


# ---------------------------------------------------------------------------
# Account CRUD
# ---------------------------------------------------------------------------


def create_account(db: Session, name: str, initial_cash: Decimal, **kwargs) -> PaperAccount:
    account = PaperAccount(
        name=name,
        initial_cash=initial_cash,
        cash_balance=initial_cash,
        buying_power=initial_cash,
        total_equity=initial_cash,
        **kwargs,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_account(db: Session, account_id: uuid.UUID) -> Optional[PaperAccount]:
    return db.query(PaperAccount).filter(PaperAccount.id == account_id).first()


def list_accounts(db: Session, active_only: bool = True) -> List[PaperAccount]:
    q = db.query(PaperAccount)
    if active_only:
        q = q.filter(PaperAccount.is_active == True)  # noqa: E712
    return q.order_by(PaperAccount.created_at.desc()).all()


def get_position(db: Session, account_id: uuid.UUID, ticker: str) -> Optional[PaperPosition]:
    return (
        db.query(PaperPosition)
        .filter(PaperPosition.account_id == account_id, PaperPosition.ticker == ticker.upper())
        .first()
    )


def list_positions(db: Session, account_id: uuid.UUID) -> List[PaperPosition]:
    return db.query(PaperPosition).filter(PaperPosition.account_id == account_id).all()


def list_trades(
    db: Session,
    account_id: uuid.UUID,
    page: int = 1,
    page_size: int = 100,
) -> Tuple[List[PaperTrade], int]:
    q = db.query(PaperTrade).filter(PaperTrade.account_id == account_id)
    total = q.count()
    trades = q.order_by(PaperTrade.trade_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return trades, total


# ---------------------------------------------------------------------------
# Position update (AVCO)
# ---------------------------------------------------------------------------


def _update_position_buy(
    position: Optional[PaperPosition],
    account_id: uuid.UUID,
    ticker: str,
    qty: Decimal,
    fill_price: Decimal,
    db: Session,
) -> PaperPosition:
    if position is None:
        position = PaperPosition(
            account_id=account_id,
            ticker=ticker,
            quantity=Decimal("0"),
            average_cost=fill_price,
            cost_basis=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        db.add(position)

    new_total_qty = position.quantity + qty
    if new_total_qty > 0:
        position.average_cost = (position.quantity * position.average_cost + qty * fill_price) / new_total_qty
    position.cost_basis = position.average_cost * new_total_qty
    position.quantity = new_total_qty
    return position


def _update_position_sell(
    position: Optional[PaperPosition],
    qty: Decimal,
    fill_price: Decimal,
    db: Session,
) -> Tuple[PaperPosition, Decimal]:
    """Reduce position using AVCO; returns (position, realized_pnl)."""
    if position is None or position.quantity < qty:
        raise ValueError("Cannot sell more than current position quantity")

    realized_pnl = qty * (fill_price - position.average_cost)
    new_qty = position.quantity - qty
    position.quantity = new_qty
    position.cost_basis = position.average_cost * new_qty if new_qty > 0 else Decimal("0")
    position.realized_pnl += realized_pnl
    return position, realized_pnl


# ---------------------------------------------------------------------------
# Execute paper order (main entry point)
# ---------------------------------------------------------------------------


def execute_paper_order(
    db: Session,
    order: Order,
    market_price: Decimal,
) -> Optional[PaperTrade]:
    """Attempt to fill a paper order at the current market price.

    Returns a PaperTrade if filled, None if the order did not fill (e.g. limit
    not reached).  The caller must ensure the order.paper_account_id is set.
    """
    if order.paper_account_id is None:
        raise ValueError("Order must be linked to a paper account")

    account = get_account(db, order.paper_account_id)
    if account is None:
        raise ValueError(f"Paper account {order.paper_account_id} not found")

    order_type = order.order_type.value if hasattr(order.order_type, "value") else order.order_type
    side = order.side.value if hasattr(order.side, "value") else order.side
    limit_price = order.limit_price
    stop_price = order.stop_price

    fill_price = compute_fill_price(
        order_type=order_type,
        side=side,
        market_price=market_price,
        limit_price=limit_price,
        stop_price=stop_price,
        slippage_bps=account.slippage_bps,
    )

    if fill_price is None:
        return None  # order does not fill at current price

    fill_qty = order.quantity - order.filled_quantity
    if fill_qty <= 0:
        return None

    commission = compute_commission(
        fill_qty, fill_price,
        account.commission_type.value if hasattr(account.commission_type, "value") else account.commission_type,
        account.commission_rate,
        account.min_commission,
    )
    slippage_cost = compute_slippage_cost(fill_qty, market_price, account.slippage_bps)
    latency_ms = simulate_latency_ms()

    is_buy = side in (OrderSideEnum.BUY.value, "BUY", "BUY_TO_COVER")
    ticker = order.ticker.upper()
    realized_pnl = Decimal("0")

    if is_buy:
        total_cost = fill_qty * fill_price + commission
        if account.cash_balance < total_cost:
            # Reject due to insufficient funds
            order.status = OrderStatusEnum.REJECTED
            order.rejection_reason = "Insufficient buying power"
            db.commit()
            return None
        account.cash_balance -= total_cost
        position = get_position(db, account.id, ticker)
        position = _update_position_buy(position, account.id, ticker, fill_qty, fill_price, db)
    else:
        position = get_position(db, account.id, ticker)
        position, realized_pnl = _update_position_sell(position, fill_qty, fill_price, db)
        proceeds = fill_qty * fill_price - commission
        account.cash_balance += proceeds
        account.realized_pnl += realized_pnl

    # Record in OMS
    oms_service.record_partial_fill(
        db=db,
        order=order,
        fill_qty=fill_qty,
        fill_price=fill_price,
        commission=commission,
        slippage=slippage_cost,
        venue="PAPER",
        broker="PAPER",
        latency_ms=latency_ms,
    )

    # Record PaperTrade (immutable history)
    trade = PaperTrade(
        account_id=account.id,
        order_id=order.id,
        ticker=ticker,
        side=side,
        quantity=fill_qty,
        fill_price=fill_price,
        market_price_at_fill=market_price,
        commission=commission,
        slippage_cost=slippage_cost,
        realized_pnl=realized_pnl,
        strategy_tag=order.strategy_tag,
        trade_time=datetime.now(timezone.utc),
    )
    db.add(trade)

    # Recompute account equity
    all_positions = list_positions(db, account.id)
    # market values are stale but we'll update the position we just touched
    position.last_price = fill_price
    position.market_value = position.quantity * fill_price
    position.unrealized_pnl = position.quantity * (fill_price - position.average_cost)
    total_market_value = sum(p.market_value for p in all_positions)
    account.total_market_value = total_market_value
    account.total_equity = account.cash_balance + total_market_value
    account.buying_power = account.cash_balance
    account.unrealized_pnl = sum(p.unrealized_pnl for p in all_positions)

    db.commit()
    db.refresh(trade)
    return trade


# ---------------------------------------------------------------------------
# Refresh position market values
# ---------------------------------------------------------------------------


def refresh_position_prices(db: Session, account_id: uuid.UUID) -> PaperAccount:
    """Update all position market values and account equity using current prices."""
    from services.quotes import get_current_prices

    account = get_account(db, account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found")

    positions = list_positions(db, account_id)
    if not positions:
        account.total_market_value = Decimal("0")
        account.total_equity = account.cash_balance
        account.unrealized_pnl = Decimal("0")
        db.commit()
        db.refresh(account)
        return account

    tickers = [p.ticker for p in positions]
    prices = get_current_prices(tickers)

    total_market_value = Decimal("0")
    total_unrealized = Decimal("0")
    for pos in positions:
        price = prices.get(pos.ticker)
        if price is not None:
            pos.last_price = price
            pos.market_value = pos.quantity * price
            pos.unrealized_pnl = pos.quantity * (price - pos.average_cost)
        total_market_value += pos.market_value
        total_unrealized += pos.unrealized_pnl

    account.total_market_value = total_market_value
    account.total_equity = account.cash_balance + total_market_value
    account.buying_power = account.cash_balance
    account.unrealized_pnl = total_unrealized

    db.commit()
    db.refresh(account)
    return account


# ---------------------------------------------------------------------------
# Account summary
# ---------------------------------------------------------------------------


def get_account_summary(db: Session, account_id: uuid.UUID) -> Dict[str, Any]:
    account = get_account(db, account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found")

    positions = list_positions(db, account_id)
    open_orders = db.query(Order).filter(
        Order.paper_account_id == account_id,
        Order.status.in_([
            OrderStatusEnum.PENDING.value,
            OrderStatusEnum.SUBMITTED.value,
            OrderStatusEnum.ACCEPTED.value,
            OrderStatusEnum.PARTIALLY_FILLED.value,
        ]),
    ).count()

    total_trades = db.query(PaperTrade).filter(PaperTrade.account_id == account_id).count()

    from sqlalchemy import func as sqlfunc
    comm_result = db.query(sqlfunc.sum(PaperTrade.commission)).filter(PaperTrade.account_id == account_id).scalar()
    slip_result = db.query(sqlfunc.sum(PaperTrade.slippage_cost)).filter(PaperTrade.account_id == account_id).scalar()

    total_commission = Decimal(str(comm_result or 0))
    total_slippage = Decimal(str(slip_result or 0))

    return_pct = (
        (account.total_equity - account.initial_cash) / account.initial_cash * Decimal("100")
        if account.initial_cash > 0
        else Decimal("0")
    )

    return {
        "account": account,
        "positions": positions,
        "open_orders_count": open_orders,
        "total_trades": total_trades,
        "total_commission_paid": total_commission,
        "total_slippage_cost": total_slippage,
        "return_pct": return_pct,
    }
