from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class SavedScreener(Base):
    __tablename__ = "saved_screeners"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screener_type: Mapped[str] = mapped_column(String(50), nullable=False, default="FUNDAMENTAL")
    rules: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    sort_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_dir: Mapped[str] = mapped_column(String(4), default="DESC")
    scoring_weights: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    results: Mapped[List["ScreenerResult"]] = relationship("ScreenerResult", back_populates="screener", cascade="all, delete-orphan")


class ScreenerResult(Base):
    __tablename__ = "screener_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    screener_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("saved_screeners.id", ondelete="SET NULL"), nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tickers_matched: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    results: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    total_universe: Mapped[int] = mapped_column(Integer, default=0)
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    screener: Mapped[Optional["SavedScreener"]] = relationship("SavedScreener", back_populates="results")
