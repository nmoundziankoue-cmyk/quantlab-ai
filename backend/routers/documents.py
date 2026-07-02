from __future__ import annotations
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.document_intelligence import Document
from schemas.document_intelligence import (
    DocumentIngest, DocumentResponse, DocumentChunkResponse,
    DocumentSearchRequest, DocumentSearchResponse,
    AskDocumentRequest, CitedAnswer,
)
from services.document_ingestion import ingest_document, delete_document, reindex_document
from services.rag_engine import search_documents, ask_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def ingest(data: DocumentIngest, db: Session = Depends(get_db)):
    doc = ingest_document(db, data)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=List[DocumentResponse])
def list_documents(doc_type: Optional[str] = None, status_filter: Optional[str] = Query(None, alias="status"), ticker: Optional[str] = None, page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    q = db.query(Document)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type.upper())
    if status_filter:
        q = q.filter(Document.status == status_filter.upper())
    if ticker:
        q = q.filter(Document.tickers.contains([ticker.upper()]))
    return q.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doc(document_id: uuid.UUID, db: Session = Depends(get_db)):
    if not delete_document(db, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    db.commit()


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
def reindex(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = reindex_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or has no content")
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/search", response_model=DocumentSearchResponse)
def search(req: DocumentSearchRequest, db: Session = Depends(get_db)):
    return search_documents(db, req)


@router.post("/ask", response_model=CitedAnswer)
def ask(req: AskDocumentRequest, db: Session = Depends(get_db)):
    return ask_document(db, req)
