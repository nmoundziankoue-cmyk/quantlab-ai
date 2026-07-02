"""ORM models for M4 Portfolio & Risk Analytics.

All tables use UUID primary keys and JSONB for bulk numerical results.
These models store computed analytics results so expensive calculations
can be retrieved without recomputation.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class PortfolioSnapshot(Base):
    """Daily portfolio value snapshot for performance attribution.

    Captured once per day by the analytics pipeline. Used for time-series
    risk metrics that require a full equity curve.
    """

    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    holdings_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    daily_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    daily_return_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PortfolioOptimization(Base):
    """Stored portfolio optimization result.

    Caches the frontier, weights, and metrics so the user can
    review past optimizations without re-running the solver.
    """

    __tablename__ = "portfolio_optimizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    tickers: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    weights: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    expected_volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    frontier_points: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    params: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StressScenario(Base):
    """User-defined or built-in stress test scenario definition.

    ``shocks`` stores per-ticker or market-wide percentage shocks
    as a dict, e.g. ``{"AAPL": -0.30, "MARKET": -0.20}``.
    """

    __tablename__ = "stress_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shocks: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RiskAnalysis(Base):
    """Cached risk analytics result for a portfolio.

    Recomputed whenever the portfolio changes or the TTL expires.
    All metrics are stored in a single JSONB blob to avoid
    wide sparse columns.
    """

    __tablename__ = "risk_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False, default=252)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    var_historical_95: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    var_parametric_95: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    var_monte_carlo_95: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    cvar_95: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    max_drawdown_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    volatility_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)


class SimulationResult(Base):
    """Monte Carlo simulation output for a portfolio.

    Stores compressed percentile statistics (not raw paths) to
    keep storage bounded. ``percentile_paths`` has keys like
    ``"p5"``, ``"p25"``, ``"p50"``, ``"p75"``, ``"p95"`` each
    mapping to a list of portfolio values indexed by simulation day.
    """

    __tablename__ = "simulation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    simulation_days: Mapped[int] = mapped_column(Integer, nullable=False)
    n_simulations: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str] = mapped_column(String(20), nullable=False, default="gbm")
    initial_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    percentile_paths: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    final_value_stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prob_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    expected_final_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
