from __future__ import annotations
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ProjectStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    COMPLETED = "COMPLETED"


class ReportDraftStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    FINAL = "FINAL"


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    tags: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    tickers: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    folders: Mapped[List["ResearchFolder"]] = relationship("ResearchFolder", back_populates="project", cascade="all, delete-orphan")
    notes: Mapped[List["ResearchNote"]] = relationship("ResearchNote", back_populates="project", cascade="all, delete-orphan")
    sessions: Mapped[List["ResearchSession"]] = relationship("ResearchSession", back_populates="project", cascade="all, delete-orphan")
    report_drafts: Mapped[List["ReportDraft"]] = relationship("ReportDraft", back_populates="project", cascade="all, delete-orphan")


class ResearchFolder(Base):
    __tablename__ = "research_folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    parent_folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("research_folders.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["ResearchProject"] = relationship("ResearchProject", back_populates="folders")
    children: Mapped[List["ResearchFolder"]] = relationship("ResearchFolder", back_populates="parent")
    parent: Mapped[Optional["ResearchFolder"]] = relationship("ResearchFolder", back_populates="children", remote_side="ResearchFolder.id")
    notes: Mapped[List["ResearchNote"]] = relationship("ResearchNote", back_populates="folder")


class ResearchNote(Base):
    __tablename__ = "research_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("research_folders.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    tickers: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["ResearchProject"] = relationship("ResearchProject", back_populates="notes")
    folder: Mapped[Optional["ResearchFolder"]] = relationship("ResearchFolder", back_populates="notes")


class Bookmark(Base):
    __tablename__ = "research_bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tags: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedSearch(Base):
    __tablename__ = "research_saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    search_type: Mapped[str] = mapped_column(String(50), default="KEYWORD")
    result_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="Untitled Session")
    session_data: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    tickers_researched: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Optional["ResearchProject"]] = relationship("ResearchProject", back_populates="sessions")


class ReportDraft(Base):
    __tablename__ = "report_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sections: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[Optional["ResearchProject"]] = relationship("ResearchProject", back_populates="report_drafts")


class RecentActivity(Base):
    __tablename__ = "research_recent_activity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PinnedItem(Base):
    __tablename__ = "research_pinned_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
