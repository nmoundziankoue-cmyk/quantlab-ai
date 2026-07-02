from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Research Project
# ---------------------------------------------------------------------------

class ResearchProjectCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    status: str = "ACTIVE"
    tags: Optional[List[str]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    tickers: Optional[List[str]] = None


class ResearchProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    tickers: Optional[List[str]] = None


class ResearchProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: Optional[str]
    owner_id: Optional[str]
    status: str
    tags: Optional[Any]
    tickers: Optional[Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Research Folder
# ---------------------------------------------------------------------------

class ResearchFolderCreate(BaseModel):
    project_id: uuid.UUID
    parent_folder_id: Optional[uuid.UUID] = None
    name: str = Field(min_length=1, max_length=255)


class ResearchFolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    parent_folder_id: Optional[uuid.UUID] = None


class ResearchFolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    parent_folder_id: Optional[uuid.UUID]
    name: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Research Note
# ---------------------------------------------------------------------------

class ResearchNoteCreate(BaseModel):
    project_id: uuid.UUID
    folder_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=1, max_length=500)
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    tickers: Optional[List[str]] = None
    is_pinned: bool = False


class ResearchNoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    content: Optional[str] = None
    folder_id: Optional[uuid.UUID] = None
    tags: Optional[List[str]] = None
    tickers: Optional[List[str]] = None
    is_pinned: Optional[bool] = None


class ResearchNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    folder_id: Optional[uuid.UUID]
    title: str
    content: Optional[str]
    tags: Optional[Any]
    tickers: Optional[Any]
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Bookmark
# ---------------------------------------------------------------------------

class BookmarkCreate(BaseModel):
    project_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=1, max_length=500)
    url: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: Optional[uuid.UUID]
    title: str
    url: Optional[str]
    reference_type: Optional[str]
    reference_id: Optional[str]
    tags: Optional[Any]
    notes: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Saved Search
# ---------------------------------------------------------------------------

class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    query: str = Field(min_length=1)
    filters: Optional[Dict[str, Any]] = None
    search_type: str = "KEYWORD"


class SavedSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    query: str
    filters: Optional[Any]
    search_type: str
    result_count: Optional[int]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Research Session
# ---------------------------------------------------------------------------

class ResearchSessionCreate(BaseModel):
    project_id: Optional[uuid.UUID] = None
    title: str = "Untitled Session"
    tickers_researched: Optional[List[str]] = None


class ResearchSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: Optional[uuid.UUID]
    title: str
    session_data: Optional[Any]
    tickers_researched: Optional[Any]
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime


# ---------------------------------------------------------------------------
# Report Draft
# ---------------------------------------------------------------------------

class ReportDraftCreate(BaseModel):
    project_id: Optional[uuid.UUID] = None
    ticker: Optional[str] = Field(default=None, max_length=20)
    title: str = Field(min_length=1, max_length=500)
    content: Optional[str] = None
    sections: Optional[Dict[str, Any]] = None
    status: str = "DRAFT"


class ReportDraftUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    content: Optional[str] = None
    sections: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    ticker: Optional[str] = None


class ReportDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: Optional[uuid.UUID]
    ticker: Optional[str]
    title: str
    content: Optional[str]
    sections: Optional[Any]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Recent Activity + Pinned Item
# ---------------------------------------------------------------------------

class RecentActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    activity_type: str
    entity_type: str
    entity_id: Optional[str]
    description: Optional[str]
    created_at: datetime


class PinnedItemCreate(BaseModel):
    entity_type: str
    entity_id: str
    label: str = Field(min_length=1, max_length=255)
    sort_order: int = 0


class PinnedItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entity_type: str
    entity_id: str
    label: str
    sort_order: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Workspace Search
# ---------------------------------------------------------------------------

class WorkspaceSearchResult(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    snippet: Optional[str] = None
    score: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
