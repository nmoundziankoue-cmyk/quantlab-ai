from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

SCREENER_TYPES = [
    "FUNDAMENTAL", "TECHNICAL", "QUALITY", "VALUE", "GROWTH",
    "MOMENTUM", "DIVIDEND", "VOLATILITY", "RISK", "CUSTOM",
]

OPERATORS = ["gt", "gte", "lt", "lte", "eq", "neq", "in", "not_in"]


class ScreenerRule(BaseModel):
    field: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    value: Any


class SavedScreenerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    screener_type: str = "FUNDAMENTAL"
    rules: Optional[List[ScreenerRule]] = None
    sort_by: Optional[str] = None
    sort_dir: str = "DESC"
    scoring_weights: Optional[Dict[str, float]] = None


class SavedScreenerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    screener_type: Optional[str] = None
    rules: Optional[List[ScreenerRule]] = None
    sort_by: Optional[str] = None
    sort_dir: Optional[str] = None
    scoring_weights: Optional[Dict[str, float]] = None


class SavedScreenerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: Optional[str]
    screener_type: str
    rules: Optional[Any]
    sort_by: Optional[str]
    sort_dir: str
    scoring_weights: Optional[Any]
    created_at: datetime
    updated_at: datetime


class ScreenerRunRequest(BaseModel):
    screener_id: Optional[uuid.UUID] = None
    rules: Optional[List[ScreenerRule]] = None
    screener_type: str = "FUNDAMENTAL"
    sort_by: Optional[str] = None
    sort_dir: str = "DESC"
    universe: Optional[List[str]] = None
    limit: int = Field(default=100, ge=1, le=1000)


class ScreenerResultItem(BaseModel):
    ticker: str
    rank: int
    score: float
    field_values: Dict[str, Any] = {}
    pass_count: int = 0
    fail_count: int = 0


class ScreenerRunResponse(BaseModel):
    screener_id: Optional[uuid.UUID]
    screener_type: str
    run_at: datetime
    total_universe: int
    match_count: int
    results: List[ScreenerResultItem]


class ScreenerResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    screener_id: Optional[uuid.UUID]
    run_at: datetime
    tickers_matched: Optional[Any]
    results: Optional[Any]
    total_universe: int
    match_count: int
    created_at: datetime
