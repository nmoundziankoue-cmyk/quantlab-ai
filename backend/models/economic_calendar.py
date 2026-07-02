"""ORM models for the Economic Calendar (M7)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    importance: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forecast: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    previous: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    release_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    affected_assets: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
