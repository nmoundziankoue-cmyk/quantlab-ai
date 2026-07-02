"""M14 — Pydantic v2 schemas for the Alternative Data Intelligence Platform API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class AltProviderInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    priority: int
    capabilities: List[str]
    is_healthy: bool
    p50_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    quality_score: float


class AltCapabilitiesMatrixResponse(BaseModel):
    providers: Dict[str, List[str]]


class AltHealthSummaryResponse(BaseModel):
    providers: List[Dict[str, Any]]
    latency: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentIngestRequest(BaseModel):
    doc_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=10)
    filing_type: str
    text: str = Field(min_length=1)
    source: str = "unknown"
    published_at: Optional[str] = None


class DocumentIngestResponse(BaseModel):
    doc_id: str
    symbol: str
    filing_type: str
    version: int
    checksum: str
    size_bytes: int
    quality_score: float
    quality_passed: bool


class DocumentMetadataResponse(BaseModel):
    doc_id: str
    symbol: str
    filing_type: str
    source: str
    version: int
    checksum: str
    size_bytes: int
    published_at: Optional[str] = None
    extra: Dict[str, Any] = {}


class ParsedFilingResponse(BaseModel):
    doc_id: str
    sections: Dict[str, Any]
    entities: Dict[str, List[str]]


# ---------------------------------------------------------------------------
# Document AI
# ---------------------------------------------------------------------------

class EnrichTextRequest(BaseModel):
    text: str = Field(min_length=1)
    corpus_texts: Optional[List[str]] = None
    summary_sentences: int = Field(default=3, ge=1, le=10)


class EnrichTextResponse(BaseModel):
    entities: Dict[str, List[str]]
    topics: List[str]
    keywords: List[Dict[str, Any]]
    sentiment: float
    risk: float
    uncertainty: float
    readability: float
    novelty: float
    summary: str


class QuestionAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    text: str = Field(min_length=1)


class QuestionAnswerResponse(BaseModel):
    answer: str
    confidence: float
    sentence_index: int


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class EventDetectionRequest(BaseModel):
    text: str = Field(min_length=1)
    symbol: str = Field(default="UNKNOWN", min_length=1, max_length=10)
    source_doc_id: Optional[str] = None


class AltEventResponse(BaseModel):
    event_type: str
    symbol: str
    confidence: float
    severity: str
    snippet: str
    source_doc_id: Optional[str] = None
    matched_patterns: List[str] = []


class EventDetectionResponse(BaseModel):
    symbol: str
    events: List[AltEventResponse]
    event_count: int


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

class AltFeatureComputeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    document_texts: List[str] = Field(default_factory=list)
    insider_buys: int = 0
    insider_sells: int = 0
    executive_changes: int = 0
    total_executives: int = 1
    earnings_surprises: List[float] = Field(default_factory=list)
    patent_counts_by_period: List[float] = Field(default_factory=list)
    supplier_concentration_shares: List[float] = Field(default_factory=list)
    customer_concentration_shares: List[float] = Field(default_factory=list)
    news_mentions_by_period: List[float] = Field(default_factory=list)
    social_mentions_by_period: List[float] = Field(default_factory=list)
    search_trend_values: List[float] = Field(default_factory=list)
    esg_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    transcript_texts: List[str] = Field(default_factory=list)
    window_days: int = Field(default=30, ge=1)


class AltFeatureComputeResponse(BaseModel):
    symbol: str
    features: Dict[str, float]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class AltSearchRequest(BaseModel):
    query: Optional[str] = None
    symbol: Optional[str] = None
    filing_type: Optional[str] = None
    executive: Optional[str] = None
    company: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    semantic: bool = False
    limit: int = Field(default=20, ge=1, le=200)

    @model_validator(mode="after")
    def _require_some_criteria(self) -> "AltSearchRequest":
        if not any([self.query, self.symbol, self.filing_type, self.executive, self.company]):
            raise ValueError("At least one search criterion is required")
        return self


class AltSearchHitResponse(BaseModel):
    doc_id: str
    symbol: str
    filing_type: str
    score: float
    snippet: str


class AltSearchResponse(BaseModel):
    hits: List[AltSearchHitResponse]
    hit_count: int


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------

class GraphEntityLinkRequest(BaseModel):
    entity_id: str = Field(min_length=1)
    entity_name: str = Field(min_length=1)
    related_company_id: str = Field(min_length=1)
    relation_label: Optional[str] = None
    score: float = Field(default=1.0, ge=0.0, le=1.0)


class GraphMetricsResponse(BaseModel):
    node_count: int
    component_count: int
    largest_component_size: int
    community_count: int
    top_central_nodes: List[Dict[str, Any]]


class DependencyChainRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = Field(default=6, ge=1, le=20)


class DependencyChainResponse(BaseModel):
    path: Optional[List[str]]
    found: bool


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

class DocQualityCheckRequest(BaseModel):
    doc_id: str
    text: str = Field(min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocQualityCheckResponse(BaseModel):
    doc_id: str
    quality_score: float
    passed: bool
    issues: List[Dict[str, str]]
