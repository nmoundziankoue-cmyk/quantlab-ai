"""M14 Phase 12 — Tests: alternative data search engine (Phase 8).

Semantic search scores are cosine similarity in [-1, 1].
"""
import pytest
from services.document_store import FilingType, DocumentStore
from services.alt_search import (
    IndexedDocument,
    SearchHit,
    AltSearchEngine,
    get_default_search_engine,
)


@pytest.fixture()
def engine():
    return AltSearchEngine()


@pytest.fixture()
def store_with_docs():
    s = DocumentStore()
    s.ingest("d1", "AAPL", FilingType.FORM_10K, "Apple reported record revenue of $90 billion. Strong earnings beat all estimates.")
    s.ingest("d2", "MSFT", FilingType.FORM_10Q, "Microsoft Azure cloud revenue grew 29% year over year. Tim Cook was mentioned.")
    s.ingest("d3", "AAPL", FilingType.FORM_8K, "Apple Board authorized $80 billion share buyback program.")
    return s


def test_document_count_empty(engine):
    assert engine.document_count == 0


def test_index_document(engine, store_with_docs):
    doc = store_with_docs.get("d1", "AAPL", FilingType.FORM_10K)
    engine.index_document(doc)
    assert engine.document_count == 1


def test_index_many(engine, store_with_docs):
    all_docs = store_with_docs.all_documents_full()
    engine.index_many(all_docs)
    assert engine.document_count == len(all_docs)


def test_search_by_query(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(query="revenue", limit=10)
    assert len(hits) > 0


def test_search_hit_type(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(query="revenue")
    for h in hits:
        assert isinstance(h, SearchHit)
        assert h.score >= 0


def test_search_by_symbol(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(symbol="AAPL", limit=10)
    assert all(h.symbol == "AAPL" for h in hits)


def test_search_by_filing_type(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(filing_type="10-K")
    assert all(h.filing_type == "10-K" for h in hits)


def test_search_by_query_and_symbol(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(query="revenue", symbol="AAPL")
    assert all(h.symbol == "AAPL" for h in hits)


def test_search_limit(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(query="revenue", limit=1)
    assert len(hits) <= 1


def test_search_sorted_by_score(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(query="revenue")
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_search_snippet_nonempty(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(query="Apple")
    for h in hits:
        assert len(h.snippet) > 0


def test_search_no_results(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(query="xyznonexistenttoken12345")
    assert hits == []


def test_search_empty_engine():
    eng = AltSearchEngine()
    hits = eng.search(query="revenue")
    assert hits == []


def test_search_by_date_since(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(symbol="AAPL", since="1900-01-01")
    assert isinstance(hits, list)


def test_search_by_date_until(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(symbol="AAPL", until="9999-12-31")
    assert isinstance(hits, list)


def test_semantic_search_returns_list(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.semantic_search("earnings and revenue performance", limit=5)
    assert isinstance(hits, list)
    assert len(hits) > 0


def test_semantic_search_score_is_float(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.semantic_search("cloud computing growth")
    for h in hits:
        assert isinstance(h, SearchHit)
        assert isinstance(h.score, float)


def test_semantic_search_score_bounded(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.semantic_search("earnings growth")
    for h in hits:
        # Cosine similarity is in [-1, 1]; stored rounded
        assert -1.0 <= h.score <= 1.0


def test_search_companies(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    results = engine.search_companies("apple")
    assert isinstance(results, list)


def test_search_executives(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    results = engine.search_executives("Tim")
    assert isinstance(results, list)


def test_reindex_document(engine, store_with_docs):
    doc = store_with_docs.get("d1", "AAPL", FilingType.FORM_10K)
    engine.index_document(doc)
    engine.index_document(doc)  # Should not raise; count stays at 1
    assert engine.document_count == 1


def test_search_by_company_name(engine, store_with_docs):
    engine.index_many(store_with_docs.all_documents_full())
    hits = engine.search(company="Apple", limit=10)
    assert isinstance(hits, list)


def test_singleton():
    e1 = get_default_search_engine()
    e2 = get_default_search_engine()
    assert e1 is e2
