"""M15 — Pydantic v2 schemas for the Event Intelligence Platform."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Corporate event schemas
# ---------------------------------------------------------------------------

class AddCorporateEventRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    company: str = Field(..., min_length=1)
    event_type: str = Field(..., description="CorporateEventType value")
    description: str = Field(..., min_length=1)
    sector: str = "unknown"
    industry: str = "unknown"
    country: str = "US"
    confidence: float = Field(0.9, ge=0.0, le=1.0)
    source: str = "internal"
    timestamp: Optional[float] = None
    importance: Optional[str] = None
    severity: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class CorporateEventResponse(BaseModel):
    id: str
    ticker: str
    company: str
    sector: str
    industry: str
    country: str
    timestamp: float
    event_type: str
    importance: str
    severity: str
    confidence: float
    source: str
    description: str
    metadata: Dict[str, Any]
    tags: List[str]


# ---------------------------------------------------------------------------
# Macro event schemas
# ---------------------------------------------------------------------------

class AddMacroEventRequest(BaseModel):
    event_type: str = Field(..., description="MacroEventType value")
    description: str = Field(..., min_length=1)
    country: str = "US"
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    historical_values: Optional[List[float]] = None
    timestamp: Optional[float] = None
    importance: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MacroEventResponse(BaseModel):
    id: str
    event_type: str
    country: str
    timestamp: float
    importance: str
    description: str
    actual: Optional[float]
    forecast: Optional[float]
    previous: Optional[float]
    surprise: Optional[float]
    surprise_pct: Optional[float]
    historical_percentile: Optional[float]
    volatility_expectation: Optional[float]
    metadata: Dict[str, Any]


# ---------------------------------------------------------------------------
# Event study schemas
# ---------------------------------------------------------------------------

class EventStudyRequest(BaseModel):
    event_id: str
    tickers: List[str] = Field(..., min_length=1)
    actual_returns: Dict[str, List[float]] = Field(..., description="ticker -> daily actual returns")
    expected_returns: Dict[str, List[float]] = Field({}, description="ticker -> daily expected returns")
    windows: Optional[List[str]] = None


class EventStudyResponse(BaseModel):
    event_id: str
    results: Dict[str, Any]


# ---------------------------------------------------------------------------
# Event impact schemas
# ---------------------------------------------------------------------------

class EventImpactRequest(BaseModel):
    event_id: str
    ticker: str
    pre_returns: List[float] = Field(default_factory=list)
    post_returns: List[float] = Field(default_factory=list)
    market_returns: Optional[List[float]] = None
    pre_volumes: Optional[List[float]] = None
    post_volumes: Optional[List[float]] = None
    gap_return: float = 0.0
    expected_daily_return: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class EventImpactResponse(BaseModel):
    event_id: str
    ticker: str
    pre_return: float
    post_return: float
    gap_pct: float
    volume_spike: float
    volatility_spike: float
    relative_return: float
    abnormal_return: float
    liquidity_change: float
    max_drawdown: float
    recovery_days: Optional[int]
    momentum_persistence: float
    risk_contribution: float


# ---------------------------------------------------------------------------
# Catalyst schemas
# ---------------------------------------------------------------------------

class CatalystRequest(BaseModel):
    event_id: str
    ticker: Optional[str] = None


class CatalystResponse(BaseModel):
    event_id: str
    ticker: str
    direction: str
    theme: str
    raw_score: float
    importance_score: float
    severity_score: float
    confidence_score: float
    composite_score: float
    tags: List[str]


# ---------------------------------------------------------------------------
# Intelligence schemas
# ---------------------------------------------------------------------------

class IntelligenceRequest(BaseModel):
    event_id: str


class IntelligenceResponse(BaseModel):
    event_id: str
    ticker: str
    executive_summary: str
    bull_case: str
    bear_case: str
    neutral_view: str
    key_risks: List[str]
    key_opportunities: List[str]
    portfolio_implications: str
    sector_implications: str
    macro_implications: str
    historical_analogues: List[str]
    confidence: float


# ---------------------------------------------------------------------------
# Search schemas
# ---------------------------------------------------------------------------

class EventSearchRequest(BaseModel):
    query: Optional[str] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    importance: Optional[List[str]] = None
    since: Optional[float] = None
    until: Optional[float] = None
    kind: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("corporate", "macro"):
            raise ValueError("kind must be 'corporate', 'macro', or null")
        return v


class EventSearchResponse(BaseModel):
    hits: List[Dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# Timeline schemas
# ---------------------------------------------------------------------------

class TimelineRequest(BaseModel):
    since: Optional[float] = None
    until: Optional[float] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    importance: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    grouping: str = "day"
    view: str = "market"


class TimelineResponse(BaseModel):
    groups: List[Dict[str, Any]]
    total_events: int


# ---------------------------------------------------------------------------
# Calendar schemas
# ---------------------------------------------------------------------------

class CalendarRequest(BaseModel):
    view: str = "agenda"
    since: Optional[float] = None
    until: Optional[float] = None
    importance: Optional[List[str]] = None
    tickers: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    grouping: str = "day"
    limit: int = Field(50, ge=1, le=500)


# ---------------------------------------------------------------------------
# Report schemas
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    report_type: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    since: Optional[float] = None
    until: Optional[float] = None


# ---------------------------------------------------------------------------
# Clustering schemas
# ---------------------------------------------------------------------------

class ClusterRequest(BaseModel):
    event_ids: Optional[List[str]] = None
    limit: int = Field(50, ge=1, le=500)


# ---------------------------------------------------------------------------
# Intelligence score schemas
# ---------------------------------------------------------------------------

class IntelligenceScoreResponse(BaseModel):
    event_id: str
    positive_score: float
    negative_score: float
    confidence_score: float
    importance_score: float
    novelty_score: float
    expected_volatility: float
    expected_liquidity: float
    institutional_interest: float
    portfolio_relevance: float
    overall_score: float


# ---------------------------------------------------------------------------
# Shared filter schema
# ---------------------------------------------------------------------------

class EventFilterQuery(BaseModel):
    ticker: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    event_type: Optional[str] = None
    importance: Optional[str] = None
    since: Optional[float] = None
    until: Optional[float] = None
    limit: int = Field(50, ge=1, le=500)
