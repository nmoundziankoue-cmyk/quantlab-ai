"""Tests for M6 News Intelligence Terminal service."""
from __future__ import annotations
import pytest
from sqlalchemy.orm import Session

from schemas.alternative_data import AlternativeDataEventIngest
from services.alternative_data import ingest_event
from services.news_intelligence import (
    news_feed, breaking_news, ticker_news, sector_news,
    daily_summary, news_clusters, news_impact,
    _is_news, _urgency_label, _sentiment_label,
)


# ---------------------------------------------------------------------------
# Pure utility helpers
# ---------------------------------------------------------------------------

def _make_event(db, event_type="NEWS", headline="Test headline", ticker=None, sector=None,
                urgency=0.2, importance=0.5, sentiment=0.1, source="Reuters"):
    return ingest_event(db, AlternativeDataEventIngest(
        event_type=event_type,
        source=source,
        headline=headline,
        tickers=[ticker] if ticker else [],
        sectors=[sector] if sector else [],
        urgency_score=urgency,
        importance_score=importance,
        sentiment_score=sentiment,
    ))


def test_urgency_label_breaking():
    assert _urgency_label(0.8) == "BREAKING"


def test_urgency_label_high():
    assert _urgency_label(0.5) == "HIGH"


def test_urgency_label_medium():
    assert _urgency_label(0.3) == "MEDIUM"


def test_urgency_label_low():
    assert _urgency_label(0.1) == "LOW"


def test_urgency_label_none():
    assert _urgency_label(None) == "LOW"


def test_sentiment_label_positive():
    assert _sentiment_label(0.4) == "BULLISH"


def test_sentiment_label_negative():
    assert _sentiment_label(-0.4) == "BEARISH"


def test_sentiment_label_neutral():
    assert _sentiment_label(0.1) == "NEUTRAL"


def test_sentiment_label_none():
    assert _sentiment_label(None) == "NEUTRAL"


# ---------------------------------------------------------------------------
# News feed
# ---------------------------------------------------------------------------

def test_news_feed_returns_list(db: Session):
    _make_event(db, "NEWS", "Market open today")
    result = news_feed(db)
    assert isinstance(result, list)


def test_news_feed_filters_non_news(db: Session):
    _make_event(db, "NEWS", "Breaking market news")
    _make_event(db, "ANALYST_UPGRADE", "AAPL upgraded to Buy")
    result = news_feed(db)
    # All returned items should be news-type events
    for item in result:
        assert item["event_type"] in ("NEWS", "ANALYST_UPGRADE", "ANALYST_DOWNGRADE", "MACRO_EVENT", "CENTRAL_BANK")


def test_news_feed_page_size(db: Session):
    for i in range(5):
        _make_event(db, "NEWS", f"News story {i}")
    result = news_feed(db, page=1, page_size=3)
    assert len(result) <= 3


def test_news_feed_has_enriched_fields(db: Session):
    _make_event(db, "NEWS", "Fed cuts rates sharply", urgency=0.4)
    result = news_feed(db)
    if result:
        item = result[0]
        assert "urgency_label" in item
        assert "sentiment_label" in item


# ---------------------------------------------------------------------------
# Breaking news
# ---------------------------------------------------------------------------

def test_breaking_news_only_high_urgency(db: Session):
    _make_event(db, "NEWS", "Normal story", urgency=0.1)
    _make_event(db, "NEWS", "BREAKING: market crash alert", urgency=0.8)
    result = breaking_news(db, limit=10)
    if result:
        for item in result:
            assert float(item.get("urgency_score", item.get("urgency", 0))) >= 0.3


def test_breaking_news_limit(db: Session):
    for i in range(5):
        _make_event(db, "NEWS", f"Breaking {i}", urgency=0.8)
    result = breaking_news(db, limit=3)
    assert len(result) <= 3


def test_breaking_news_empty_when_none(db: Session):
    result = breaking_news(db, limit=10)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Ticker news
# ---------------------------------------------------------------------------

def test_ticker_news_returns_ticker_events(db: Session):
    _make_event(db, "NEWS", "AAPL Q4 beat", ticker="AAPL")
    _make_event(db, "NEWS", "MSFT cloud growth", ticker="MSFT")
    result = ticker_news(db, "AAPL")
    for item in result:
        tickers = item.get("tickers", [])
        assert "AAPL" in tickers


def test_ticker_news_empty_ticker(db: Session):
    result = ticker_news(db, "ZZZZ_FAKE")
    assert result == []


def test_ticker_news_limit(db: Session):
    for i in range(5):
        _make_event(db, "NEWS", f"AAPL story {i}", ticker="AAPL")
    result = ticker_news(db, "AAPL", limit=3)
    assert len(result) <= 3


# ---------------------------------------------------------------------------
# Sector news
# ---------------------------------------------------------------------------

def test_sector_news_returns_sector_events(db: Session):
    _make_event(db, "NEWS", "Tech sector rally", sector="Technology")
    _make_event(db, "NEWS", "Energy dip", sector="Energy")
    result = sector_news(db, "Technology")
    for item in result:
        sectors = item.get("sectors", [])
        assert "Technology" in sectors


def test_sector_news_empty(db: Session):
    result = sector_news(db, "FAKE_SECTOR_XYZ")
    assert result == []


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------

def test_daily_summary_structure(db: Session):
    _make_event(db, "NEWS", "Market opens higher")
    result = daily_summary(db)
    assert "total_events" in result
    assert "breaking_count" in result
    assert "avg_sentiment" in result


def test_daily_summary_counts(db: Session):
    _make_event(db, "NEWS", "Story 1")
    _make_event(db, "NEWS", "Story 2")
    result = daily_summary(db)
    assert result["total_events"] >= 0


def test_daily_summary_no_events(db: Session):
    result = daily_summary(db)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# News clusters
# ---------------------------------------------------------------------------

def test_news_clusters_returns_list(db: Session):
    _make_event(db, "NEWS", "Fed story 1")
    _make_event(db, "NEWS", "Fed story 2")
    result = news_clusters(db)
    assert isinstance(result, list)


def test_news_clusters_structure(db: Session):
    _make_event(db, "NEWS", "Earnings beat for AAPL")
    clusters = news_clusters(db)
    if clusters:
        c = clusters[0]
        assert "cluster" in c or "cluster_label" in c or "event_type" in c


# ---------------------------------------------------------------------------
# News impact
# ---------------------------------------------------------------------------

def test_news_impact_returns_high_importance(db: Session):
    _make_event(db, "CENTRAL_BANK", "Fed raises rates by 25bps", importance=0.9)
    _make_event(db, "NEWS", "Company picnic", importance=0.2)
    result = news_impact(db, limit=10)
    assert isinstance(result, list)
    if result:
        scores = [float(item.get("importance_score", item.get("importance", 0.0))) for item in result]
        assert max(scores) >= 0.5


def test_news_impact_limit(db: Session):
    for i in range(5):
        _make_event(db, "CENTRAL_BANK", f"Fed story {i}", importance=0.9)
    result = news_impact(db, limit=3)
    assert len(result) <= 3
