"""Pydantic v2 schemas for the Knowledge Graph (M7)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateEntityRequest(BaseModel):
    name: str
    entity_type: str
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    source_doc_id: Optional[uuid.UUID] = None


class EntitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    entity_type: str
    description: Optional[str] = None
    aliases: Optional[Any] = None
    properties: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    created_at: datetime


class CreateEdgeRequest(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    relationship_type: str
    weight: float = Field(1.0, ge=0.0)
    evidence: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class EdgeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    relationship_type: str
    weight: float
    evidence: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    created_at: datetime


class ExtractEntitiesRequest(BaseModel):
    text: str
    source_doc_id: Optional[uuid.UUID] = None
    persist: bool = False


class GraphNeighborhoodRequest(BaseModel):
    depth: int = Field(1, ge=1, le=5)
    relationship_type: Optional[str] = None
