"""Tests for M6 RAG engine — search and QA."""
from __future__ import annotations
import pytest
from sqlalchemy.orm import Session

from schemas.document_intelligence import (
    DocumentIngest, DocumentSearchRequest, AskDocumentRequest,
)
from services.document_ingestion import ingest_document
from services.rag_engine import search_documents, ask_document
from services.embeddings import (
    compute_embedding, cosine_similarity, keyword_score, hybrid_score,
    EMBEDDING_DIM, EMBEDDING_MODEL,
)


# ---------------------------------------------------------------------------
# Embedding tests (pure, no DB)
# ---------------------------------------------------------------------------

def test_embedding_dimension():
    emb = compute_embedding("Apple quarterly earnings beat expectations")
    assert len(emb) == EMBEDDING_DIM


def test_embedding_deterministic():
    text = "Microsoft Azure cloud revenue grew 29 percent"
    e1 = compute_embedding(text)
    e2 = compute_embedding(text)
    assert e1 == e2


def test_embedding_unit_norm():
    import math
    emb = compute_embedding("NVDA semiconductor chip market leader")
    norm = math.sqrt(sum(x * x for x in emb))
    assert abs(norm - 1.0) < 1e-6


def test_embedding_empty_text():
    emb = compute_embedding("")
    assert len(emb) == EMBEDDING_DIM
    assert all(v == 0.0 for v in emb)


def test_cosine_similarity_identical():
    emb = compute_embedding("identical text")
    score = cosine_similarity(emb, emb)
    assert abs(score - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    e1 = [1.0] + [0.0] * (EMBEDDING_DIM - 1)
    e2 = [0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2)
    assert cosine_similarity(e1, e2) == 0.0


def test_cosine_similarity_similar_texts():
    e1 = compute_embedding("Apple iPhone revenue growth quarterly earnings")
    e2 = compute_embedding("Apple quarterly earnings iPhone revenue")
    score = cosine_similarity(e1, e2)
    assert score > 0.5


def test_cosine_similarity_dissimilar_texts():
    e1 = compute_embedding("Apple iPhone technology consumer electronics")
    e2 = compute_embedding("oil pipeline infrastructure commodity pricing")
    score_similar = cosine_similarity(compute_embedding("Apple tech"), e1)
    score_dissimilar = cosine_similarity(compute_embedding("Apple tech"), e2)
    assert score_similar >= score_dissimilar


def test_keyword_score_full_match():
    score = keyword_score("apple earnings beat", "apple quarterly earnings beat expectations")
    assert score == 1.0


def test_keyword_score_partial_match():
    score = keyword_score("apple msft", "apple quarterly revenue")
    assert 0 < score < 1.0


def test_keyword_score_no_match():
    score = keyword_score("xyz123", "apple quarterly earnings")
    assert score == 0.0


def test_hybrid_score_range():
    e1 = compute_embedding("semiconductor")
    e2 = compute_embedding("semiconductor chip NVDA GPU")
    score = hybrid_score("semiconductor GPU", "semiconductor chip NVDA GPU", e1, e2)
    assert 0.0 <= score <= 1.0


def test_embedding_model_name():
    assert EMBEDDING_MODEL == "tfidf-128-v1"


# ---------------------------------------------------------------------------
# Semantic search (requires DB)
# ---------------------------------------------------------------------------

def test_search_returns_results(db: Session):
    ingest_document(db, DocumentIngest(title="AAPL Report", content="Apple iPhone revenue grew significantly in Q4. AAPL stock price increased after earnings beat."))
    ingest_document(db, DocumentIngest(title="MSFT Report", content="Microsoft Azure cloud computing revenue grew 29 percent. MSFT earnings exceeded analyst expectations."))
    req = DocumentSearchRequest(query="Apple iPhone revenue", top_k=5, search_type="KEYWORD")
    result = search_documents(db, req)
    assert result.total_results > 0
    assert result.query == "Apple iPhone revenue"


def test_search_semantic(db: Session):
    ingest_document(db, DocumentIngest(title="Tech Earnings", content="Semiconductor chip demand surged driven by AI workloads. GPU allocation increased significantly."))
    req = DocumentSearchRequest(query="artificial intelligence hardware", top_k=5, search_type="SEMANTIC")
    result = search_documents(db, req)
    assert isinstance(result.results, list)


def test_search_hybrid(db: Session):
    ingest_document(db, DocumentIngest(title="Hybrid Test", content="Federal Reserve interest rate decision impacts bond yields and equity valuations."))
    req = DocumentSearchRequest(query="Federal Reserve rate", top_k=5, search_type="HYBRID")
    result = search_documents(db, req)
    assert result.search_type == "HYBRID"


def test_search_top_k_limit(db: Session):
    ingest_document(db, DocumentIngest(title="Large Doc", content=" ".join([f"keyword topic {i}" for i in range(600)])))
    req = DocumentSearchRequest(query="keyword topic", top_k=2, search_type="KEYWORD")
    result = search_documents(db, req)
    assert len(result.results) <= 2


def test_search_result_has_score(db: Session):
    ingest_document(db, DocumentIngest(title="Scored", content="NVDA earnings beat analyst estimates for GPU revenue."))
    req = DocumentSearchRequest(query="NVDA GPU revenue", top_k=5, search_type="KEYWORD")
    result = search_documents(db, req)
    for r in result.results:
        assert 0.0 <= r.score <= 1.0


def test_search_result_fields(db: Session):
    ingest_document(db, DocumentIngest(title="Field Test", doc_type="SEC_FILING", content="Revenue and earnings for the fiscal year."))
    req = DocumentSearchRequest(query="revenue earnings", top_k=3, search_type="KEYWORD")
    result = search_documents(db, req)
    if result.results:
        r = result.results[0]
        assert r.document_title == "Field Test"
        assert r.doc_type == "SEC_FILING"
        assert r.chunk_index >= 0
        assert r.content


def test_search_empty_db_no_crash(db: Session):
    req = DocumentSearchRequest(query="nothing", top_k=5)
    result = search_documents(db, req)
    assert result.total_results == 0


def test_search_filter_doc_type(db: Session):
    ingest_document(db, DocumentIngest(title="Transcript", doc_type="EARNINGS_TRANSCRIPT", content="CEO discussed revenue guidance and margin expansion."))
    ingest_document(db, DocumentIngest(title="Filing", doc_type="SEC_FILING", content="Revenue and expenses disclosed in 10-K filing."))
    req = DocumentSearchRequest(query="revenue", top_k=10, search_type="KEYWORD", doc_types=["EARNINGS_TRANSCRIPT"])
    result = search_documents(db, req)
    for r in result.results:
        assert r.doc_type == "EARNINGS_TRANSCRIPT"


# ---------------------------------------------------------------------------
# RAG QA
# ---------------------------------------------------------------------------

def test_ask_document_returns_answer(db: Session):
    ingest_document(db, DocumentIngest(title="AAPL Q4", content="Apple reported EPS of $2.18 for Q4 2024, beating consensus of $2.05. Revenue was $119 billion."))
    req = AskDocumentRequest(question="What was Apple EPS in Q4 2024?", top_k=3)
    answer = ask_document(db, req)
    assert answer.question == "What was Apple EPS in Q4 2024?"
    assert isinstance(answer.answer, str)
    assert len(answer.answer) > 0
    assert 0.0 <= answer.confidence <= 1.0


def test_ask_document_with_citations(db: Session):
    ingest_document(db, DocumentIngest(title="Cited Doc", content="NVDA gross margin expanded to 74% driven by data center GPU demand. Revenue was $22 billion."))
    req = AskDocumentRequest(question="What is NVDA gross margin?", top_k=3)
    answer = ask_document(db, req)
    assert isinstance(answer.citations, list)


def test_ask_document_no_docs_graceful(db: Session):
    req = AskDocumentRequest(question="What is the meaning of alpha?", top_k=3)
    answer = ask_document(db, req)
    assert isinstance(answer.answer, str)
    assert answer.confidence == 0.0


def test_ask_document_with_specific_ids(db: Session):
    doc = ingest_document(db, DocumentIngest(title="Specific", content="This document contains specific information about bond duration and yield curve."))
    req = AskDocumentRequest(question="bond duration yield", document_ids=[doc.id], top_k=3)
    answer = ask_document(db, req)
    assert answer.model_used == "deterministic-rag-v1"


def test_ask_model_used(db: Session):
    ingest_document(db, DocumentIngest(title="Any", content="Some content for testing."))
    req = AskDocumentRequest(question="some question")
    answer = ask_document(db, req)
    assert answer.model_used == "deterministic-rag-v1"
