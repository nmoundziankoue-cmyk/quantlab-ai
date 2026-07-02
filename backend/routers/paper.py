"""Paper Trading router.

Endpoints:
  POST   /paper/accounts                          Create paper account
  GET    /paper/accounts                          List paper accounts
  GET    /paper/accounts/{account_id}             Account summary + positions
  PATCH  /paper/accounts/{account_id}             Update account settings
  DELETE /paper/accounts/{account_id}             Deactivate account
  POST   /paper/accounts/{account_id}/refresh     Refresh position market values
  POST   /paper/accounts/{account_id}/orders      Submit an order to paper engine
  GET    /paper/accounts/{account_id}/positions   List positions
  GET    /paper/accounts/{account_id}/trades      Trade history
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.trading import (
    OrderCreate,
    OrderResponse,
    PaperAccountCreate,
    PaperAccountResponse,
    PaperAccountSummary,
    PaperAccountUpdate,
    PaperPositionResponse,
    PaperTradeResponse,
)
from services import paper_trading as paper_service
from services import oms as oms_service
from services.streaming import publish_event

router = APIRouter(prefix="/paper", tags=["paper-trading"])


@router.post("/accounts", response_model=PaperAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(body: PaperAccountCreate, db: Session = Depends(get_db)) -> PaperAccountResponse:
    account = paper_service.create_account(
        db,
        name=body.name,
        initial_cash=body.initial_cash,
        description=body.description,
        currency=body.currency,
        commission_type=body.commission_type,
        commission_rate=body.commission_rate,
        min_commission=body.min_commission,
        slippage_bps=body.slippage_bps,
    )
    return PaperAccountResponse.model_validate(account)


@router.get("/accounts", response_model=List[PaperAccountResponse])
def list_accounts(
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> List[PaperAccountResponse]:
    accounts = paper_service.list_accounts(db, active_only=active_only)
    return [PaperAccountResponse.model_validate(a) for a in accounts]


@router.get("/accounts/{account_id}", response_model=PaperAccountSummary)
def get_account_summary(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PaperAccountSummary:
    try:
        summary = paper_service.get_account_summary(db, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    account = summary["account"]
    positions = summary["positions"]

    return PaperAccountSummary(
        **PaperAccountResponse.model_validate(account).model_dump(),
        positions=[PaperPositionResponse.model_validate(p) for p in positions],
        open_orders_count=summary["open_orders_count"],
        total_trades=summary["total_trades"],
        total_commission_paid=summary["total_commission_paid"],
        total_slippage_cost=summary["total_slippage_cost"],
        return_pct=summary["return_pct"],
    )


@router.patch("/accounts/{account_id}", response_model=PaperAccountResponse)
def update_account(
    account_id: uuid.UUID,
    body: PaperAccountUpdate,
    db: Session = Depends(get_db),
) -> PaperAccountResponse:
    account = paper_service.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if hasattr(account, key):
            setattr(account, key, val)
    db.commit()
    db.refresh(account)
    return PaperAccountResponse.model_validate(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_account(account_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    account = paper_service.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    account.is_active = False
    db.commit()


@router.post("/accounts/{account_id}/refresh", response_model=PaperAccountResponse)
def refresh_prices(account_id: uuid.UUID, db: Session = Depends(get_db)) -> PaperAccountResponse:
    try:
        account = paper_service.refresh_position_prices(db, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PaperAccountResponse.model_validate(account)


@router.post("/accounts/{account_id}/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def submit_paper_order(
    account_id: uuid.UUID,
    body: OrderCreate,
    db: Session = Depends(get_db),
) -> OrderResponse:
    account = paper_service.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    from services.quotes import get_current_prices
    prices = get_current_prices([body.ticker])
    market_price = prices.get(body.ticker.upper())

    is_valid, errors = oms_service.validate_order(body, account.cash_balance, market_price)
    if not is_valid:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    order = oms_service.create_order(db, body, paper_account_id=account_id)
    order = oms_service.mark_submitted(db, order)

    if market_price:
        trade = paper_service.execute_paper_order(db, order, market_price)
        db.refresh(order)
        if trade:
            publish_event("executions", {
                "type": "PAPER_FILL",
                "account_id": str(account_id),
                "ticker": order.ticker,
                "side": body.side if isinstance(body.side, str) else body.side.value,
                "quantity": str(order.filled_quantity),
                "fill_price": str(order.average_fill_price),
            })
            publish_event("positions", {"account_id": str(account_id)})

    return OrderResponse.model_validate(order)


@router.get("/accounts/{account_id}/positions", response_model=List[PaperPositionResponse])
def list_positions(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> List[PaperPositionResponse]:
    account = paper_service.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    positions = paper_service.list_positions(db, account_id)
    return [PaperPositionResponse.model_validate(p) for p in positions]


@router.get("/accounts/{account_id}/trades", response_model=Dict[str, Any])
def list_trades(
    account_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    account = paper_service.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    trades, total = paper_service.list_trades(db, account_id, page=page, page_size=page_size)
    return {
        "trades": [PaperTradeResponse.model_validate(t).model_dump() for t in trades],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
