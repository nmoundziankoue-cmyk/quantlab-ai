"""Pydantic v2 schemas for the Agent Orchestration Engine (M7)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskDefinitionSchema(BaseModel):
    task_name: str
    agent_id: str
    depends_on: Optional[List[str]] = None
    input_data: Optional[Dict[str, Any]] = None


class DAGDefinitionSchema(BaseModel):
    tasks: List[TaskDefinitionSchema]


class CreateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    dag_definition: Optional[DAGDefinitionSchema] = None
    priority: int = Field(5, ge=1, le=10)
    metadata: Optional[Dict[str, Any]] = None


class WorkflowTaskSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    agent_id: str
    task_name: str
    depends_on: Optional[Any] = None
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class WorkflowSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    dag_definition: Optional[Dict[str, Any]] = None
    status: str
    priority: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: Optional[Dict[str, Any]] = None
    metadata_: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ExecuteWorkflowRequest(BaseModel):
    ticker: Optional[str] = None
    global_input: Optional[Dict[str, Any]] = None


class ExecuteWorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    tasks: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None
