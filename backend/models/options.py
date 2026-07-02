"""ORM models for the Options Analytics desk (M7)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class OptionsSnapshot(Base):
    __tablename__ = "options_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    underlying_price: Mapped[float] = mapped_column(Float, nullable=False)
    strike: Mapped[float] = mapped_column(Float, nullable=False)
    expiry_days: Mapped[int] = mapped_column(Integer, nullable=False)
    option_type: Mapped[str] = mapped_column(String(10), default="CALL")
    implied_vol: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gamma: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    theta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vega: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rho: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    theoretical_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
