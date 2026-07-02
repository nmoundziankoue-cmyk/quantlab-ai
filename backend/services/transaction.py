"""Transaction and holdings service.

Owns two concerns:
1. **Ledger CRUD**: adding, listing, and deleting transaction records.
2. **Holdings computation**: deriving current positions and portfolio
   summary KPIs from the transaction ledger.

Cost basis method: Average Cost (AVCO).
All monetary arithmetic uses ``float`` after reading Decimal values from the
database.  Decimal columns exist in PostgreSQL to prevent rounding at storage;
the service layer operates in float for numpy/pandas compatibility.
"""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from models.portfolio import Transaction, TransactionType
from schemas.portfolio import (
    HoldingRead,
    PortfolioSummaryRead,
    TransactionCreate,
)
from services.market_data import get_current_prices, get_day_change_pct
from services.portfolio import get_portfolio


class InsufficientSharesError(Exception):
    """Raised when a SELL quantity exceeds the current holding."""


class TransactionNotFoundError(Exception):
    """Raised when a transaction with the given ID does not exist."""


# ---------------------------------------------------------------------------
# Ledger CRUD
# ---------------------------------------------------------------------------

def list_transactions(
    db: Session,
    portfolio_id: uuid.UUID,
    limit: int = 200,
    offset: int = 0,
) -> Sequence[Transaction]:
    """Return transactions for a portfolio, newest first.

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID.
        limit:        Maximum rows to return (default 200).
        offset:       Row offset for pagination.

    Returns:
        Sequence of Transaction ORM objects.
    """
    return (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def add_transaction(
    db: Session,
    portfolio_id: uuid.UUID,
    payload: TransactionCreate,
) -> Transaction:
    """Validate and persist a new transaction.

    For SELL transactions, validates that sufficient shares are held before
    committing.

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID (existence already verified by caller).
        payload:      Validated creation schema.

    Returns:
        Newly created Transaction ORM object.

    Raises:
        InsufficientSharesError: If a SELL exceeds the current position.
    """
    if payload.transaction_type == TransactionType.SELL and payload.ticker:
        existing_txs = (
            db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio_id,
                Transaction.ticker == payload.ticker,
            )
            .all()
        )
        current_qty = _compute_ticker_quantity(existing_txs)
        if payload.quantity > current_qty:
            raise InsufficientSharesError(
                f"Cannot sell {payload.quantity:.4f} shares of {payload.ticker}: "
                f"only {current_qty:.4f} held"
            )

    tx = Transaction(
        portfolio_id=portfolio_id,
        ticker=payload.ticker,
        transaction_type=payload.transaction_type,
        quantity=payload.quantity,
        price=payload.price,
        fees=payload.fees,
        transaction_date=payload.transaction_date,
        notes=payload.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(
    db: Session,
    portfolio_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> None:
    """Remove a transaction from the ledger.

    Args:
        db:             Active SQLAlchemy session.
        portfolio_id:   Portfolio UUID (for ownership check).
        transaction_id: Transaction UUID.

    Raises:
        TransactionNotFoundError: If no matching transaction exists.
    """
    tx: Optional[Transaction] = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == portfolio_id,
        )
        .first()
    )
    if tx is None:
        raise TransactionNotFoundError(transaction_id)
    db.delete(tx)
    db.commit()


# ---------------------------------------------------------------------------
# Holdings computation
# ---------------------------------------------------------------------------

def compute_portfolio_summary(
    db: Session,
    portfolio_id: uuid.UUID,
) -> PortfolioSummaryRead:
    """Derive the current portfolio snapshot from the transaction ledger.

    Fetches live prices for all open positions, computes market values,
    P&L figures, and position weights in one pass.

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID.

    Returns:
        PortfolioSummaryRead with holdings and aggregated KPIs.
    """
    # Ensure portfolio exists (raises if not)
    get_portfolio(db, portfolio_id)

    txs: Sequence[Transaction] = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
        .all()
    )

    # Positions: ticker -> [quantity, cost_basis]
    positions: dict[str, list[float]] = {}
    cash: float = 0.0

    for tx in txs:
        qty = float(tx.quantity)
        price = float(tx.price)
        fees = float(tx.fees)

        match tx.transaction_type:
            case TransactionType.DEPOSIT:
                cash += qty * price
            case TransactionType.WITHDRAWAL:
                cash -= qty * price
            case TransactionType.DIVIDEND:
                cash += qty * price
            case TransactionType.BUY if tx.ticker:
                pos = positions.setdefault(tx.ticker, [0.0, 0.0])
                pos[0] += qty
                pos[1] += qty * price + fees
                cash -= qty * price + fees
            case TransactionType.SELL if tx.ticker:
                pos = positions.get(tx.ticker)
                if pos and pos[0] > 0:
                    proportion = min(qty / pos[0], 1.0)
                    pos[1] *= 1.0 - proportion
                    pos[0] -= qty
                    cash += qty * price - fees
                    if pos[0] <= 0:
                        del positions[tx.ticker]

    # Remove any positions that rounded to zero
    open_positions = {t: p for t, p in positions.items() if p[0] > 1e-10}

    # Fetch live prices for open positions
    live_tickers = list(open_positions.keys())
    current_prices = get_current_prices(live_tickers) if live_tickers else {}

    # Build holdings list
    holdings: list[HoldingRead] = []
    total_equity_value: float = 0.0
    total_cost_basis: float = 0.0

    for ticker, (qty, basis) in open_positions.items():
        current_price = current_prices.get(ticker, 0.0)
        market_value = qty * current_price
        avg_cost = basis / qty if qty > 0 else 0.0
        unrealized_pnl = market_value - basis
        unrealized_pnl_pct = (unrealized_pnl / basis * 100) if basis > 0 else 0.0

        holdings.append(
            HoldingRead(
                ticker=ticker,
                quantity=round(qty, 8),
                avg_cost=round(avg_cost, 4),
                cost_basis=round(basis, 2),
                current_price=round(current_price, 4),
                market_value=round(market_value, 2),
                unrealized_pnl=round(unrealized_pnl, 2),
                unrealized_pnl_pct=round(unrealized_pnl_pct, 2),
                weight_pct=0.0,        # computed after total is known
                day_change_pct=None,   # populated below
            )
        )
        total_equity_value += market_value
        total_cost_basis += basis

    # Compute position weights
    for h in holdings:
        h.weight_pct = (
            round(h.market_value / total_equity_value * 100, 2)
            if total_equity_value > 0
            else 0.0
        )

    # Sort by market value descending
    holdings.sort(key=lambda h: h.market_value, reverse=True)

    total_market_value = total_equity_value + cash
    total_unrealized_pnl = total_equity_value - total_cost_basis
    total_unrealized_pnl_pct = (
        total_unrealized_pnl / total_cost_basis * 100
        if total_cost_basis > 0
        else 0.0
    )

    return PortfolioSummaryRead(
        portfolio_id=portfolio_id,
        total_market_value=round(total_market_value, 2),
        total_equity_value=round(total_equity_value, 2),
        cash_balance=round(cash, 2),
        total_cost_basis=round(total_cost_basis, 2),
        total_unrealized_pnl=round(total_unrealized_pnl, 2),
        total_unrealized_pnl_pct=round(total_unrealized_pnl_pct, 2),
        holdings_count=len(holdings),
        holdings=holdings,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_ticker_quantity(transactions: Sequence[Transaction]) -> float:
    """Compute the net shares held for a ticker from its transaction records."""
    qty: float = 0.0
    for tx in transactions:
        if tx.transaction_type == TransactionType.BUY:
            qty += float(tx.quantity)
        elif tx.transaction_type == TransactionType.SELL:
            qty -= float(tx.quantity)
    return qty
