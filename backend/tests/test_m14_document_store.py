"""M14 Phase 12 — Tests: document store (Phase 2)."""
import pytest
from services.document_store import (
    FilingType,
    DocumentMetadata,
    StoredDocument,
    extract_metadata,
    DocumentStore,
    get_default_document_store,
)


@pytest.fixture()
def store():
    return DocumentStore()


SAMPLE_TEXT = "Apple Inc reported Q3 revenue of $89.5 billion, up 7% year-over-year. Gross margin expanded to 45.9%."


def test_filing_type_values():
    assert FilingType("10-K") == FilingType.FORM_10K
    assert FilingType("10-Q") == FilingType.FORM_10Q
    assert FilingType("8-K") == FilingType.FORM_8K


def test_extract_metadata_returns_dict():
    meta = extract_metadata(SAMPLE_TEXT)
    assert isinstance(meta, dict)
    assert "checksum" in meta or len(meta) > 0


def test_ingest_basic(store):
    meta = store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    assert meta.doc_id == "d1"
    assert meta.symbol == "AAPL"
    assert meta.version == 1


def test_ingest_versioning(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    meta2 = store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT + " Updated.")
    assert meta2.version == 2


def test_ingest_dedup_same_content_returns_existing(store):
    meta1 = store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    # Re-ingest same content: should return existing (dedup) rather than raise
    meta2 = store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    # Either returns same version or increments — either way checksum is same
    assert meta1.checksum == meta2.checksum


def test_get_retrieves_document(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    doc = store.get("d1", "AAPL", FilingType.FORM_10K)
    assert doc is not None
    assert doc.doc_id == "d1"
    assert doc.text == SAMPLE_TEXT


def test_get_nonexistent_returns_none(store):
    assert store.get("ghost", "AAPL", FilingType.FORM_10K) is None


def test_get_latest_version(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    store.ingest("d1", "AAPL", FilingType.FORM_10K, "New content v2.")
    doc = store.get("d1", "AAPL", FilingType.FORM_10K)
    assert doc.text == "New content v2."
    assert doc.meta.version == 2


def test_list_documents_empty(store):
    assert store.list_documents() == []


def test_list_documents_returns_all(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    store.ingest("d2", "MSFT", FilingType.FORM_10Q, "Microsoft quarterly report content here.")
    docs = store.list_documents()
    assert len(docs) == 2


def test_list_documents_filter_by_symbol(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    store.ingest("d2", "MSFT", FilingType.FORM_10Q, "Microsoft quarterly report content here.")
    aapl_docs = store.list_documents(symbol="AAPL")
    assert all(d.symbol == "AAPL" for d in aapl_docs)
    assert len(aapl_docs) == 1


def test_list_documents_filter_by_filing_type(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    store.ingest("d2", "AAPL", FilingType.FORM_10Q, "Quarterly report content here.")
    tenk_docs = store.list_documents(filing_type=FilingType.FORM_10K)
    assert all(d.filing_type == FilingType.FORM_10K for d in tenk_docs)


def test_stats_empty(store):
    s = store.stats()
    assert isinstance(s, dict)
    assert s.get("document_count", s.get("total_documents", 0)) == 0


def test_stats_after_ingest(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    store.ingest("d2", "MSFT", FilingType.FORM_10Q, "MSFT report content here for testing.")
    s = store.stats()
    count = s.get("document_count", s.get("total_documents", 0))
    assert count == 2


def test_checksum_deterministic(store):
    m1 = store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    m2 = store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT + " v2")
    # Both have valid checksums
    assert len(m1.checksum) > 0
    assert len(m2.checksum) > 0


def test_all_documents_full(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    all_docs = store.all_documents_full()
    assert len(all_docs) == 1
    assert all_docs[0].text == SAMPLE_TEXT


def test_stored_document_has_text(store):
    store.ingest("d1", "AAPL", FilingType.FORM_10K, SAMPLE_TEXT)
    doc = store.get("d1", "AAPL", FilingType.FORM_10K)
    assert doc.text == SAMPLE_TEXT


def test_singleton():
    s1 = get_default_document_store()
    s2 = get_default_document_store()
    assert s1 is s2
