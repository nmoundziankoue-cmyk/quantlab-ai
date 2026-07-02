"""Pydantic v2 schemas for the Economic Calendar (M7)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateEconomicEventRequest(BaseModel):
    name: str
    country: str
    category: str
    importance: str = "MEDIUM"
    currency: Optional[str] = None
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    unit: Optional[str] = None
    release_date: Optional[datetime] = None
    description: Optional[str] = None
    affected_assets: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateEconomicEventRequest(BaseModel):
    name: Optional[str] = None
    importance: Optional[str] = None
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    release_date: Optional[datetime] = None
    description: Optional[str] = None


class EconomicEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    country: str
    currency: Optional[str] = None
    importance: str
    category: str
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    unit: Optional[str] = None
    release_date: Optional[datetime] = None
    description: Optional[str] = None
    impact_score: Optional[float] = None
    affected_assets: Optional[Dict[str, Any]] = None
    metadata_: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
