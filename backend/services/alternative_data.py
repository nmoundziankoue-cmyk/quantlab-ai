from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.alternative_data import AlternativeDataEvent, EventCluster
from schemas.alternative_data import (
    AlternativeDataEventIngest, BatchIngestRequest, BatchIngestResponse,
    EventSearchRequest, SentimentSummary, EventClusterResponse,
)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_URGENCY_KEYWORDS = {"breaking", "urgent", "alert", "crash", "surge", "plunge", "halt", "fda", "recall", "indictment"}
_IMPORTANCE_MAP = {
    "EARNINGS_TRANSCRIPT": 0.85,
    "SEC_FILING": 0.80,
    "INSIDER_TRANSACTION": 0.75,
    "OPTIONS_FLOW": 0.70,
    "CONGRESS_TRADING": 0.72,
    "NEWS": 0.60,
    "MACRO_EVENT": 0.80,
    "CENTRAL_BANK": 0.88,
    "ANALYST_UPGRADE": 0.65,
    "ANALYST_DOWNGRADE": 0.65,
    "PATENT_FILING": 0.50,
    "SOCIAL_SENTIMENT": 0.40,
    "JOB_POSTINGS": 0.45,
    "APP_RANKING": 0.45,
    "SHORT_INTEREST": 0.68,
    "COMMODITY_EVENT": 0.60,
}
_RELIABILITY_MAP = {
    "SEC_FILING": 0.98, "CENTRAL_BANK": 0.98, "EARNINGS_TRANSCRIPT": 0.95,
    "INSIDER_TRANSACTION": 0.90, "CONGRESS_TRADING": 0.90, "OPTIONS_FLOW": 0.75,
    "NEWS": 0.65, "ANALYST_UPGRADE": 0.70, "ANALYST_DOWNGRADE": 0.70,
    "SOCIAL_SENTIMENT": 0.40, "PATENT_FILING": 0.85,
}


def _compute_urgency(headline: str) -> float:
    lower = headline.lower()
    matches = sum(1 for kw in _URGENCY_KEYWORDS if kw in lower)
    return min(0.1 * matches + 0.1, 1.0)


def _compute_sentiment(headline: str, content: Optional[str]) -> float:
    text = (headline + " " + (content or "")).lower()
    pos = {"growth", "beat", "surge", "profit", "record", "strong", "gain", "buy", "upgrade", "positive"}
    neg = {"miss", "loss", "decline", "fall", "crash", "risk", "warning", "sell", "downgrade", "negative", "cut"}
    p_score = sum(1 for w in pos if w in text)
    n_score = sum(1 for w in neg if w in text)
    total = p_score + n_score
    if total == 0:
        return 0.0
    return round((p_score - n_score) / total, 4)


def _compute_market_impact(event_type: str, importance: float, urgency: float) -> float:
    base = importance * 0.7 + urgency * 0.3
    multiplier = 1.2 if event_type in ("EARNINGS_TRANSCRIPT", "CENTRAL_BANK", "MACRO_EVENT") else 1.0
    return round(min(base * multiplier, 1.0), 4)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_event(db: Session, data: AlternativeDataEventIngest) -> AlternativeDataEvent:
    importance = data.importance_score or _IMPORTANCE_MAP.get(data.event_type, 0.5)
    urgency = data.urgency_score or _compute_urgency(data.headline)
    sentiment = data.sentiment_score if data.sentiment_score is not None else _compute_sentiment(data.headline, data.content)
    reliability = data.source_reliability_score or _RELIABILITY_MAP.get(data.event_type, 0.60)
    market_impact = data.market_impact_score or _compute_market_impact(data.event_type, importance, urgency)

    event = AlternativeDataEvent(
        event_type=data.event_type,
        source=data.source,
        source_url=data.source_url,
        headline=data.headline,
        content=data.content,
        tickers=data.tickers or [],
        sectors=data.sectors or [],
        countries=data.countries or [],
        entities=data.entities or [],
        sentiment_score=sentiment,
        importance_score=importance,
        urgency_score=urgency,
        source_reliability_score=reliability,
        market_impact_score=market_impact,
        published_at=data.published_at,
        metadata_=data.metadata,
    )
    db.add(event)
    db.flush()
    return event


def batch_ingest(db: Session, req: BatchIngestRequest) -> BatchIngestResponse:
    ingested = 0
    errors: List[str] = []
    for item in req.events:
        try:
            ingest_event(db, item)
            ingested += 1
        except Exception as e:
            errors.append(str(e))
    db.flush()
    return BatchIngestResponse(ingested=ingested, failed=len(errors), errors=errors)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def list_events(db: Session, req: EventSearchRequest) -> List[AlternativeDataEvent]:
    q = db.query(AlternativeDataEvent)
    if req.event_types:
        q = q.filter(AlternativeDataEvent.event_type.in_(req.event_types))
    if req.tickers:
        for ticker in req.tickers:
            q = q.filter(AlternativeDataEvent.tickers.contains([ticker]))
    if req.sectors:
        for sector in req.sectors:
            q = q.filter(AlternativeDataEvent.sectors.contains([sector]))
    if req.min_importance is not None:
        q = q.filter(AlternativeDataEvent.importance_score >= req.min_importance)
    if req.min_sentiment is not None:
        q = q.filter(AlternativeDataEvent.sentiment_score >= req.min_sentiment)
    if req.max_sentiment is not None:
        q = q.filter(AlternativeDataEvent.sentiment_score <= req.max_sentiment)
    if req.since:
        q = q.filter(AlternativeDataEvent.created_at >= req.since)
    if req.until:
        q = q.filter(AlternativeDataEvent.created_at <= req.until)
    if req.query:
        q_lower = req.query.lower()
        q = q.filter(func.lower(AlternativeDataEvent.headline).contains(q_lower))
    return q.order_by(AlternativeDataEvent.created_at.desc()).offset((req.page - 1) * req.page_size).limit(req.page_size).all()


def get_event(db: Session, event_id: uuid.UUID) -> Optional[AlternativeDataEvent]:
    return db.query(AlternativeDataEvent).filter(AlternativeDataEvent.id == event_id).first()


def ticker_timeline(db: Session, ticker: str, limit: int = 50) -> List[AlternativeDataEvent]:
    return (
        db.query(AlternativeDataEvent)
        .filter(AlternativeDataEvent.tickers.contains([ticker]))
        .order_by(AlternativeDataEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def ticker_sentiment(db: Session, ticker: str) -> SentimentSummary:
    events = ticker_timeline(db, ticker, limit=200)
    if not events:
        return SentimentSummary(ticker=ticker, avg_sentiment=0.0, event_count=0, bullish_count=0, bearish_count=0, neutral_count=0, latest_event_at=None)
    sentiments = [float(e.sentiment_score) for e in events if e.sentiment_score is not None]
    avg = sum(sentiments) / len(sentiments) if sentiments else 0.0
    bullish = sum(1 for s in sentiments if s > 0.1)
    bearish = sum(1 for s in sentiments if s < -0.1)
    neutral = len(sentiments) - bullish - bearish
    latest = max((e.created_at for e in events), default=None)
    return SentimentSummary(
        ticker=ticker, avg_sentiment=round(avg, 4), event_count=len(events),
        bullish_count=bullish, bearish_count=bearish, neutral_count=neutral, latest_event_at=latest,
    )


def importance_feed(db: Session, limit: int = 20, min_importance: float = 0.7) -> List[AlternativeDataEvent]:
    return (
        db.query(AlternativeDataEvent)
        .filter(AlternativeDataEvent.importance_score >= min_importance)
        .order_by(AlternativeDataEvent.importance_score.desc(), AlternativeDataEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def list_clusters(db: Session) -> List[EventCluster]:
    return db.query(EventCluster).order_by(EventCluster.event_count.desc()).limit(50).all()


def build_clusters(db: Session) -> List[EventCluster]:
    db.query(EventCluster).delete()
    events = db.query(AlternativeDataEvent).filter(AlternativeDataEvent.importance_score >= 0.5).order_by(AlternativeDataEvent.created_at.desc()).limit(200).all()
    cluster_map: Dict[str, List[AlternativeDataEvent]] = {}
    for event in events:
        label = event.event_type
        cluster_map.setdefault(label, []).append(event)
    clusters = []
    for label, evs in cluster_map.items():
        all_tickers: List[str] = []
        sentiments = []
        importances = []
        for e in evs:
            if e.tickers:
                all_tickers.extend(e.tickers)
            if e.sentiment_score is not None:
                sentiments.append(float(e.sentiment_score))
            if e.importance_score is not None:
                importances.append(float(e.importance_score))
        from collections import Counter
        top_tickers = [t for t, _ in Counter(all_tickers).most_common(10)]
        cluster = EventCluster(
            cluster_label=label,
            event_count=len(evs),
            representative_event_id=evs[0].id if evs else None,
            topics=[label],
            tickers=top_tickers,
            avg_sentiment=round(sum(sentiments) / len(sentiments), 4) if sentiments else None,
            avg_importance=round(sum(importances) / len(importances), 4) if importances else None,
        )
        db.add(cluster)
        clusters.append(cluster)
    db.flush()
    return clusters
