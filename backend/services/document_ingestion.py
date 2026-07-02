"""Document ingestion pipeline: chunk, embed, and index documents."""
from __future__ import annotations
import re
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from models.document_intelligence import Document, DocumentChunk
from schemas.document_intelligence import DocumentIngest
from services.embeddings import compute_embedding, EMBEDDING_MODEL

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Ticker / entity extraction
# ---------------------------------------------------------------------------

_TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")
_COMMON_WORDS = {"A", "I", "THE", "AN", "IN", "OF", "OR", "AND", "TO", "IS", "IT", "BE", "DO", "NO", "ON", "AT", "IF"}


def _extract_tickers(text: str) -> List[str]:
    found = _TICKER_RE.findall(text)
    return list({t for t in found if t not in _COMMON_WORDS and len(t) >= 2})[:20]


# ---------------------------------------------------------------------------
# Core ingestion
# ---------------------------------------------------------------------------

def ingest_document(db: Session, data: DocumentIngest) -> Document:
    text = data.content
    tickers = data.tickers or _extract_tickers(text)

    doc = Document(
        title=data.title,
        doc_type=data.doc_type,
        source_name=data.source_name,
        source_url=data.source_url,
        content=text,
        file_size=len(text.encode("utf-8")),
        status="PROCESSING",
        tickers=tickers,
        sectors=data.sectors,
        entities=data.entities,
        metadata_=data.metadata,
    )
    db.add(doc)
    db.flush()

    raw_chunks = _split_into_chunks(text)
    chunks = []
    for idx, chunk_text in enumerate(raw_chunks):
        embedding = compute_embedding(chunk_text)
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=chunk_text,
            token_count=_count_tokens(chunk_text),
            embedding=embedding,
            embedding_model=EMBEDDING_MODEL,
            metadata_={"doc_type": data.doc_type, "chunk_of": str(doc.id)},
        )
        chunks.append(chunk)

    db.bulk_save_objects(chunks)
    doc.chunk_count = len(chunks)
    doc.status = "INDEXED"
    db.flush()
    return doc


def delete_document(db: Session, doc_id: uuid.UUID) -> bool:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return False
    db.delete(doc)
    db.flush()
    return True


def reindex_document(db: Session, doc_id: uuid.UUID) -> Optional[Document]:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc or not doc.content:
        return None
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
    doc.status = "PROCESSING"
    db.flush()

    raw_chunks = _split_into_chunks(doc.content)
    chunks = []
    for idx, chunk_text in enumerate(raw_chunks):
        embedding = compute_embedding(chunk_text)
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=chunk_text,
            token_count=_count_tokens(chunk_text),
            embedding=embedding,
            embedding_model=EMBEDDING_MODEL,
        )
        chunks.append(chunk)
    db.bulk_save_objects(chunks)
    doc.chunk_count = len(chunks)
    doc.status = "INDEXED"
    db.flush()
    return doc
