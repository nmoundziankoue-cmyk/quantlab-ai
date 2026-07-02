"""ORM models for the enterprise notification system (M8)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    metadata_: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
