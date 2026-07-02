from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


EVENT_TYPES = [
    "NEWS", "SEC_FILING", "EARNINGS_TRANSCRIPT", "INSIDER_TRANSACTION",
    "SHORT_INTEREST", "OPTIONS_FLOW", "CONGRESS_TRADING", "MACRO_EVENT",
    "CENTRAL_BANK", "JOB_POSTINGS", "PATENT_FILING", "SOCIAL_SENTIMENT",
    "APP_RANKING", "COMMODITY_EVENT", "ANALYST_UPGRADE", "ANALYST_DOWNGRADE",
]


class AlternativeDataEventIngest(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=255)
    source_url: Optional[str] = None
    headline: str = Field(min_length=1, max_length=1000)
    content: Optional[str] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    sentiment_score: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    importance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    urgency_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source_reliability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    market_impact_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    published_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AlternativeDataEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    event_type: str
    source: str
    source_url: Optional[str]
    headline: str
    content: Optional[str]
    tickers: Optional[Any]
    sectors: Optional[Any]
    countries: Optional[Any]
    entities: Optional[Any]
    sentiment_score: Optional[float]
    importance_score: Optional[float]
    urgency_score: Optional[float]
    source_reliability_score: Optional[float]
    market_impact_score: Optional[float]
    cluster_id: Optional[uuid.UUID]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class BatchIngestRequest(BaseModel):
    events: List[AlternativeDataEventIngest] = Field(min_length=1, max_length=500)


class BatchIngestResponse(BaseModel):
    ingested: int
    failed: int
    errors: List[str] = []


class EventSearchRequest(BaseModel):
    query: Optional[str] = None
    event_types: Optional[List[str]] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    min_importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_sentiment: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    max_sentiment: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class SentimentSummary(BaseModel):
    ticker: str
    avg_sentiment: float
    event_count: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    latest_event_at: Optional[datetime]


class ImportanceFeedItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    event_type: str
    headline: str
    tickers: Optional[Any]
    importance_score: Optional[float]
    urgency_score: Optional[float]
    market_impact_score: Optional[float]
    sentiment_score: Optional[float]
    published_at: Optional[datetime]
    created_at: datetime


class EventClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cluster_label: str
    event_count: int
    topics: Optional[Any]
    tickers: Optional[Any]
    avg_sentiment: Optional[float]
    avg_importance: Optional[float]
    created_at: datetime
    updated_at: datetime
