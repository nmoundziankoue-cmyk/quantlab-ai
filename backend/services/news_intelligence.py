"""News intelligence service — feeds, clustering, sentiment, impact scoring."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.alternative_data import AlternativeDataEvent


NEWS_EVENT_TYPES = {"NEWS", "ANALYST_UPGRADE", "ANALYST_DOWNGRADE", "MACRO_EVENT", "CENTRAL_BANK"}


def _is_news(event: AlternativeDataEvent) -> bool:
    return event.event_type in NEWS_EVENT_TYPES


def _urgency_label(score: Optional[float]) -> str:
    if score is None:
        return "LOW"
    if score >= 0.7:
        return "BREAKING"
    if score >= 0.4:
        return "HIGH"
    if score >= 0.2:
        return "MEDIUM"
    return "LOW"


def _sentiment_label(score: Optional[float]) -> str:
    if score is None:
        return "NEUTRAL"
    if score > 0.2:
        return "BULLISH"
    if score < -0.2:
        return "BEARISH"
    return "NEUTRAL"


def _enrich_event(event: AlternativeDataEvent) -> Dict[str, Any]:
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "source": event.source,
        "headline": event.headline,
        "tickers": event.tickers or [],
        "sectors": event.sectors or [],
        "sentiment_score": float(event.sentiment_score) if event.sentiment_score is not None else None,
        "sentiment_label": _sentiment_label(event.sentiment_score),
        "importance_score": float(event.importance_score) if event.importance_score is not None else None,
        "urgency_score": float(event.urgency_score) if event.urgency_score is not None else None,
        "urgency_label": _urgency_label(event.urgency_score),
        "market_impact_score": float(event.market_impact_score) if event.market_impact_score is not None else None,
        "published_at": event.published_at.isoformat() if event.published_at else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


# ---------------------------------------------------------------------------
# Feeds
# ---------------------------------------------------------------------------

def news_feed(db: Session, page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
    events = (
        db.query(AlternativeDataEvent)
        .filter(AlternativeDataEvent.event_type.in_(NEWS_EVENT_TYPES))
        .order_by(AlternativeDataEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [_enrich_event(e) for e in events]


def breaking_news(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    events = (
        db.query(AlternativeDataEvent)
        .filter(
            AlternativeDataEvent.event_type.in_(NEWS_EVENT_TYPES),
            AlternativeDataEvent.urgency_score >= 0.6,
        )
        .order_by(AlternativeDataEvent.urgency_score.desc(), AlternativeDataEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_enrich_event(e) for e in events]


def ticker_news(db: Session, ticker: str, limit: int = 50) -> List[Dict[str, Any]]:
    events = (
        db.query(AlternativeDataEvent)
        .filter(
            AlternativeDataEvent.event_type.in_(NEWS_EVENT_TYPES),
            AlternativeDataEvent.tickers.contains([ticker.upper()]),
        )
        .order_by(AlternativeDataEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_enrich_event(e) for e in events]


def sector_news(db: Session, sector: str, limit: int = 50) -> List[Dict[str, Any]]:
    events = (
        db.query(AlternativeDataEvent)
        .filter(
            AlternativeDataEvent.event_type.in_(NEWS_EVENT_TYPES),
            AlternativeDataEvent.sectors.contains([sector]),
        )
        .order_by(AlternativeDataEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_enrich_event(e) for e in events]


def daily_summary(db: Session) -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    events = (
        db.query(AlternativeDataEvent)
        .filter(
            AlternativeDataEvent.event_type.in_(NEWS_EVENT_TYPES),
            AlternativeDataEvent.created_at >= since,
        )
        .all()
    )
    if not events:
        return {
            "period": "last_24h",
            "total_events": 0,
            "breaking_count": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "top_tickers": [],
            "top_sectors": [],
            "avg_sentiment": None,
            "avg_importance": None,
        }

    sentiments = [float(e.sentiment_score) for e in events if e.sentiment_score is not None]
    importances = [float(e.importance_score) for e in events if e.importance_score is not None]
    breaking = sum(1 for e in events if e.urgency_score and float(e.urgency_score) >= 0.6)
    bullish = sum(1 for s in sentiments if s > 0.2)
    bearish = sum(1 for s in sentiments if s < -0.2)

    from collections import Counter
    all_tickers: List[str] = []
    all_sectors: List[str] = []
    for e in events:
        if e.tickers:
            all_tickers.extend(e.tickers)
        if e.sectors:
            all_sectors.extend(e.sectors)

    top_tickers = [t for t, _ in Counter(all_tickers).most_common(10)]
    top_sectors = [s for s, _ in Counter(all_sectors).most_common(5)]

    return {
        "period": "last_24h",
        "total_events": len(events),
        "breaking_count": breaking,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "top_tickers": top_tickers,
        "top_sectors": top_sectors,
        "avg_sentiment": round(sum(sentiments) / len(sentiments), 4) if sentiments else None,
        "avg_importance": round(sum(importances) / len(importances), 4) if importances else None,
    }


def news_clusters(db: Session) -> List[Dict[str, Any]]:
    from collections import Counter
    events = (
        db.query(AlternativeDataEvent)
        .filter(AlternativeDataEvent.event_type.in_(NEWS_EVENT_TYPES))
        .order_by(AlternativeDataEvent.created_at.desc())
        .limit(200)
        .all()
    )
    cluster_map: Dict[str, List[AlternativeDataEvent]] = {}
    for e in events:
        key = e.event_type
        cluster_map.setdefault(key, []).append(e)

    result = []
    for label, evs in cluster_map.items():
        all_tickers: List[str] = []
        for e in evs:
            if e.tickers:
                all_tickers.extend(e.tickers)
        result.append({
            "cluster": label,
            "event_count": len(evs),
            "top_tickers": [t for t, _ in Counter(all_tickers).most_common(5)],
            "latest_headline": evs[0].headline if evs else None,
        })
    return sorted(result, key=lambda x: x["event_count"], reverse=True)


def news_impact(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    events = (
        db.query(AlternativeDataEvent)
        .filter(
            AlternativeDataEvent.event_type.in_(NEWS_EVENT_TYPES),
            AlternativeDataEvent.market_impact_score >= 0.6,
        )
        .order_by(AlternativeDataEvent.market_impact_score.desc())
        .limit(limit)
        .all()
    )
    return [_enrich_event(e) for e in events]
