"""Pydantic v2 schemas for Milestone 2 — Market Data Engine."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# Quote
# ===========================================================================

class QuoteRead(BaseModel):
    """Full real-time quote for a single ticker."""

    ticker: str
    name: str
    exchange: str
    currency: str

    # Price
    price: float
    change: float = Field(..., description="Absolute price change vs previous close")
    change_pct: float = Field(..., description="Percentage change vs previous close")
    prev_close: float

    # Intraday range
    open: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None

    # Volume
    volume: Optional[int] = None
    avg_volume: Optional[int] = None

    # Fundamentals
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None

    # 52-week range
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None

    # Classification
    sector: str = "Unknown"
    industry: str = "Unknown"

    # Meta
    fetched_at: str = Field(..., description="ISO-8601 timestamp of data retrieval")


class BatchQuoteRequest(BaseModel):
    """Request body for batch quote fetch."""

    tickers: list[str] = Field(..., min_length=1, max_length=50)

    @field_validator("tickers", mode="before")
    @classmethod
    def normalise(cls, v: list[str]) -> list[str]:
        return [t.strip().upper() for t in v if t.strip()]


class BatchQuoteRead(BaseModel):
    """Map of ticker → quote (missing tickers omitted)."""

    quotes: dict[str, QuoteRead]
    errors: dict[str, str] = Field(default_factory=dict)


# ===========================================================================
# OHLCV
# ===========================================================================

class OHLCVPoint(BaseModel):
    """Single OHLCV bar."""

    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVRead(BaseModel):
    """Historical OHLCV data for one ticker."""

    ticker: str
    interval: str
    period: str
    data: list[OHLCVPoint]


# ===========================================================================
# News & Sentiment
# ===========================================================================

class NewsArticle(BaseModel):
    """A single news item."""

    uuid: str
    title: str
    publisher: str
    link: str
    published_at: str = Field(..., description="ISO-8601 UTC datetime")
    related_tickers: list[str] = Field(default_factory=list)
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="-1 (bearish) to +1 (bullish)")
    sentiment_label: str = Field(..., description="bullish | bearish | neutral")


class NewsRead(BaseModel):
    """News feed + aggregated sentiment for a ticker."""

    ticker: str
    articles: list[NewsArticle]
    overall_score: float = Field(..., ge=-1.0, le=1.0)
    overall_label: str
    signal: str = Field(..., description="Strong Buy | Buy | Hold | Sell | Strong Sell")


class SentimentRead(BaseModel):
    """Condensed sentiment snapshot for a ticker."""

    ticker: str
    score: float = Field(..., ge=-1.0, le=1.0)
    label: str
    signal: str
    article_count: int


# ===========================================================================
# Economic calendar
# ===========================================================================

class EconEvent(BaseModel):
    """A single scheduled macroeconomic event."""

    date: str = Field(..., description="YYYY-MM-DD")
    time: str = Field(..., description="HH:MM ET or 'All Day'")
    event: str
    importance: str = Field(..., description="high | medium | low")
    country: str = "US"
    previous: Optional[str] = None
    forecast: Optional[str] = None
    actual: Optional[str] = None


class CalendarRead(BaseModel):
    """Economic calendar covering the requested window."""

    from_date: str
    to_date: str
    events: list[EconEvent]


# ===========================================================================
# Watchlist
# ===========================================================================

class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class WatchlistItemCreate(BaseModel):
    ticker: str = Field(..., pattern=r"^[A-Z0-9.\-]{1,10}$")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("ticker", mode="before")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().upper()


class WatchlistItemRead(_OrmBase):
    id: uuid.UUID
    ticker: str
    notes: Optional[str]
    created_at: datetime
    quote: Optional[QuoteRead] = None


class WatchlistRead(_OrmBase):
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    items: list[WatchlistItemRead] = Field(default_factory=list)
