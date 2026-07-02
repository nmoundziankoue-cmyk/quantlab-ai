"""ORM models for M3 — Quantitative Research Engine."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from models.base import Base


class Strategy(Base):
    """Saved strategy configurations that can be reused across backtests."""

    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    backtests: Mapped[list["Backtest"]] = relationship(
        "Backtest", back_populates="strategy", passive_deletes=True
    )


class Backtest(Base):
    """Stored backtest runs with full results persisted as JSONB."""

    __tablename__ = "backtests"

    __table_args__ = (
        Index("ix_backtests_ticker", "ticker"),
        Index("ix_backtests_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Optional link to a saved strategy — can be NULL for ad-hoc runs
    strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
    )

    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    benchmark: Mapped[str] = mapped_column(String(10), nullable=False, default="SPY")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    initial_capital: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, default=100_000
    )
    commission_pct: Mapped[float] = mapped_column(
        Numeric(8, 6), nullable=False, default=0.001
    )
    slippage_pct: Mapped[float] = mapped_column(
        Numeric(8, 6), nullable=False, default=0.001
    )
    position_size_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=1.0
    )

    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False)
    strategy_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scalar metrics — denormalised for easy leaderboard queries
    total_return_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    annual_return_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    benchmark_return_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    sortino_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    calmar_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    max_drawdown_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    win_rate_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    profit_factor: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    total_trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Full time-series results as JSONB
    equity_curve: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    trades: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    monthly_returns: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    strategy: Mapped[Optional[Strategy]] = relationship(
        "Strategy", back_populates="backtests"
    )
