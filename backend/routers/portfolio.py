"""Portfolio REST router (M10 Phase 7: auth + ownership + risk snapshots).

All portfolio-domain endpoints are defined here and mounted on the FastAPI app
at the prefix ``/portfolios``.

Auth: write endpoints require a valid JWT. Read endpoints work with or without
auth — when authenticated, results are scoped to the current user's portfolios.

Error mapping:
  PortfolioNotFoundError    → 404
  InsufficientSharesError   → 409
  TransactionNotFoundError  → 404
  ValidationError (Pydantic) → 422 (handled automatically by FastAPI)
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from middleware.rbac import get_current_user_payload, get_optional_user_payload
from schemas.portfolio import (
    AllocationRead,
    PerformanceRead,
    PortfolioCreate,
    PortfolioRead,
    PortfolioSummaryRead,
    PortfolioUpdate,
    TransactionCreate,
    TransactionRead,
)
from services.performance import compute_allocation, compute_performance
from services.portfolio import (
    PortfolioNotFoundError,
    create_portfolio,
    delete_portfolio,
    get_portfolio,
    list_portfolios,
    list_risk_snapshots,
    save_risk_snapshot,
    update_portfolio,
)
from services.transaction import (
    InsufficientSharesError,
    TransactionNotFoundError,
    add_transaction,
    compute_portfolio_summary,
    delete_transaction,
    list_transactions,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])

# ---------------------------------------------------------------------------
# Type aliases — keep signatures concise
# ---------------------------------------------------------------------------

DbSession = Annotated[Session, Depends(get_db)]
OptionalUser = Annotated[Optional[dict], Depends(get_optional_user_payload)]
AuthUser = Annotated[dict, Depends(get_current_user_payload)]


def _owner_id(user_payload: Optional[dict]) -> Optional[uuid.UUID]:
    """Extract UUID owner_id from JWT payload, or None for anonymous."""
    if not user_payload:
        return None
    sub = user_payload.get("sub")
    try:
        return uuid.UUID(str(sub))
    except (ValueError, TypeError):
        return None


# ===========================================================================
# Portfolio CRUD
# ===========================================================================

@router.get("", response_model=list[PortfolioRead], summary="List portfolios")
def route_list_portfolios(
    db: DbSession,
    user: OptionalUser,
) -> list[PortfolioRead]:
    """Return portfolios. When authenticated, scoped to the caller's portfolios."""
    return list(list_portfolios(db, owner_id=_owner_id(user)))


@router.post(
    "",
    response_model=PortfolioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a portfolio",
)
def route_create_portfolio(
    payload: PortfolioCreate,
    db: DbSession,
    user: AuthUser,
) -> PortfolioRead:
    """Persist a new portfolio record (auth required)."""
    return create_portfolio(db, payload, owner_id=_owner_id(user))


@router.get("/{portfolio_id}", response_model=PortfolioRead, summary="Get a portfolio")
def route_get_portfolio(
    portfolio_id: uuid.UUID,
    db: DbSession,
) -> PortfolioRead:
    """Fetch a single portfolio by its UUID."""
    try:
        return get_portfolio(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


@router.put("/{portfolio_id}", response_model=PortfolioRead, summary="Update a portfolio")
def route_update_portfolio(
    portfolio_id: uuid.UUID,
    payload: PortfolioUpdate,
    db: DbSession,
) -> PortfolioRead:
    """Partially update a portfolio.  Only supplied fields are written."""
    try:
        return update_portfolio(db, portfolio_id, payload)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a portfolio",
)
def route_delete_portfolio(
    portfolio_id: uuid.UUID,
    db: DbSession,
) -> None:
    """Permanently delete a portfolio and all its transactions (cascade)."""
    try:
        delete_portfolio(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


# ===========================================================================
# Portfolio computed views
# ===========================================================================

@router.get(
    "/{portfolio_id}/summary",
    response_model=PortfolioSummaryRead,
    summary="Portfolio snapshot KPIs",
)
def route_portfolio_summary(
    portfolio_id: uuid.UUID,
    db: DbSession,
) -> PortfolioSummaryRead:
    """Return current holdings and aggregate KPIs computed from the transaction ledger."""
    try:
        return compute_portfolio_summary(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


@router.get(
    "/{portfolio_id}/performance",
    response_model=PerformanceRead,
    summary="NAV series and performance metrics",
)
def route_portfolio_performance(
    portfolio_id: uuid.UUID,
    db: DbSession,
) -> PerformanceRead:
    """Compute the daily NAV series vs benchmark and scalar return/risk metrics."""
    try:
        return compute_performance(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data unavailable: {exc}",
        )


@router.get(
    "/{portfolio_id}/allocation",
    response_model=AllocationRead,
    summary="Allocation by ticker and sector",
)
def route_portfolio_allocation(
    portfolio_id: uuid.UUID,
    db: DbSession,
) -> AllocationRead:
    """Return position weights broken down by ticker and GICS sector."""
    try:
        return compute_allocation(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


# ===========================================================================
# Transactions
# ===========================================================================

@router.get(
    "/{portfolio_id}/transactions",
    response_model=list[TransactionRead],
    summary="List transactions",
)
def route_list_transactions(
    portfolio_id: uuid.UUID,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TransactionRead]:
    """Return paginated transactions for a portfolio, newest first."""
    try:
        get_portfolio(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return list(list_transactions(db, portfolio_id, limit=limit, offset=offset))


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new transaction",
)
def route_add_transaction(
    portfolio_id: uuid.UUID,
    payload: TransactionCreate,
    db: DbSession,
) -> TransactionRead:
    """Validate and persist a new transaction against the portfolio's ledger.

    Returns HTTP 409 if a SELL order exceeds the current position.
    """
    try:
        get_portfolio(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    try:
        return add_transaction(db, portfolio_id, payload)
    except InsufficientSharesError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.delete(
    "/{portfolio_id}/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction",
)
def route_delete_transaction(
    portfolio_id: uuid.UUID,
    transaction_id: uuid.UUID,
    db: DbSession,
) -> None:
    """Remove a transaction from the portfolio's ledger."""
    try:
        delete_transaction(db, portfolio_id, transaction_id)
    except TransactionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )


# ===========================================================================
# Risk snapshots (M10 Phase 7)
# ===========================================================================

@router.get(
    "/{portfolio_id}/risk-snapshots",
    summary="List risk snapshots",
)
def route_list_risk_snapshots(
    portfolio_id: uuid.UUID,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> dict:
    """Return the most recent persisted risk snapshots for a portfolio."""
    try:
        get_portfolio(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    snaps = list_risk_snapshots(db, portfolio_id, limit=limit)
    return {
        "portfolio_id": str(portfolio_id),
        "snapshots": [
            {
                "id": str(s.id),
                "taken_at": s.taken_at.isoformat(),
                "total_value": float(s.total_value) if s.total_value is not None else None,
                "total_pnl": float(s.total_pnl) if s.total_pnl is not None else None,
                "total_pnl_pct": float(s.total_pnl_pct) if s.total_pnl_pct is not None else None,
                "positions_count": s.positions_count,
                "metadata": s.metadata_json,
            }
            for s in snaps
        ],
        "total": len(snaps),
    }


@router.post(
    "/{portfolio_id}/risk-snapshots",
    status_code=status.HTTP_201_CREATED,
    summary="Take a risk snapshot",
)
def route_take_risk_snapshot(
    portfolio_id: uuid.UUID,
    db: DbSession,
    user: AuthUser,
) -> dict:
    """Compute and persist a point-in-time risk snapshot (auth required)."""
    try:
        summary = compute_portfolio_summary(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    total_value = Decimal(str(summary.total_value)) if summary.total_value else None
    total_pnl = Decimal(str(summary.total_pnl)) if summary.total_pnl else None
    total_pnl_pct = None
    if total_value and total_pnl and total_value > 0:
        cost_basis = total_value - total_pnl
        total_pnl_pct = total_pnl / cost_basis * 100 if cost_basis else None

    snap = save_risk_snapshot(
        db,
        portfolio_id=portfolio_id,
        total_value=total_value,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        positions_count=len(summary.holdings) if summary.holdings else 0,
        metadata={"triggered_by": user.get("sub"), "source": "manual"},
    )
    return {
        "id": str(snap.id),
        "portfolio_id": str(portfolio_id),
        "taken_at": snap.taken_at.isoformat(),
        "total_value": float(snap.total_value) if snap.total_value is not None else None,
        "total_pnl": float(snap.total_pnl) if snap.total_pnl is not None else None,
        "total_pnl_pct": float(snap.total_pnl_pct) if snap.total_pnl_pct is not None else None,
        "positions_count": snap.positions_count,
    }
