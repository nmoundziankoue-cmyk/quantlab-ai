from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
import services.alternative_data as svc
from schemas.alternative_data import (
    AlternativeDataEventIngest, AlternativeDataEventResponse,
    BatchIngestRequest, BatchIngestResponse,
    EventSearchRequest, SentimentSummary, ImportanceFeedItem, EventClusterResponse,
)

router = APIRouter(prefix="/alternative-data", tags=["alternative-data"])


@router.post("/ingest", response_model=AlternativeDataEventResponse, status_code=status.HTTP_201_CREATED)
def ingest_event(data: AlternativeDataEventIngest, db: Session = Depends(get_db)):
    event = svc.ingest_event(db, data)
    db.commit()
    db.refresh(event)
    return event


@router.post("/ingest/batch", response_model=BatchIngestResponse, status_code=status.HTTP_201_CREATED)
def batch_ingest(req: BatchIngestRequest, db: Session = Depends(get_db)):
    result = svc.batch_ingest(db, req)
    db.commit()
    return result


@router.get("/events", response_model=List[AlternativeDataEventResponse])
def list_events(
    event_type: Optional[str] = None,
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
    min_importance: Optional[float] = None,
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    req = EventSearchRequest(
        event_types=[event_type] if event_type else None,
        tickers=[ticker] if ticker else None,
        sectors=[sector] if sector else None,
        min_importance=min_importance,
        query=query,
        page=page,
        page_size=page_size,
    )
    return svc.list_events(db, req)


@router.post("/events/search", response_model=List[AlternativeDataEventResponse])
def search_events(req: EventSearchRequest, db: Session = Depends(get_db)):
    return svc.list_events(db, req)


@router.get("/events/{event_id}", response_model=AlternativeDataEventResponse)
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    event = svc.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/ticker/{ticker}/timeline", response_model=List[AlternativeDataEventResponse])
def ticker_timeline(ticker: str, limit: int = 50, db: Session = Depends(get_db)):
    return svc.ticker_timeline(db, ticker.upper(), limit=limit)


@router.get("/ticker/{ticker}/sentiment", response_model=SentimentSummary)
def ticker_sentiment(ticker: str, db: Session = Depends(get_db)):
    return svc.ticker_sentiment(db, ticker.upper())


@router.get("/feed/importance")
def importance_feed(limit: int = 20, min_importance: float = 0.7, db: Session = Depends(get_db)):
    events = svc.importance_feed(db, limit=limit, min_importance=min_importance)
    return [{"id": str(e.id), "headline": e.headline, "event_type": e.event_type, "importance_score": float(e.importance_score) if e.importance_score else None, "tickers": e.tickers, "created_at": e.created_at.isoformat()} for e in events]


@router.get("/clusters", response_model=List[EventClusterResponse])
def list_clusters(db: Session = Depends(get_db)):
    return svc.list_clusters(db)


@router.post("/clusters/build")
def build_clusters(db: Session = Depends(get_db)):
    clusters = svc.build_clusters(db)
    db.commit()
    return {"clusters_built": len(clusters)}
