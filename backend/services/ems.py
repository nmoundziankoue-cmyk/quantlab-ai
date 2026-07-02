"""Execution Management System (EMS).

Tracks the state and quality of all executions.  The EMS is the read-layer
for execution data; writes happen via the OMS (record_partial_fill) and the
paper trading engine.

Responsibilities:
  - Query executions (by order, ticker, date range)
  - Compute per-order execution quality metrics (fill ratio, slippage, IS)
  - Build the institutional trade blotter with full detail and CSV export
  - Aggregate execution statistics (for the analytics dashboard)
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from models.trading import Execution, Order, OrderStatusEnum


# ---------------------------------------------------------------------------
# Execution queries
# ---------------------------------------------------------------------------


def get_execution(db: Session, execution_id: uuid.UUID) -> Optional[Execution]:
    return db.query(Execution).filter(Execution.id == execution_id).first()


def list_executions(
    db: Session,
    order_id: Optional[uuid.UUID] = None,
    ticker: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    venue: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> Tuple[List[Execution], int]:
    q = db.query(Execution)
    if order_id:
        q = q.filter(Execution.order_id == order_id)
    if ticker:
        q = q.filter(Execution.ticker == ticker.upper())
    if since:
        q = q.filter(Execution.execution_time >= since)
    if until:
        q = q.filter(Execution.execution_time <= until)
    if venue:
        q = q.filter(Execution.venue == venue.upper())
    total = q.count()
    execs = q.order_by(Execution.execution_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return execs, total


def list_executions_for_order(db: Session, order_id: uuid.UUID) -> List[Execution]:
    return (
        db.query(Execution)
        .filter(Execution.order_id == order_id)
        .order_by(Execution.execution_time.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Execution Quality
# ---------------------------------------------------------------------------


def compute_execution_quality(db: Session, order_id: uuid.UUID) -> Dict[str, Any]:
    """Compute execution quality metrics for a single order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise ValueError(f"Order {order_id} not found")

    executions = list_executions_for_order(db, order_id)

    ordered_qty = order.quantity
    filled_qty = order.filled_quantity
    avg_fill = order.average_fill_price

    fill_ratio = float(filled_qty / ordered_qty) if ordered_qty > 0 else 0.0
    total_commission = sum(e.commission for e in executions)

    first_exec_time = executions[0].execution_time if executions else None
    last_exec_time = executions[-1].execution_time if executions else None
    execution_time_ms = None
    if first_exec_time and last_exec_time:
        delta = (last_exec_time - first_exec_time).total_seconds() * 1000
        execution_time_ms = int(delta)

    # Implementation Shortfall: (avg_fill - arrival_price) / arrival_price in bps
    # arrival_price is approximated as first fill's market_price_at_fill
    arrival_price = executions[0].market_price_at_fill if executions else None
    is_bps = None
    if arrival_price and avg_fill:
        is_bps = float((avg_fill - arrival_price) / arrival_price * 10000)

    slippage_bps = None
    if arrival_price and avg_fill and arrival_price > 0:
        slippage_bps = float((avg_fill - arrival_price) / arrival_price * 10000)

    # Quality score: 100 = perfect fill at arrival price; docked for slippage and partial fills
    quality_score = 100.0
    if fill_ratio < 1.0:
        quality_score -= (1.0 - fill_ratio) * 50
    if slippage_bps:
        quality_score -= min(abs(slippage_bps) * 0.5, 40)
    quality_score = max(0.0, quality_score)

    return {
        "order_id": order_id,
        "ticker": order.ticker,
        "side": order.side.value if hasattr(order.side, "value") else order.side,
        "ordered_qty": ordered_qty,
        "filled_qty": filled_qty,
        "avg_fill_price": avg_fill,
        "arrival_price": arrival_price,
        "implementation_shortfall_bps": is_bps,
        "vwap_benchmark": None,  # would require VWAP data feed
        "vwap_slippage_bps": None,
        "fill_ratio": fill_ratio,
        "total_commission": total_commission,
        "execution_time_ms": execution_time_ms,
        "quality_score": quality_score,
    }


# ---------------------------------------------------------------------------
# Trade Blotter
# ---------------------------------------------------------------------------


def build_blotter_row(order: Order, execution: Execution) -> Dict[str, Any]:
    fill_price = execution.fill_price
    market_price = execution.market_price_at_fill or fill_price
    gross_value = execution.quantity * fill_price
    net_value = gross_value - execution.commission
    slippage_bps = None
    if market_price and fill_price and market_price > 0:
        slippage_bps = float((fill_price - market_price) / market_price * 10000)

    return {
        "execution_id": execution.id,
        "order_id": order.id,
        "trade_date": execution.execution_time.strftime("%Y-%m-%d"),
        "execution_time": execution.execution_time,
        "ticker": execution.ticker,
        "side": execution.side,
        "quantity": execution.quantity,
        "fill_price": fill_price,
        "gross_value": gross_value,
        "commission": execution.commission,
        "slippage": execution.slippage,
        "net_value": net_value,
        "venue": execution.venue,
        "broker": execution.broker,
        "strategy_tag": order.strategy_tag,
        "notes": order.notes,
        "order_type": order.order_type.value if hasattr(order.order_type, "value") else order.order_type,
        "latency_ms": execution.latency_ms,
        "market_price_at_fill": execution.market_price_at_fill,
        "execution_quality_bps": slippage_bps,
    }


def get_blotter(
    db: Session,
    portfolio_id: Optional[uuid.UUID] = None,
    paper_account_id: Optional[uuid.UUID] = None,
    ticker: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    side: Optional[str] = None,
    strategy_tag: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
    """Return blotter rows, total count, and summary statistics."""
    exec_q = db.query(Execution, Order).join(Order, Execution.order_id == Order.id)

    if portfolio_id:
        exec_q = exec_q.filter(Order.portfolio_id == portfolio_id)
    if paper_account_id:
        exec_q = exec_q.filter(Order.paper_account_id == paper_account_id)
    if ticker:
        exec_q = exec_q.filter(Execution.ticker == ticker.upper())
    if since:
        exec_q = exec_q.filter(Execution.execution_time >= since)
    if until:
        exec_q = exec_q.filter(Execution.execution_time <= until)
    if side:
        exec_q = exec_q.filter(Execution.side == side.upper())
    if strategy_tag:
        exec_q = exec_q.filter(Order.strategy_tag == strategy_tag)

    total = exec_q.count()
    pairs = (
        exec_q.order_by(Execution.execution_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    rows = [build_blotter_row(order, execution) for execution, order in pairs]

    # Summary
    all_pairs = exec_q.all()
    total_volume = sum(e.quantity * e.fill_price for e, _ in all_pairs)
    total_commission = sum(e.commission for e, _ in all_pairs)
    total_slippage = sum(e.slippage for e, _ in all_pairs)
    summary = {
        "total_trades": total,
        "total_volume": total_volume,
        "total_commission": total_commission,
        "total_slippage_cost": total_slippage,
        "net_total_value": total_volume - total_commission,
    }

    return rows, total, summary


def export_blotter_csv(
    db: Session,
    portfolio_id: Optional[uuid.UUID] = None,
    paper_account_id: Optional[uuid.UUID] = None,
) -> str:
    rows, _, _ = get_blotter(
        db,
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        page=1,
        page_size=10_000,
    )
    output = io.StringIO()
    if not rows:
        return ""

    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        # Convert non-serialisable types
        serializable = {k: (str(v) if isinstance(v, (uuid.UUID, Decimal, datetime)) else v) for k, v in row.items()}
        writer.writerow(serializable)

    return output.getvalue()


# ---------------------------------------------------------------------------
# Execution Analytics Aggregation
# ---------------------------------------------------------------------------


def get_execution_analytics(
    db: Session,
    portfolio_id: Optional[uuid.UUID] = None,
    paper_account_id: Optional[uuid.UUID] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Aggregate execution analytics over a time window."""
    exec_q = db.query(Execution, Order).join(Order, Execution.order_id == Order.id)

    if portfolio_id:
        exec_q = exec_q.filter(Order.portfolio_id == portfolio_id)
    if paper_account_id:
        exec_q = exec_q.filter(Order.paper_account_id == paper_account_id)
    if since:
        exec_q = exec_q.filter(Execution.execution_time >= since)
    if until:
        exec_q = exec_q.filter(Execution.execution_time <= until)

    pairs = exec_q.all()
    if not pairs:
        now = datetime.now(timezone.utc)
        return {
            "period_start": since or now,
            "period_end": until or now,
            "total_trades": 0,
            "total_volume": Decimal("0"),
            "fill_ratio": 0.0,
            "avg_slippage_bps": 0.0,
            "avg_commission_per_trade": Decimal("0"),
            "total_commission": Decimal("0"),
            "total_slippage_cost": Decimal("0"),
            "avg_latency_ms": None,
            "win_rate": 0.0,
            "avg_holding_period_days": None,
            "turnover": Decimal("0"),
            "by_ticker": [],
            "slippage_distribution": [],
        }

    executions = [e for e, _ in pairs]
    orders = [o for _, o in pairs]

    total = len(executions)
    total_volume = sum(e.quantity * e.fill_price for e in executions)
    total_commission = sum(e.commission for e in executions)
    total_slippage = sum(e.slippage for e in executions)
    latencies = [e.latency_ms for e in executions if e.latency_ms is not None]

    # Slippage in bps per execution
    slippage_bps_list: List[float] = []
    for e in executions:
        if e.market_price_at_fill and e.market_price_at_fill > 0:
            bps = float((e.fill_price - e.market_price_at_fill) / e.market_price_at_fill * 10000)
            slippage_bps_list.append(bps)

    avg_slippage_bps = sum(slippage_bps_list) / len(slippage_bps_list) if slippage_bps_list else 0.0

    # Fill ratio: sum(filled_qty) / sum(ordered_qty) across unique orders
    unique_order_ids = {e.order_id for e in executions}
    unique_orders = db.query(Order).filter(Order.id.in_(unique_order_ids)).all()
    total_ordered = sum(o.quantity for o in unique_orders)
    total_filled = sum(o.filled_quantity for o in unique_orders)
    fill_ratio = float(total_filled / total_ordered) if total_ordered > 0 else 0.0

    # Win rate: realized PnL > 0 per sell trade
    sells = [e for e in executions if e.side in ("SELL", "SELL_SHORT")]
    # approximate: fill_price > order average_cost — requires joining position data
    # We use a simpler proxy: slippage_bps < 0 (meaning we sold higher than arrival)
    win_trades = sum(1 for bps in slippage_bps_list if bps < 0)
    win_rate = win_trades / len(slippage_bps_list) if slippage_bps_list else 0.0

    # By-ticker breakdown
    by_ticker: Dict[str, Dict[str, Any]] = {}
    for e in executions:
        t = e.ticker
        if t not in by_ticker:
            by_ticker[t] = {"ticker": t, "trades": 0, "volume": Decimal("0"), "commission": Decimal("0")}
        by_ticker[t]["trades"] += 1
        by_ticker[t]["volume"] += e.quantity * e.fill_price
        by_ticker[t]["commission"] += e.commission

    # Slippage histogram (0-2 bps, 2-5 bps, 5-10 bps, 10+ bps)
    buckets = [(0, 2), (2, 5), (5, 10), (10, float("inf"))]
    distribution = []
    for lo, hi in buckets:
        count = sum(1 for bps in slippage_bps_list if lo <= abs(bps) < hi)
        distribution.append({"label": f"{lo}-{int(hi) if hi != float('inf') else '10+'}bps", "count": count})

    exec_times = [e.execution_time for e in executions]
    period_start = min(exec_times) if exec_times else (since or datetime.now(timezone.utc))
    period_end = max(exec_times) if exec_times else (until or datetime.now(timezone.utc))

    return {
        "period_start": period_start,
        "period_end": period_end,
        "total_trades": total,
        "total_volume": total_volume,
        "fill_ratio": fill_ratio,
        "avg_slippage_bps": avg_slippage_bps,
        "avg_commission_per_trade": total_commission / total if total > 0 else Decimal("0"),
        "total_commission": total_commission,
        "total_slippage_cost": total_slippage,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "win_rate": win_rate,
        "avg_holding_period_days": None,
        "turnover": total_volume,
        "by_ticker": list(by_ticker.values()),
        "slippage_distribution": distribution,
    }
