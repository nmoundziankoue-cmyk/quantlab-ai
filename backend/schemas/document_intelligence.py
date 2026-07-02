from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class DocumentIngest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    doc_type: str = "TEXT"
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    content: str = Field(min_length=1)
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    doc_type: str
    source_name: Optional[str]
    source_url: Optional[str]
    status: str
    tickers: Optional[Any]
    sectors: Optional[Any]
    entities: Optional[Any]
    chunk_count: int
    file_size: Optional[int]
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    token_count: int
    embedding_model: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    doc_types: Optional[List[str]] = None
    tickers: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=100)
    search_type: str = "HYBRID"


class SearchResultChunk(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    doc_type: str
    chunk_index: int
    content: str
    score: float
    source_name: Optional[str] = None


class DocumentSearchResponse(BaseModel):
    query: str
    search_type: str
    results: List[SearchResultChunk]
    total_results: int


# ---------------------------------------------------------------------------
# Ask / RAG
# ---------------------------------------------------------------------------

class AskDocumentRequest(BaseModel):
    question: str = Field(min_length=1)
    document_ids: Optional[List[uuid.UUID]] = None
    top_k: int = Field(default=5, ge=1, le=20)


class CitedAnswer(BaseModel):
    question: str
    answer: str
    confidence: float
    citations: List[SearchResultChunk]
    model_used: str = "deterministic"


# ---------------------------------------------------------------------------
# Copilot Session
# ---------------------------------------------------------------------------

class CopilotMessage(BaseModel):
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[datetime] = None


class CopilotSessionCreate(BaseModel):
    title: str = "New Chat"
    session_type: str = "CHAT"
    ticker: Optional[str] = None


class CopilotMessageCreate(BaseModel):
    role: str = "user"
    content: str = Field(min_length=1)
    document_ids: Optional[List[uuid.UUID]] = None


class CopilotSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    session_type: str
    ticker: Optional[str]
    messages: Optional[Any]
    context_docs: Optional[Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

class PromptTemplate(BaseModel):
    key: str
    name: str
    description: str
    category: str
    input_fields: List[str]


# ---------------------------------------------------------------------------
# Thesis / Research Generation
# ---------------------------------------------------------------------------

class ThesisRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    additional_context: Optional[str] = None
    document_ids: Optional[List[uuid.UUID]] = None


class MemoRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    memo_type: str = "RESEARCH_MEMO"
    key_points: Optional[List[str]] = None
    additional_context: Optional[str] = None


class ReportRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    sections: Optional[List[str]] = None
    include_technicals: bool = True
    include_valuation: bool = True
    additional_context: Optional[str] = None
