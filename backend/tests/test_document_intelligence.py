"""Tests for M6 Document Intelligence — ingestion, chunking, and CRUD."""
from __future__ import annotations
import uuid
import pytest
from sqlalchemy.orm import Session

from models.document_intelligence import Document, DocumentChunk, CopilotSession
from schemas.document_intelligence import DocumentIngest, CopilotSessionCreate
from services.document_ingestion import ingest_document, delete_document, reindex_document, _split_into_chunks, _count_tokens, _extract_tickers


# ---------------------------------------------------------------------------
# Chunking utilities
# ---------------------------------------------------------------------------

def test_split_into_chunks_basic():
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = _split_into_chunks(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.split()) <= 20


def test_split_empty_text():
    assert _split_into_chunks("") == []


def test_split_short_text():
    chunks = _split_into_chunks("hello world", chunk_size=512)
    assert len(chunks) == 1
    assert chunks[0] == "hello world"


def test_split_overlap():
    text = " ".join([f"w{i}" for i in range(30)])
    chunks = _split_into_chunks(text, chunk_size=10, overlap=3)
    assert len(chunks) >= 3


def test_count_tokens():
    assert _count_tokens("hello world") == 2
    assert _count_tokens("") == 1
    assert _count_tokens("a b c d e") == 5


def test_extract_tickers():
    text = "AAPL and MSFT reported earnings. The Fed mentioned GDP growth."
    tickers = _extract_tickers(text)
    assert "AAPL" in tickers
    assert "MSFT" in tickers


def test_extract_tickers_filters_common():
    text = "THE company AND its OR subsidiaries IN the market"
    tickers = _extract_tickers(text)
    assert "THE" not in tickers
    assert "AND" not in tickers


# ---------------------------------------------------------------------------
# Document ingestion
# ---------------------------------------------------------------------------

def test_ingest_document_basic(db: Session):
    data = DocumentIngest(title="AAPL 10-K 2024", doc_type="SEC_FILING", content="Apple Inc. reported record revenue of $100 billion for fiscal 2024. AAPL shares rose significantly.")
    doc = ingest_document(db, data)
    assert doc.id is not None
    assert doc.title == "AAPL 10-K 2024"
    assert doc.doc_type == "SEC_FILING"
    assert doc.status == "INDEXED"
    assert doc.chunk_count > 0
    assert doc.file_size > 0


def test_ingest_document_creates_chunks(db: Session):
    content = " ".join([f"word{i}" for i in range(600)])
    data = DocumentIngest(title="Long Doc", content=content)
    doc = ingest_document(db, data)
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    assert len(chunks) == doc.chunk_count
    assert len(chunks) > 1


def test_ingest_document_with_tickers(db: Session):
    data = DocumentIngest(title="Report", content="Revenue analysis", tickers=["MSFT", "GOOGL"])
    doc = ingest_document(db, data)
    assert "MSFT" in doc.tickers
    assert "GOOGL" in doc.tickers


def test_ingest_document_extracts_tickers_auto(db: Session):
    data = DocumentIngest(title="News", content="NVDA beat expectations while TSLA missed. The CEO of AMZN commented.")
    doc = ingest_document(db, data)
    assert doc.tickers is not None
    assert isinstance(doc.tickers, list)


def test_ingest_with_metadata(db: Session):
    data = DocumentIngest(title="Memo", content="Internal research memo.", metadata={"author": "analyst", "category": "equity"})
    doc = ingest_document(db, data)
    assert doc.metadata_ == {"author": "analyst", "category": "equity"}


def test_ingest_short_doc_one_chunk(db: Session):
    data = DocumentIngest(title="Short", content="This is a very short document.")
    doc = ingest_document(db, data)
    assert doc.chunk_count == 1


def test_ingest_chunks_have_embeddings(db: Session):
    data = DocumentIngest(title="Embedded", content="This document should have chunk embeddings stored.")
    doc = ingest_document(db, data)
    chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).first()
    assert chunk is not None
    assert chunk.embedding is not None
    assert isinstance(chunk.embedding, list)
    assert len(chunk.embedding) == 128


def test_ingest_chunks_ordered(db: Session):
    content = " ".join([f"word{i}" for i in range(600)])
    data = DocumentIngest(title="Ordered", content=content)
    doc = ingest_document(db, data)
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index).all()
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(indices)))


def test_delete_document(db: Session):
    data = DocumentIngest(title="Del Doc", content="To be deleted.")
    doc = ingest_document(db, data)
    doc_id = doc.id
    assert delete_document(db, doc_id) is True
    assert db.query(Document).filter(Document.id == doc_id).first() is None


def test_delete_document_cascades_chunks(db: Session):
    content = " ".join([f"w{i}" for i in range(600)])
    data = DocumentIngest(title="Cascade Del", content=content)
    doc = ingest_document(db, data)
    doc_id = doc.id
    delete_document(db, doc_id)
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
    assert len(chunks) == 0


def test_delete_document_missing(db: Session):
    assert delete_document(db, uuid.uuid4()) is False


def test_reindex_document(db: Session):
    content = " ".join([f"word{i}" for i in range(600)])
    data = DocumentIngest(title="Reindex", content=content)
    doc = ingest_document(db, data)
    original_count = doc.chunk_count
    reindexed = reindex_document(db, doc.id)
    assert reindexed is not None
    assert reindexed.status == "INDEXED"
    assert reindexed.chunk_count == original_count


def test_reindex_missing(db: Session):
    assert reindex_document(db, uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# Copilot Session model
# ---------------------------------------------------------------------------

def test_create_copilot_session(db: Session):
    session = CopilotSession(title="Test Session", session_type="CHAT", messages=[], context_docs=[])
    db.add(session)
    db.flush()
    assert session.id is not None
    assert session.title == "Test Session"


def test_copilot_session_messages_json(db: Session):
    msgs = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    session = CopilotSession(title="Msgs", messages=msgs)
    db.add(session)
    db.flush()
    fetched = db.query(CopilotSession).filter(CopilotSession.id == session.id).first()
    assert len(fetched.messages) == 2
    assert fetched.messages[0]["role"] == "user"
