"""ORM models for M10 enterprise features: strategies, agent sessions, jobs, WS events, health snapshots."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ── Strategies ────────────────────────────────────────────────────────────────

class TradingStrategy(Base):
    __tablename__ = "trading_strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parameters: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[List["TradingStrategyRun"]] = relationship(
        "TradingStrategyRun", back_populates="strategy", cascade="all, delete-orphan"
    )


class TradingStrategyRun(Base):
    __tablename__ = "trading_strategy_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading_strategies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    parameters_snapshot: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    result: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategy: Mapped["TradingStrategy"] = relationship("TradingStrategy", back_populates="runs")


# ── Agent Sessions ────────────────────────────────────────────────────────────

class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    session_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    context: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[List["AgentMessage"]] = relationship(
        "AgentMessage", back_populates="session", cascade="all, delete-orphan"
    )


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant" | "system" | "tool"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    token_usage: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["AgentSession"] = relationship("AgentSession", back_populates="messages")


# ── WebSocket Events ──────────────────────────────────────────────────────────

class WebSocketEvent(Base):
    __tablename__ = "websocket_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conn_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ── Background Jobs ───────────────────────────────────────────────────────────

class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    payload: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    result: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    progress_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enqueued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Provider Health Snapshots ─────────────────────────────────────────────────

class ProviderHealthSnapshot(Base):
    __tablename__ = "provider_health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    health_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms_p50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms_p95: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quota_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quota_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
