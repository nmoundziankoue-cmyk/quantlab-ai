from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class AlternativeDataEvent(Base):
    __tablename__ = "alternative_data_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    headline: Mapped[str] = mapped_column(String(1000), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tickers: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    sectors: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    countries: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    entities: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    importance_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    urgency_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    source_reliability_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    market_impact_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EventCluster(Base):
    __tablename__ = "event_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_label: Mapped[str] = mapped_column(String(500), nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    representative_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    topics: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    tickers: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    avg_sentiment: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    avg_importance: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
