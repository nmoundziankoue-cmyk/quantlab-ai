"""Tests for M6 Alternative Data Intelligence service."""
from __future__ import annotations
import uuid
import pytest
from sqlalchemy.orm import Session

from schemas.alternative_data import (
    AlternativeDataEventIngest, BatchIngestRequest, EventSearchRequest,
)
from services.alternative_data import (
    ingest_event, batch_ingest, list_events, get_event,
    ticker_timeline, ticker_sentiment, importance_feed,
    list_clusters, build_clusters,
    _compute_urgency, _compute_sentiment, _compute_market_impact,
)


# ---------------------------------------------------------------------------
# Scoring helpers (pure)
# ---------------------------------------------------------------------------

def test_compute_urgency_breaking():
    score = _compute_urgency("BREAKING: Fed announces emergency rate cut")
    assert score > 0.1


def test_compute_urgency_normal():
    score = _compute_urgency("Company reports quarterly earnings")
    assert score >= 0.0


def test_compute_urgency_max():
    score = _compute_urgency("BREAKING URGENT ALERT: crash plunge halt surge")
    assert score <= 1.0


def test_compute_sentiment_positive():
    score = _compute_sentiment("Company beats earnings, strong revenue growth", None)
    assert score > 0.0


def test_compute_sentiment_negative():
    score = _compute_sentiment("Stock crashes on earnings miss, loss reported", None)
    assert score < 0.0


def test_compute_sentiment_neutral():
    score = _compute_sentiment("Company reports quarterly results", "Revenue was in line with expectations")
    assert -1.0 <= score <= 1.0


def test_compute_market_impact_high_importance():
    score = _compute_market_impact("CENTRAL_BANK", 0.88, 0.5)
    assert score > 0.7


def test_compute_market_impact_low_importance():
    score = _compute_market_impact("SOCIAL_SENTIMENT", 0.4, 0.1)
    assert score < 0.5


def test_compute_market_impact_clamped():
    score = _compute_market_impact("EARNINGS_TRANSCRIPT", 1.0, 1.0)
    assert score <= 1.0


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def test_ingest_event_basic(db: Session):
    data = AlternativeDataEventIngest(
        event_type="NEWS",
        source="Reuters",
        headline="AAPL beats Q4 earnings by 6 percent",
        tickers=["AAPL"],
    )
    event = ingest_event(db, data)
    assert event.id is not None
    assert event.event_type == "NEWS"
    assert "AAPL" in event.tickers


def test_ingest_event_scores_auto_computed(db: Session):
    data = AlternativeDataEventIngest(
        event_type="EARNINGS_TRANSCRIPT",
        source="SEC",
        headline="NVDA smashes revenue estimates driven by AI chip demand",
        tickers=["NVDA"],
    )
    event = ingest_event(db, data)
    assert event.importance_score is not None
    assert event.urgency_score is not None
    assert event.sentiment_score is not None
    assert event.source_reliability_score is not None
    assert event.market_impact_score is not None


def test_ingest_event_scores_override(db: Session):
    data = AlternativeDataEventIngest(
        event_type="NEWS",
        source="Test",
        headline="Generic news",
        importance_score=0.9,
        sentiment_score=0.5,
    )
    event = ingest_event(db, data)
    assert abs(float(event.importance_score) - 0.9) < 0.01
    assert abs(float(event.sentiment_score) - 0.5) < 0.01


def test_ingest_event_breaking_sets_high_urgency(db: Session):
    data = AlternativeDataEventIngest(
        event_type="NEWS",
        source="Bloomberg",
        headline="BREAKING: Fed announces emergency rate cut amid market crash",
        tickers=["SPY"],
    )
    event = ingest_event(db, data)
    assert float(event.urgency_score) > 0.0


def test_ingest_event_sec_filing_high_reliability(db: Session):
    data = AlternativeDataEventIngest(
        event_type="SEC_FILING",
        source="SEC EDGAR",
        headline="AAPL files 10-K annual report",
        tickers=["AAPL"],
    )
    event = ingest_event(db, data)
    assert float(event.source_reliability_score) >= 0.95


def test_ingest_event_with_sectors(db: Session):
    data = AlternativeDataEventIngest(
        event_type="MACRO_EVENT",
        source="Fed",
        headline="Fed raises interest rates",
        sectors=["Financials", "Real Estate"],
    )
    event = ingest_event(db, data)
    assert "Financials" in event.sectors


# ---------------------------------------------------------------------------
# Batch ingestion
# ---------------------------------------------------------------------------

def test_batch_ingest(db: Session):
    events = [
        AlternativeDataEventIngest(event_type="NEWS", source="S1", headline="AAPL news", tickers=["AAPL"]),
        AlternativeDataEventIngest(event_type="NEWS", source="S2", headline="MSFT news", tickers=["MSFT"]),
        AlternativeDataEventIngest(event_type="SEC_FILING", source="SEC", headline="GOOGL filing", tickers=["GOOGL"]),
    ]
    req = BatchIngestRequest(events=events)
    result = batch_ingest(db, req)
    assert result.ingested == 3
    assert result.failed == 0


def test_batch_ingest_single(db: Session):
    req = BatchIngestRequest(events=[
        AlternativeDataEventIngest(event_type="NEWS", source="T", headline="Single event"),
    ])
    result = batch_ingest(db, req)
    assert result.ingested == 1


# ---------------------------------------------------------------------------
# Listing / filtering
# ---------------------------------------------------------------------------

def test_list_events_basic(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="H1", tickers=["AAPL"]))
    result = list_events(db, EventSearchRequest())
    assert len(result) >= 1


def test_list_events_filter_event_type(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="news", tickers=["AAPL"]))
    ingest_event(db, AlternativeDataEventIngest(event_type="SEC_FILING", source="SEC", headline="filing", tickers=["AAPL"]))
    result = list_events(db, EventSearchRequest(event_types=["SEC_FILING"]))
    assert all(e.event_type == "SEC_FILING" for e in result)


def test_list_events_filter_ticker(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="AAPL H", tickers=["AAPL"]))
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="MSFT H", tickers=["MSFT"]))
    result = list_events(db, EventSearchRequest(tickers=["AAPL"]))
    for e in result:
        assert "AAPL" in (e.tickers or [])


def test_list_events_filter_min_importance(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="Low", importance_score=0.3))
    ingest_event(db, AlternativeDataEventIngest(event_type="CENTRAL_BANK", source="Fed", headline="High", importance_score=0.9))
    result = list_events(db, EventSearchRequest(min_importance=0.7))
    for e in result:
        assert float(e.importance_score) >= 0.7


def test_get_event(db: Session):
    event = ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="Get Me"))
    found = get_event(db, event.id)
    assert found is not None
    assert found.headline == "Get Me"


def test_get_event_missing(db: Session):
    assert get_event(db, uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# Timeline and sentiment
# ---------------------------------------------------------------------------

def test_ticker_timeline(db: Session):
    for i in range(3):
        ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline=f"AAPL event {i}", tickers=["AAPL"]))
    timeline = ticker_timeline(db, "AAPL")
    assert len(timeline) >= 3


def test_ticker_timeline_empty(db: Session):
    result = ticker_timeline(db, "ZZZZ_FAKE")
    assert result == []


def test_ticker_sentiment_bullish(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="AAPL beats earnings, revenue growth profit record", tickers=["AAPL"], sentiment_score=0.8))
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="AAPL strong buy upgrade", tickers=["AAPL"], sentiment_score=0.7))
    summary = ticker_sentiment(db, "AAPL")
    assert summary.bullish_count + summary.bearish_count + summary.neutral_count >= 2


def test_ticker_sentiment_no_data(db: Session):
    summary = ticker_sentiment(db, "ZZZZ_FAKE")
    assert summary.bullish_count == 0
    assert summary.bearish_count == 0


# ---------------------------------------------------------------------------
# Importance feed
# ---------------------------------------------------------------------------

def test_importance_feed(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="CENTRAL_BANK", source="Fed", headline="Fed raises rates", importance_score=0.9))
    feed = importance_feed(db, limit=10, min_importance=0.7)
    for e in feed:
        assert float(e.importance_score) >= 0.7


def test_importance_feed_empty(db: Session):
    result = importance_feed(db, limit=5, min_importance=0.99)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

def test_build_clusters(db: Session):
    for i in range(3):
        ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline=f"News {i}", tickers=["AAPL"]))
    for i in range(3):
        ingest_event(db, AlternativeDataEventIngest(event_type="SEC_FILING", source="SEC", headline=f"Filing {i}", tickers=["MSFT"]))
    clusters = build_clusters(db)
    assert len(clusters) >= 1


def test_list_clusters_after_build(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="NEWS", source="T", headline="H1"))
    build_clusters(db)
    clusters = list_clusters(db)
    assert isinstance(clusters, list)


def test_cluster_fields(db: Session):
    ingest_event(db, AlternativeDataEventIngest(event_type="MACRO_EVENT", source="Fed", headline="Rate decision"))
    clusters = build_clusters(db)
    if clusters:
        c = clusters[0]
        assert c.cluster_label is not None
        assert c.event_count >= 1
