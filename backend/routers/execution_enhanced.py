"""M9 Phase 8 — Enhanced execution engine API."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from services.execution_enhanced import (
    Order, OrderType, OrderSide, get_execution_engine, OrderBookSimulator, RiskLimits
)

router = APIRouter(prefix="/execution/enhanced", tags=["execution_enhanced"])


class OrderRequest(BaseModel):
    ticker: str
    side: str               # buy | sell
    order_type: str = "market"
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    trail_pct: Optional[float] = None
    trail_amount: Optional[float] = None
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    time_in_force: str = "DAY"
    market_price: float = 100.0  # required for simulation


@router.post("/orders")
def submit_order(req: OrderRequest):
    order = Order(
        ticker=req.ticker,
        side=OrderSide(req.side),
        order_type=OrderType(req.order_type),
        quantity=req.quantity,
        limit_price=req.limit_price,
        stop_price=req.stop_price,
        trail_pct=req.trail_pct,
        trail_amount=req.trail_amount,
        take_profit_price=req.take_profit_price,
        stop_loss_price=req.stop_loss_price,
        time_in_force=req.time_in_force,
    )
    return get_execution_engine().submit_order(order, req.market_price)


@router.get("/orders")
def list_orders(status: Optional[str] = None, ticker: Optional[str] = None):
    return {"orders": get_execution_engine().list_orders(status, ticker)}


@router.get("/orders/{order_id}")
def get_order(order_id: str):
    order = get_execution_engine().get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return get_execution_engine()._order_to_dict(order)


@router.delete("/orders/{order_id}")
def cancel_order(order_id: str):
    ok = get_execution_engine().cancel_order(order_id)
    if not ok:
        raise HTTPException(400, "Cannot cancel — order not found or already filled/cancelled")
    return {"cancelled": order_id}


@router.get("/reports")
def execution_reports(limit: int = Query(50, le=200)):
    return {"reports": get_execution_engine().execution_reports(limit)}


@router.get("/latency")
def latency_stats():
    return get_execution_engine().latency_stats()


@router.get("/book")
def order_book(mid_price: float = Query(100.0), spread_bps: float = Query(5.0)):
    book = OrderBookSimulator(mid_price, spread_bps)
    return book.to_dict()
