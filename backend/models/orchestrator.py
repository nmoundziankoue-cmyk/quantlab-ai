"""ORM models for the Agent Orchestration Engine (M7)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class AgentWorkflow(Base):
    __tablename__ = "agent_workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dag_definition: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result_summary: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tasks: Mapped[List["WorkflowTask"]] = relationship(
        "WorkflowTask", back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    depends_on: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    input_data: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workflow: Mapped["AgentWorkflow"] = relationship("AgentWorkflow", back_populates="tasks")
