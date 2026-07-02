"""Portfolio CRUD service (M10 Phase 7: owner_id + risk snapshots).

All database operations for creating, reading, updating, and deleting
Portfolio records.  Business logic that involves market data or
transaction-derived state lives in the specialist services.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from models.portfolio import Portfolio, PortfolioRiskSnapshot
from schemas.portfolio import PortfolioCreate, PortfolioUpdate


class PortfolioNotFoundError(Exception):
    """Raised when a portfolio with the given ID does not exist."""


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def list_portfolios(
    db: Session, owner_id: Optional[uuid.UUID] = None
) -> Sequence[Portfolio]:
    """Return portfolios ordered by creation date (newest first).

    Args:
        db:       Active SQLAlchemy session.
        owner_id: If provided, return only portfolios belonging to this user.
                  Unowned legacy portfolios (owner_id IS NULL) are included
                  only when owner_id is not specified.
    """
    q = db.query(Portfolio)
    if owner_id is not None:
        q = q.filter(Portfolio.owner_id == owner_id)
    return q.order_by(Portfolio.created_at.desc()).all()


def get_portfolio(db: Session, portfolio_id: uuid.UUID) -> Portfolio:
    """Fetch a single portfolio by primary key.

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID.

    Returns:
        Portfolio ORM object.

    Raises:
        PortfolioNotFoundError: If no portfolio with that ID exists.
    """
    portfolio: Optional[Portfolio] = (
        db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    )
    if portfolio is None:
        raise PortfolioNotFoundError(portfolio_id)
    return portfolio


def create_portfolio(
    db: Session,
    payload: PortfolioCreate,
    owner_id: Optional[uuid.UUID] = None,
) -> Portfolio:
    """Persist a new portfolio and return the created record.

    Args:
        db:       Active SQLAlchemy session.
        payload:  Validated creation schema.
        owner_id: UUID of the authenticated user creating this portfolio.
    """
    portfolio = Portfolio(
        owner_id=owner_id,
        name=payload.name,
        description=payload.description,
        currency=payload.currency,
        benchmark=payload.benchmark,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def update_portfolio(
    db: Session,
    portfolio_id: uuid.UUID,
    payload: PortfolioUpdate,
) -> Portfolio:
    """Apply a partial update to an existing portfolio.

    Only fields explicitly provided in *payload* (non-None) are written.

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID.
        payload:      Validated update schema.

    Returns:
        Updated Portfolio ORM object.

    Raises:
        PortfolioNotFoundError: If no portfolio with that ID exists.
    """
    portfolio = get_portfolio(db, portfolio_id)

    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(portfolio, field, value)

    db.commit()
    db.refresh(portfolio)
    return portfolio


# ---------------------------------------------------------------------------
# Risk snapshot helpers
# ---------------------------------------------------------------------------

def save_risk_snapshot(
    db: Session,
    portfolio_id: uuid.UUID,
    total_value: Optional[Decimal] = None,
    total_pnl: Optional[Decimal] = None,
    total_pnl_pct: Optional[Decimal] = None,
    positions_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> PortfolioRiskSnapshot:
    """Persist a point-in-time risk snapshot for a portfolio."""
    snapshot = PortfolioRiskSnapshot(
        portfolio_id=portfolio_id,
        total_value=total_value,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        positions_count=positions_count,
        metadata_json=metadata,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_risk_snapshots(
    db: Session,
    portfolio_id: uuid.UUID,
    limit: int = 50,
) -> List[PortfolioRiskSnapshot]:
    """Return the most recent risk snapshots for a portfolio."""
    return (
        db.query(PortfolioRiskSnapshot)
        .filter(PortfolioRiskSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioRiskSnapshot.taken_at.desc())
        .limit(limit)
        .all()
    )


def delete_portfolio(db: Session, portfolio_id: uuid.UUID) -> None:
    """Delete a portfolio and all its transactions (cascade).

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID.

    Raises:
        PortfolioNotFoundError: If no portfolio with that ID exists.
    """
    portfolio = get_portfolio(db, portfolio_id)
    db.delete(portfolio)
    db.commit()
