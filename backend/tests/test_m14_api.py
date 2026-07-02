"""M14 Phase 12 — Tests: API router /alt-intelligence."""
import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)

INGEST_PAYLOAD = {
    "doc_id": "test_doc_api_1",
    "symbol": "AAPL",
    "filing_type": "10-K",
    "text": (
        "Apple Inc reported quarterly earnings that significantly exceeded analyst expectations. "
        "Revenue grew 15% year over year driven by strong iPhone and Services performance. "
        "CEO Tim Cook stated the company raised guidance for the next fiscal year. "
        "The Board authorized a new $90 billion share repurchase program."
    ),
    "source": "sec.gov",
}


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def test_list_providers():
    r = client.get("/alt-intelligence/providers")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_list_providers_fields():
    r = client.get("/alt-intelligence/providers")
    assert r.status_code == 200
    for p in r.json():
        assert "name" in p
        assert "is_healthy" in p
        assert "capabilities" in p


def test_provider_capabilities():
    r = client.get("/alt-intelligence/providers/capabilities")
    assert r.status_code == 200
    assert "providers" in r.json()


def test_provider_health():
    r = client.get("/alt-intelligence/providers/health")
    assert r.status_code == 200
    data = r.json()
    assert "providers" in data
    assert "latency" in data


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def test_ingest_document():
    r = client.post("/alt-intelligence/documents/ingest", json=INGEST_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert data["doc_id"] == "test_doc_api_1"
    assert data["symbol"] == "AAPL"
    assert "checksum" in data
    assert "quality_score" in data


def test_ingest_document_invalid_filing_type():
    payload = {**INGEST_PAYLOAD, "doc_id": "x_invalid", "filing_type": "NOT_A_TYPE"}
    r = client.post("/alt-intelligence/documents/ingest", json=payload)
    assert r.status_code == 422


def test_ingest_document_missing_text():
    r = client.post("/alt-intelligence/documents/ingest", json={"doc_id": "x", "symbol": "AAPL", "filing_type": "10-K"})
    assert r.status_code == 422


def test_list_documents():
    # Ingest first
    client.post("/alt-intelligence/documents/ingest", json={**INGEST_PAYLOAD, "doc_id": "list_test_1"})
    r = client.get("/alt-intelligence/documents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_documents_filter_by_symbol():
    r = client.get("/alt-intelligence/documents?symbol=AAPL")
    assert r.status_code == 200
    for doc in r.json():
        assert doc["symbol"] == "AAPL"


def test_list_documents_filter_by_filing_type():
    r = client.get("/alt-intelligence/documents?filing_type=10-K")
    assert r.status_code == 200
    for doc in r.json():
        assert doc["filing_type"] == "10-K"


def test_document_stats():
    r = client.get("/alt-intelligence/documents/stats")
    assert r.status_code == 200
    data = r.json()
    # Stats may use "document_count" or "total_documents" depending on implementation
    assert "document_count" in data or "total_documents" in data


def test_parse_document():
    client.post("/alt-intelligence/documents/ingest", json={**INGEST_PAYLOAD, "doc_id": "parse_test_1"})
    r = client.get("/alt-intelligence/documents/parse_test_1/parse?symbol=AAPL&filing_type=10-K")
    assert r.status_code == 200
    data = r.json()
    assert "doc_id" in data
    assert "sections" in data
    assert "entities" in data


def test_parse_document_not_found():
    r = client.get("/alt-intelligence/documents/ghost_doc_xyz/parse?symbol=AAPL&filing_type=10-K")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Document AI
# ---------------------------------------------------------------------------

def test_enrich_text():
    r = client.post("/alt-intelligence/documents/enrich", json={"text": INGEST_PAYLOAD["text"]})
    assert r.status_code == 200
    data = r.json()
    for field in ("entities", "topics", "keywords", "sentiment", "risk", "uncertainty", "readability", "novelty", "summary"):
        assert field in data


def test_enrich_text_missing_body():
    r = client.post("/alt-intelligence/documents/enrich", json={})
    assert r.status_code == 422


def test_question_answer():
    r = client.post("/alt-intelligence/documents/qa", json={
        "question": "What was the revenue growth?",
        "text": INGEST_PAYLOAD["text"],
    })
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "confidence" in data
    assert "sentence_index" in data


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def test_detect_events():
    r = client.post("/alt-intelligence/events/detect", json={
        "text": INGEST_PAYLOAD["text"],
        "symbol": "AAPL",
    })
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert "event_count" in data
    assert isinstance(data["events"], list)


def test_detect_events_empty_text():
    r = client.post("/alt-intelligence/events/detect", json={"text": "", "symbol": "AAPL"})
    assert r.status_code == 422


def test_detect_events_buyback_text():
    r = client.post("/alt-intelligence/events/detect", json={
        "text": "The board authorized a new share repurchase program of up to $90 billion.",
        "symbol": "AAPL",
    })
    assert r.status_code == 200
    data = r.json()
    types = [e["event_type"] for e in data["events"]]
    # Actual event type is "buyback" not "share_buyback"
    assert "buyback" in types


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

def test_feature_catalog():
    r = client.get("/alt-intelligence/features/catalog")
    assert r.status_code == 200
    data = r.json()
    assert "features" in data
    assert data["total"] == 15


def test_compute_features():
    r = client.post("/alt-intelligence/features/compute", json={
        "symbol": "AAPL",
        "document_texts": [INGEST_PAYLOAD["text"]],
        "insider_buys": 10,
        "insider_sells": 4,
    })
    assert r.status_code == 200
    data = r.json()
    assert "features" in data
    assert len(data["features"]) == 15


def test_compute_features_empty_bundle():
    r = client.post("/alt-intelligence/features/compute", json={"symbol": "AAPL"})
    assert r.status_code == 200
    assert "features" in r.json()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def test_search_requires_criterion():
    r = client.post("/alt-intelligence/search", json={"limit": 10})
    assert r.status_code == 422


def test_search_by_symbol():
    r = client.post("/alt-intelligence/search", json={"symbol": "AAPL", "limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert "hits" in data
    assert "hit_count" in data


def test_search_by_query():
    r = client.post("/alt-intelligence/search", json={"query": "revenue", "limit": 10})
    assert r.status_code == 200


def test_search_semantic():
    r = client.post("/alt-intelligence/search", json={"query": "earnings growth", "semantic": True, "limit": 5})
    assert r.status_code == 200


def test_search_companies():
    r = client.get("/alt-intelligence/search/companies?q=apple")
    assert r.status_code == 200
    assert "companies" in r.json()


def test_search_executives():
    r = client.get("/alt-intelligence/search/executives?q=Tim")
    assert r.status_code == 200
    assert "executives" in r.json()


def test_search_companies_missing_q():
    r = client.get("/alt-intelligence/search/companies")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------

def test_knowledge_graph_metrics():
    r = client.get("/alt-intelligence/knowledge/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "node_count" in data
    assert "component_count" in data


def test_link_executive():
    r = client.post("/alt-intelligence/knowledge/executives", json={
        "entity_id": "exec_cook",
        "entity_name": "Tim Cook",
        "related_company_id": "AAPL",
        "relation_label": "CEO",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "linked"


def test_link_supplier():
    r = client.post("/alt-intelligence/knowledge/suppliers", json={
        "entity_id": "TSMC",
        "entity_name": "Taiwan Semiconductor",
        "related_company_id": "AAPL",
        "score": 0.35,
    })
    assert r.status_code == 200


def test_dependency_chain():
    r = client.post("/alt-intelligence/knowledge/dependency-chain", json={
        "source_id": "AAPL",
        "target_id": "MSFT",
        "max_depth": 4,
    })
    assert r.status_code == 200
    data = r.json()
    assert "found" in data
    assert "path" in data


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

def test_quality_check():
    r = client.post("/alt-intelligence/quality/check", json={
        "doc_id": "q1",
        "text": INGEST_PAYLOAD["text"],
        "metadata": {"doc_id": "q1", "symbol": "AAPL", "filing_type": "10-K", "source": "sec.gov"},
    })
    assert r.status_code == 200
    data = r.json()
    assert "quality_score" in data
    assert "passed" in data
    assert "issues" in data


def test_quality_check_bad_text():
    r = client.post("/alt-intelligence/quality/check", json={
        "doc_id": "q2",
        "text": "Short.",
        "metadata": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["passed"] is False
    assert len(data["issues"]) > 0
