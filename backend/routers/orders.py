"""Orders router — full OMS REST API.

Endpoints:
  POST   /orders                              Create order (portfolio or paper account)
  GET    /orders                              List orders (filterable)
  GET    /orders/{order_id}                   Get single order
  PATCH  /orders/{order_id}                   Modify order
  DELETE /orders/{order_id}                   Cancel order
  POST   /orders/{order_id}/submit            Submit PENDING order to execution
  GET    /orders/{order_id}/audit             Get audit log
  POST   /orders/preview                      Preview / simulate an order
  POST   /orders/basket                       Create basket (multi-leg) order
  GET    /orders/basket/{basket_id}           List basket orders
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.trading import OrderStatusEnum
from schemas.trading import (
    AuditLogEntry,
    BasketOrderCreate,
    BasketOrderResponse,
    OrderCreate,
    OrderListResponse,
    OrderModify,
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderResponse,
)
from services import oms as oms_service
from services import paper_trading as paper_service

router = APIRouter(prefix="/orders", tags=["orders"])


def _get_market_price(ticker: str) -> Optional[Decimal]:
    try:
        from services.quotes import get_current_prices
        prices = get_current_prices([ticker])
        return prices.get(ticker)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Create order
# ---------------------------------------------------------------------------


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    body: OrderCreate,
    portfolio_id: Optional[uuid.UUID] = Query(default=None),
    paper_account_id: Optional[uuid.UUID] = Query(default=None),
    broker_connection_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
) -> OrderResponse:
    if portfolio_id is None and paper_account_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either portfolio_id or paper_account_id must be provided",
        )

    # Validate buying power for paper accounts
    if paper_account_id:
        account = paper_service.get_account(db, paper_account_id)
        if account is None:
            raise HTTPException(status_code=404, detail=f"Paper account {paper_account_id} not found")
        market_price = _get_market_price(body.ticker)
        is_valid, errors = oms_service.validate_order(body, account.cash_balance, market_price)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"validation_errors": errors},
            )

    order = oms_service.create_order(
        db, body,
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        broker_connection_id=broker_connection_id,
    )
    return OrderResponse.model_validate(order)


# ---------------------------------------------------------------------------
# List orders
# ---------------------------------------------------------------------------


@router.get("", response_model=OrderListResponse)
def list_orders(
    portfolio_id: Optional[uuid.UUID] = Query(default=None),
    paper_account_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    ticker: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    orders, total = oms_service.list_orders(
        db,
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        status=status_filter,
        ticker=ticker,
        page=page,
        page_size=page_size,
    )
    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Get single order
# ---------------------------------------------------------------------------


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderResponse:
    order = oms_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return OrderResponse.model_validate(order)


# ---------------------------------------------------------------------------
# Modify order
# ---------------------------------------------------------------------------


@router.patch("/{order_id}", response_model=OrderResponse)
def modify_order(
    order_id: uuid.UUID,
    body: OrderModify,
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        order = oms_service.modify_order(db, order_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return OrderResponse.model_validate(order)


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------


@router.delete("/{order_id}", response_model=OrderResponse)
def cancel_order(
    order_id: uuid.UUID,
    reason: str = Query(default="User requested"),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        order = oms_service.cancel_order(db, order_id, reason=reason)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return OrderResponse.model_validate(order)


# ---------------------------------------------------------------------------
# Submit order to execution (paper or broker)
# ---------------------------------------------------------------------------


@router.post("/{order_id}/submit", response_model=OrderResponse)
def submit_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderResponse:
    order = oms_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    status_val = order.status.value if hasattr(order.status, "value") else order.status
    if status_val != OrderStatusEnum.PENDING.value:
        raise HTTPException(status_code=422, detail=f"Can only submit PENDING orders, got {status_val}")

    order = oms_service.mark_submitted(db, order)

    # If this is a paper order, attempt immediate fill
    if order.paper_account_id:
        market_price = _get_market_price(order.ticker)
        if market_price:
            paper_service.execute_paper_order(db, order, market_price)
            db.refresh(order)

    return OrderResponse.model_validate(order)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@router.get("/{order_id}/audit", response_model=List[AuditLogEntry])
def get_audit_log(order_id: uuid.UUID, db: Session = Depends(get_db)) -> List[AuditLogEntry]:
    order = oms_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    log = oms_service.get_audit_log(db, order_id)
    return [AuditLogEntry.model_validate(entry) for entry in log]


# ---------------------------------------------------------------------------
# Order preview / simulation
# ---------------------------------------------------------------------------


@router.post("/preview", response_model=OrderPreviewResponse)
def preview_order(body: OrderPreviewRequest, db: Session = Depends(get_db)) -> OrderPreviewResponse:
    market_price = _get_market_price(body.ticker)
    if market_price is None:
        raise HTTPException(status_code=503, detail=f"Cannot fetch market price for {body.ticker}")

    # Convert OrderPreviewRequest to an OrderCreate-compatible object for simulation
    from schemas.trading import OrderCreate as OC
    from models.trading import OrderTypeEnum, OrderSideEnum, TimeInForceEnum
    oc = OC(
        ticker=body.ticker,
        order_type=body.order_type,
        side=body.side,
        quantity=body.quantity,
        limit_price=body.limit_price,
        stop_price=body.stop_price,
    )
    result = oms_service.simulate_order(oc, market_price)
    return OrderPreviewResponse(**result)


# ---------------------------------------------------------------------------
# Basket orders
# ---------------------------------------------------------------------------


@router.post("/basket", response_model=BasketOrderResponse, status_code=status.HTTP_201_CREATED)
def create_basket_order(
    body: BasketOrderCreate,
    portfolio_id: Optional[uuid.UUID] = Query(default=None),
    paper_account_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
) -> BasketOrderResponse:
    if portfolio_id is None and paper_account_id is None:
        raise HTTPException(status_code=422, detail="Either portfolio_id or paper_account_id required")

    # Convert basket items to OrderCreate objects
    from schemas.trading import OrderCreate as OC
    order_creates = [
        OC(
            ticker=item.ticker,
            side=item.side,
            quantity=item.quantity,
            order_type=item.order_type,
            limit_price=item.limit_price,
            time_in_force=body.time_in_force,
            strategy_tag=item.strategy_tag,
            notes=body.notes,
            tags=body.tags,
        )
        for item in body.items
    ]

    basket_id, orders = oms_service.create_basket_order(
        db, order_creates,
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
    )

    return BasketOrderResponse(
        basket_id=basket_id,
        orders=[OrderResponse.model_validate(o) for o in orders],
        total_items=len(orders),
        submitted_at=datetime.utcnow().replace(tzinfo=None),
    )


@router.get("/basket/{basket_id}", response_model=List[OrderResponse])
def list_basket(basket_id: uuid.UUID, db: Session = Depends(get_db)) -> List[OrderResponse]:
    orders = oms_service.list_basket_orders(db, basket_id)
    return [OrderResponse.model_validate(o) for o in orders]
