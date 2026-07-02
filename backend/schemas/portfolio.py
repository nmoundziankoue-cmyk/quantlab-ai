"""Pydantic v2 schemas for the Portfolio domain.

Naming convention:
  *Create  – inbound request body (POST)
  *Update  – inbound request body (PATCH/PUT), all fields optional
  *Read    – outbound response body
  *         – shared / internal shapes
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.portfolio import TransactionType


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

class _OrmBase(BaseModel):
    """Base model that enables ORM-mode (from_attributes) for all read schemas."""

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# Portfolio schemas
# ===========================================================================

class PortfolioCreate(BaseModel):
    """Payload to create a new portfolio."""

    name: str = Field(..., min_length=1, max_length=100, examples=["My Tech Portfolio"])
    description: Optional[str] = Field(None, max_length=500)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$", examples=["USD"])
    benchmark: str = Field("SPY", pattern=r"^[A-Z0-9.\-]{1,10}$", examples=["SPY"])


class PortfolioUpdate(BaseModel):
    """Payload to update an existing portfolio (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    benchmark: Optional[str] = Field(None, pattern=r"^[A-Z0-9.\-]{1,10}$")


class PortfolioRead(_OrmBase):
    """Full portfolio record returned from the API."""

    id: uuid.UUID
    name: str
    description: Optional[str]
    currency: str
    benchmark: str
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Transaction schemas
# ===========================================================================

class TransactionCreate(BaseModel):
    """Payload to record a new transaction in a portfolio's ledger."""

    transaction_type: TransactionType
    transaction_date: date = Field(..., description="Settlement / trade date")
    ticker: Optional[str] = Field(
        None,
        pattern=r"^[A-Z0-9.\-]{1,10}$",
        description="Required for BUY / SELL / DIVIDEND; omit for DEPOSIT / WITHDRAWAL",
    )
    quantity: float = Field(..., gt=0, description="Shares (BUY/SELL) or 1 (DEPOSIT/DIVIDEND)")
    price: float = Field(..., gt=0, description="Price per share or total cash amount")
    fees: float = Field(0.0, ge=0, description="Brokerage commission or other fees")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("ticker", mode="before")
    @classmethod
    def normalise_ticker(cls, v: Optional[str]) -> Optional[str]:
        """Upper-case the ticker if provided."""
        return v.strip().upper() if isinstance(v, str) else v

    @model_validator(mode="after")
    def ticker_required_for_equity_transactions(self) -> "TransactionCreate":
        """Ensure ticker is present for BUY, SELL, and DIVIDEND transactions."""
        equity_types = {TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND}
        if self.transaction_type in equity_types and not self.ticker:
            raise ValueError(
                f"ticker is required for {self.transaction_type.value} transactions"
            )
        return self


class TransactionRead(_OrmBase):
    """Transaction record returned from the API."""

    id: uuid.UUID
    portfolio_id: uuid.UUID
    transaction_type: TransactionType
    transaction_date: date
    ticker: Optional[str]
    quantity: float
    price: float
    fees: float
    notes: Optional[str]
    created_at: datetime


# ===========================================================================
# Holding schemas  (computed — not stored)
# ===========================================================================

class HoldingRead(BaseModel):
    """Current position for a single ticker, derived from the transaction ledger."""

    ticker: str
    quantity: float
    avg_cost: float = Field(..., description="Average cost per share (AVCO method)")
    cost_basis: float = Field(..., description="Total amount invested (qty × avg_cost)")
    current_price: float
    market_value: float
    unrealized_pnl: float = Field(..., description="market_value − cost_basis")
    unrealized_pnl_pct: float = Field(..., description="unrealized_pnl / cost_basis × 100")
    weight_pct: float = Field(..., description="Position weight as % of total equity value")
    day_change_pct: Optional[float] = None


# ===========================================================================
# Portfolio summary  (computed KPIs)
# ===========================================================================

class PortfolioSummaryRead(BaseModel):
    """Snapshot KPIs for a portfolio, computed live from the ledger + prices."""

    portfolio_id: uuid.UUID
    total_market_value: float = Field(..., description="Total equity + cash")
    total_equity_value: float = Field(..., description="Equity positions only")
    cash_balance: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    holdings_count: int
    holdings: list[HoldingRead]


# ===========================================================================
# Performance schemas  (computed)
# ===========================================================================

class NavPoint(BaseModel):
    """Single data point in a portfolio NAV time series."""

    date: str = Field(..., description="ISO 8601 date string")
    nav: float = Field(..., description="Portfolio NAV normalised to 100 at inception")
    benchmark_nav: Optional[float] = Field(
        None, description="Benchmark NAV normalised to 100 at inception"
    )


class PerformanceRead(BaseModel):
    """Full performance report for a portfolio."""

    portfolio_id: uuid.UUID
    benchmark: str
    return_1d_pct: float
    return_1w_pct: float
    return_1m_pct: float
    return_ytd_pct: float
    return_total_pct: float
    return_annualized_pct: float
    volatility_pct: float = Field(..., description="Annualised daily-return std dev")
    sharpe_ratio: float
    max_drawdown_pct: float = Field(..., description="Peak-to-trough drawdown (negative)")
    nav_series: list[NavPoint]


# ===========================================================================
# Allocation schemas  (computed)
# ===========================================================================

class AllocationItem(BaseModel):
    """A single slice of a portfolio allocation breakdown."""

    label: str
    market_value: float
    weight_pct: float


class AllocationRead(BaseModel):
    """Allocation breakdown of a portfolio by ticker and by sector."""

    portfolio_id: uuid.UUID
    by_ticker: list[AllocationItem]
    by_sector: list[AllocationItem]
