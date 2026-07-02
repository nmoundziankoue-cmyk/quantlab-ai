from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, default="TEXT")
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    tickers: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    sectors: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    entities: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="New Chat")
    session_type: Mapped[str] = mapped_column(String(50), default="CHAT")
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    messages: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    context_docs: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
