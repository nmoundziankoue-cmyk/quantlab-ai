"""M14 — Institutional Alternative Data Intelligence Platform API router.

Prefix: /alt-intelligence
Tags:   Alternative Data Intelligence

Distinct from the existing M6 `/alternative-data` router (DB-backed event
feed) — this router exposes the M14 pure-Python provider/document/search/
event/feature/knowledge-graph stack, all in-memory and network-free.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from schemas.alt_intelligence import (
    AltCapabilitiesMatrixResponse,
    AltEventResponse,
    AltFeatureComputeRequest,
    AltFeatureComputeResponse,
    AltHealthSummaryResponse,
    AltProviderInfo,
    AltSearchHitResponse,
    AltSearchRequest,
    AltSearchResponse,
    DependencyChainRequest,
    DependencyChainResponse,
    DocQualityCheckRequest,
    DocQualityCheckResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentMetadataResponse,
    EnrichTextRequest,
    EnrichTextResponse,
    EventDetectionRequest,
    EventDetectionResponse,
    GraphEntityLinkRequest,
    GraphMetricsResponse,
    ParsedFilingResponse,
    QuestionAnswerRequest,
    QuestionAnswerResponse,
)
from services.alternative_data_provider import AltDataCapability, get_default_alt_router
from services.document_store import FilingType, get_default_document_store
from services.document_parser import parse_filing
from services.document_ai import answer_question, enrich_document
from services.event_detection import detect_events
from services.alt_feature_store import AltDataBundle, get_default_alt_feature_store
from services.alt_search import get_default_search_engine
from services.alt_data_quality import validate_document
from services.knowledge_graph_v2 import get_knowledge_graph
from services.knowledge_graph_enrichment import (
    add_executive,
    add_supplier_relationship,
    dependency_chain,
    graph_metrics_summary,
)

router = APIRouter(prefix="/alt-intelligence", tags=["Alternative Data Intelligence"])


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=List[AltProviderInfo])
def list_alt_providers() -> List[AltProviderInfo]:
    alt_router = get_default_alt_router()
    health = {h["provider"]: h for h in alt_router.health_summary()}
    latency = {l["provider"]: l for l in alt_router.latency_summary()}
    quality = alt_router.quality_scores()
    caps = alt_router.capabilities_matrix()

    results = []
    for provider in alt_router.providers:
        name = provider.name
        h = health.get(name, {})
        lat = latency.get(name, {})
        results.append(AltProviderInfo(
            name=name,
            priority=provider.config.priority,
            capabilities=caps.get(name, []),
            is_healthy=h.get("is_healthy", True),
            p50_latency_ms=lat.get("p50_ms", 0.0),
            p95_latency_ms=lat.get("p95_ms", 0.0),
            error_rate=lat.get("error_rate", 0.0),
            quality_score=quality.get(name, 0.0),
        ))
    return results


@router.get("/providers/capabilities", response_model=AltCapabilitiesMatrixResponse)
def alt_provider_capabilities() -> AltCapabilitiesMatrixResponse:
    return AltCapabilitiesMatrixResponse(providers=get_default_alt_router().capabilities_matrix())


@router.get("/providers/health", response_model=AltHealthSummaryResponse)
def alt_provider_health() -> AltHealthSummaryResponse:
    alt_router = get_default_alt_router()
    return AltHealthSummaryResponse(
        providers=alt_router.health_summary(),
        latency=alt_router.latency_summary(),
    )


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def _filing_type_from_str(value: str) -> FilingType:
    try:
        return FilingType(value)
    except ValueError:
        valid = [f.value for f in FilingType]
        raise HTTPException(status_code=422, detail=f"Invalid filing_type '{value}'. Valid: {valid}")


@router.post("/documents/ingest", response_model=DocumentIngestResponse)
def ingest_document(req: DocumentIngestRequest) -> DocumentIngestResponse:
    filing_type = _filing_type_from_str(req.filing_type)
    store = get_default_document_store()
    try:
        meta = store.ingest(
            doc_id=req.doc_id, symbol=req.symbol, filing_type=filing_type,
            text=req.text, source=req.source, published_at=req.published_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    quality = validate_document(req.doc_id, req.text, {
        "doc_id": req.doc_id, "symbol": req.symbol, "filing_type": req.filing_type, "source": req.source,
    })

    search_engine = get_default_search_engine()
    doc = store.get(req.doc_id, req.symbol, filing_type)
    if doc is not None:
        search_engine.index_document(doc)

    return DocumentIngestResponse(
        doc_id=meta.doc_id, symbol=meta.symbol, filing_type=meta.filing_type.value,
        version=meta.version, checksum=meta.checksum, size_bytes=meta.size_bytes,
        quality_score=quality.quality_score, quality_passed=quality.passed,
    )


@router.get("/documents", response_model=List[DocumentMetadataResponse])
def list_documents(symbol: Optional[str] = None, filing_type: Optional[str] = None) -> List[DocumentMetadataResponse]:
    ft = _filing_type_from_str(filing_type) if filing_type else None
    store = get_default_document_store()
    return [
        DocumentMetadataResponse(
            doc_id=m.doc_id, symbol=m.symbol, filing_type=m.filing_type.value, source=m.source,
            version=m.version, checksum=m.checksum, size_bytes=m.size_bytes,
            published_at=m.published_at, extra=m.extra,
        )
        for m in store.list_documents(symbol=symbol, filing_type=ft)
    ]


@router.get("/documents/{doc_id}/parse", response_model=ParsedFilingResponse)
def parse_document(doc_id: str, symbol: str = Query(...), filing_type: str = Query(...)) -> ParsedFilingResponse:
    ft = _filing_type_from_str(filing_type)
    store = get_default_document_store()
    doc = store.get(doc_id, symbol, ft)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    parsed = parse_filing(doc_id, doc.text)
    return ParsedFilingResponse(
        doc_id=parsed.doc_id,
        sections={name: {"text_preview": sec.text[:240], "line_items": sec.line_items} for name, sec in parsed.sections.items()},
        entities=parsed.entities,
    )


@router.get("/documents/stats")
def document_store_stats() -> Dict[str, Any]:
    return get_default_document_store().stats()


# ---------------------------------------------------------------------------
# Document AI
# ---------------------------------------------------------------------------

@router.post("/documents/enrich", response_model=EnrichTextResponse)
def enrich_text(req: EnrichTextRequest) -> EnrichTextResponse:
    result = enrich_document(req.text, corpus_texts=req.corpus_texts, summary_sentences=req.summary_sentences)
    payload = result.to_dict()
    return EnrichTextResponse(**payload)


@router.post("/documents/qa", response_model=QuestionAnswerResponse)
def question_answer(req: QuestionAnswerRequest) -> QuestionAnswerResponse:
    result = answer_question(req.question, req.text)
    return QuestionAnswerResponse(**result)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.post("/events/detect", response_model=EventDetectionResponse)
def detect_alt_events(req: EventDetectionRequest) -> EventDetectionResponse:
    events = detect_events(req.text, symbol=req.symbol, source_doc_id=req.source_doc_id)
    return EventDetectionResponse(
        symbol=req.symbol.upper(),
        events=[AltEventResponse(**e.to_dict()) for e in events],
        event_count=len(events),
    )


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

@router.post("/features/compute", response_model=AltFeatureComputeResponse)
def compute_alt_features(req: AltFeatureComputeRequest) -> AltFeatureComputeResponse:
    events = []
    for text in req.document_texts:
        events.extend(detect_events(text, symbol=req.symbol))

    bundle = AltDataBundle(
        symbol=req.symbol,
        documents=[{"text": t} for t in req.document_texts],
        events=events,
        insider_buys=req.insider_buys,
        insider_sells=req.insider_sells,
        executive_changes=req.executive_changes,
        total_executives=req.total_executives,
        earnings_surprises=req.earnings_surprises,
        patent_counts_by_period=req.patent_counts_by_period,
        supplier_concentration_shares=req.supplier_concentration_shares,
        customer_concentration_shares=req.customer_concentration_shares,
        news_mentions_by_period=req.news_mentions_by_period,
        social_mentions_by_period=req.social_mentions_by_period,
        search_trend_values=req.search_trend_values,
        esg_score=req.esg_score,
        transcript_texts=req.transcript_texts,
        window_days=req.window_days,
    )
    store = get_default_alt_feature_store()
    features = store.compute(bundle, use_cache=False)
    return AltFeatureComputeResponse(symbol=req.symbol.upper(), features=features)


@router.get("/features/catalog")
def alt_feature_catalog() -> Dict[str, Any]:
    store = get_default_alt_feature_store()
    return {"features": store.catalog(), "total": len(store.catalog())}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.post("/search", response_model=AltSearchResponse)
def search_alt_data(req: AltSearchRequest) -> AltSearchResponse:
    engine = get_default_search_engine()
    if req.semantic and req.query:
        hits = engine.semantic_search(req.query, limit=req.limit)
    else:
        hits = engine.search(
            query=req.query, symbol=req.symbol, filing_type=req.filing_type,
            executive=req.executive, company=req.company, since=req.since,
            until=req.until, limit=req.limit,
        )
    return AltSearchResponse(
        hits=[AltSearchHitResponse(doc_id=h.doc_id, symbol=h.symbol, filing_type=h.filing_type, score=h.score, snippet=h.snippet) for h in hits],
        hit_count=len(hits),
    )


@router.get("/search/companies")
def search_companies(q: str = Query(min_length=1)) -> Dict[str, List[str]]:
    return {"companies": get_default_search_engine().search_companies(q)}


@router.get("/search/executives")
def search_executives(q: str = Query(min_length=1)) -> Dict[str, List[str]]:
    return {"executives": get_default_search_engine().search_executives(q)}


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------

@router.post("/knowledge/executives")
def link_executive(req: GraphEntityLinkRequest) -> Dict[str, str]:
    kg = get_knowledge_graph()
    add_executive(kg, req.entity_id, req.entity_name, req.related_company_id, req.relation_label or "")
    return {"status": "linked"}


@router.post("/knowledge/suppliers")
def link_supplier(req: GraphEntityLinkRequest) -> Dict[str, str]:
    kg = get_knowledge_graph()
    add_supplier_relationship(kg, req.entity_id, req.entity_name, req.related_company_id, req.score)
    return {"status": "linked"}


@router.get("/knowledge/metrics", response_model=GraphMetricsResponse)
def knowledge_graph_metrics() -> GraphMetricsResponse:
    kg = get_knowledge_graph()
    return GraphMetricsResponse(**graph_metrics_summary(kg))


@router.post("/knowledge/dependency-chain", response_model=DependencyChainResponse)
def knowledge_dependency_chain(req: DependencyChainRequest) -> DependencyChainResponse:
    kg = get_knowledge_graph()
    path = dependency_chain(kg, req.source_id, req.target_id, max_depth=req.max_depth)
    return DependencyChainResponse(path=path, found=path is not None)


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

@router.post("/quality/check", response_model=DocQualityCheckResponse)
def check_document_quality(req: DocQualityCheckRequest) -> DocQualityCheckResponse:
    result = validate_document(req.doc_id, req.text, req.metadata)
    return DocQualityCheckResponse(**result.to_dict())
