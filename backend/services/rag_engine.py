"""RAG (Retrieval-Augmented Generation) engine.

Uses the TF-IDF embedding fallback from services/embeddings.py.
Architecture compatible with pgvector upgrade path.
"""
from __future__ import annotations
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from models.document_intelligence import Document, DocumentChunk
from schemas.document_intelligence import (
    DocumentSearchRequest, DocumentSearchResponse, SearchResultChunk,
    AskDocumentRequest, CitedAnswer,
)
from services.embeddings import compute_embedding, cosine_similarity, keyword_score, hybrid_score


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def _load_chunks(db: Session, doc_ids: Optional[List[uuid.UUID]] = None, doc_types: Optional[List[str]] = None, tickers: Optional[List[str]] = None) -> List[DocumentChunk]:
    q = db.query(DocumentChunk).join(Document, DocumentChunk.document_id == Document.id).filter(Document.status == "INDEXED")
    if doc_ids:
        q = q.filter(DocumentChunk.document_id.in_(doc_ids))
    if doc_types:
        q = q.filter(Document.doc_type.in_(doc_types))
    return q.all()


def _score_chunk(query: str, query_emb: List[float], chunk: DocumentChunk, search_type: str) -> float:
    chunk_emb: List[float] = chunk.embedding or []
    if search_type == "SEMANTIC" and chunk_emb:
        return cosine_similarity(query_emb, chunk_emb)
    elif search_type == "KEYWORD":
        return keyword_score(query, chunk.content)
    else:
        if chunk_emb:
            return hybrid_score(query, chunk.content, query_emb, chunk_emb)
        return keyword_score(query, chunk.content)


def search_documents(db: Session, req: DocumentSearchRequest) -> DocumentSearchResponse:
    query_emb = compute_embedding(req.query)
    chunks = _load_chunks(db, doc_types=req.doc_types)

    scored = []
    doc_cache: dict[uuid.UUID, Document] = {}
    for chunk in chunks:
        score = _score_chunk(req.query, query_emb, chunk, req.search_type)
        if score > 0.01:
            scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: req.top_k]

    results = []
    for chunk, score in top:
        doc = doc_cache.get(chunk.document_id)
        if doc is None:
            doc = db.query(Document).filter(Document.id == chunk.document_id).first()
            if doc:
                doc_cache[chunk.document_id] = doc
        if doc:
            results.append(SearchResultChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=doc.title,
                doc_type=doc.doc_type,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=round(score, 4),
                source_name=doc.source_name,
            ))

    return DocumentSearchResponse(
        query=req.query,
        search_type=req.search_type,
        results=results,
        total_results=len(results),
    )


# ---------------------------------------------------------------------------
# RAG Answer Generation
# ---------------------------------------------------------------------------

def _build_context(chunks: List[SearchResultChunk], max_tokens: int = 2048) -> str:
    parts = []
    total = 0
    for ch in chunks:
        token_est = len(ch.content.split())
        if total + token_est > max_tokens:
            break
        parts.append(f"[Source: {ch.document_title}, chunk {ch.chunk_index + 1}]\n{ch.content}")
        total += token_est
    return "\n\n---\n\n".join(parts)


def _extract_answer(question: str, context: str) -> str:
    q_lower = question.lower()
    ctx_sentences = [s.strip() for s in context.replace("\n", " ").split(".") if len(s.strip()) > 20]
    q_tokens = set(q_lower.split())
    scored = []
    for sent in ctx_sentences:
        s_tokens = set(sent.lower().split())
        overlap = len(q_tokens & s_tokens) / max(len(q_tokens), 1)
        scored.append((sent, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    top_sentences = [s for s, _ in scored[:3] if _]
    if not top_sentences:
        return f"Based on the available documents, a direct answer to '{question}' requires further analysis of the provided context."
    return ". ".join(top_sentences) + "."


def ask_document(db: Session, req: AskDocumentRequest) -> CitedAnswer:
    search_req = DocumentSearchRequest(
        query=req.question,
        top_k=req.top_k,
        search_type="HYBRID",
    )
    if req.document_ids:
        search_req = DocumentSearchRequest(query=req.question, top_k=req.top_k, search_type="HYBRID")
        query_emb = compute_embedding(req.question)
        chunks = _load_chunks(db, doc_ids=req.document_ids)
        scored = []
        doc_cache: dict[uuid.UUID, Document] = {}
        for chunk in chunks:
            score = _score_chunk(req.question, query_emb, chunk, "HYBRID")
            if score > 0.01:
                scored.append((chunk, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[: req.top_k]
        citations = []
        for chunk, score in top:
            doc = doc_cache.get(chunk.document_id) or db.query(Document).filter(Document.id == chunk.document_id).first()
            if doc:
                doc_cache[chunk.document_id] = doc
                citations.append(SearchResultChunk(
                    chunk_id=chunk.id, document_id=chunk.document_id,
                    document_title=doc.title, doc_type=doc.doc_type,
                    chunk_index=chunk.chunk_index, content=chunk.content,
                    score=round(score, 4), source_name=doc.source_name,
                ))
    else:
        search_result = search_documents(db, search_req)
        citations = search_result.results

    context = _build_context(citations)
    if context:
        answer = _extract_answer(req.question, context)
        confidence = citations[0].score if citations else 0.0
    else:
        answer = f"No relevant documents found to answer: '{req.question}'. Please ingest relevant documents first."
        confidence = 0.0

    return CitedAnswer(
        question=req.question,
        answer=answer,
        confidence=round(confidence, 4),
        citations=citations,
        model_used="deterministic-rag-v1",
    )
