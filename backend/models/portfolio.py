"""Portfolio and Transaction ORM models.

Both tables use UUID primary keys.  ``Transaction`` is the source of truth
for all position changes; holdings are always derived from this ledger.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TransactionType(str, enum.Enum):
    """All supported transaction types in the ledger."""

    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Portfolio(Base):
    """A named investment portfolio owned by a user.

    Holdings are not stored directly — they are derived from the
    ``transactions`` relationship at query time.
    """

    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # owner_id is nullable so existing portfolios without a user still work
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    benchmark: Mapped[str] = mapped_column(String(10), nullable=False, default="SPY")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="Transaction.transaction_date",
    )

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} name={self.name!r}>"


class Transaction(Base):
    """A single entry in a portfolio's transaction ledger.

    ``ticker`` is NULL for DEPOSIT and WITHDRAWAL entries, which represent
    cash movements not associated with a specific security.

    ``quantity`` and ``price`` semantics per type:
    - BUY/SELL:       quantity = shares; price = price per share
    - DIVIDEND:       quantity = 1;     price = total dividend amount
    - DEPOSIT/WITHDL: quantity = 1;     price = cash amount
    """

    __tablename__ = "transactions"

    __table_args__ = (
        Index("ix_transactions_portfolio_date", "portfolio_id", "transaction_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(
            TransactionType,
            name="transaction_type_enum",
            create_constraint=True,
        ),
        nullable=False,
    )
    # Decimal storage preserves full financial precision
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fees: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0")
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio", back_populates="transactions"
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} type={self.transaction_type.value} "
            f"ticker={self.ticker} qty={self.quantity} price={self.price}>"
        )


class PortfolioRiskSnapshot(Base):
    """Point-in-time risk snapshot for a portfolio (M10 Phase 7)."""

    __tablename__ = "portfolio_risk_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), nullable=True)
    total_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), nullable=True)
    total_pnl_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_portfolio_risk_snapshots_portfolio_taken", "portfolio_id", "taken_at"),
    )
