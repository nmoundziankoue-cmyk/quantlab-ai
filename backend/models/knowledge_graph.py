"""ORM models for the Knowledge Graph (M7)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class KnowledgeEntity(Base):
    __tablename__ = "knowledge_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aliases: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    properties: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    tags: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=1.0)
    source_doc_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    outgoing_edges: Mapped[List["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge", foreign_keys="KnowledgeEdge.source_id",
        back_populates="source", cascade="all, delete-orphan"
    )
    incoming_edges: Mapped[List["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge", foreign_keys="KnowledgeEdge.target_id",
        back_populates="target", cascade="all, delete-orphan"
    )


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    properties: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped["KnowledgeEntity"] = relationship(
        "KnowledgeEntity", foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    target: Mapped["KnowledgeEntity"] = relationship(
        "KnowledgeEntity", foreign_keys=[target_id], back_populates="incoming_edges"
    )
