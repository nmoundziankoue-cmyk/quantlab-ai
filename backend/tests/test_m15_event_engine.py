"""Tests for M15 CorporateEventEngine."""
import time
import pytest
from services.event_engine import (
    CorporateEvent,
    CorporateEventEngine,
    CorporateEventType,
    EventImportance,
    EventSeverity,
    get_corporate_event_engine,
)


def _make_event(engine: CorporateEventEngine, **overrides) -> CorporateEvent:
    kwargs = dict(
        ticker="AAPL",
        company="Apple Inc.",
        event_type=CorporateEventType.EARNINGS,
        description="Q4 earnings beat",
        sector="technology",
        industry="consumer electronics",
        country="US",
        confidence=0.9,
        source="sec_filing",
        timestamp=1700000000.0,
        importance=EventImportance.HIGH,
        severity=EventSeverity.MEDIUM,
        metadata={},
        tags=["earnings"],
        event_id=None,
    )
    kwargs.update(overrides)
    return engine.add_event(**kwargs)


class TestCorporateEventEngine:
    def setup_method(self):
        self.engine = CorporateEventEngine()

    def test_add_event_returns_corporate_event(self):
        ev = _make_event(self.engine)
        assert isinstance(ev, CorporateEvent)

    def test_add_event_assigns_id(self):
        ev = _make_event(self.engine)
        assert ev.id and len(ev.id) > 0

    def test_add_event_custom_id(self):
        ev = _make_event(self.engine, event_id="custom-001")
        assert ev.id == "custom-001"

    def test_add_event_stores_ticker(self):
        ev = _make_event(self.engine, ticker="MSFT")
        assert ev.ticker == "MSFT"

    def test_add_event_stores_type(self):
        ev = _make_event(self.engine, event_type=CorporateEventType.MERGER)
        assert ev.event_type == CorporateEventType.MERGER

    def test_add_event_stores_importance(self):
        ev = _make_event(self.engine, importance=EventImportance.CRITICAL)
        assert ev.importance == EventImportance.CRITICAL

    def test_add_event_stores_severity(self):
        ev = _make_event(self.engine, severity=EventSeverity.EXTREME)
        assert ev.severity == EventSeverity.EXTREME

    def test_add_event_stores_confidence(self):
        ev = _make_event(self.engine, confidence=0.75)
        assert ev.confidence == 0.75

    def test_add_event_stores_sector(self):
        ev = _make_event(self.engine, sector="healthcare")
        assert ev.sector == "healthcare"

    def test_add_event_stores_tags(self):
        ev = _make_event(self.engine, tags=["alpha", "beta"])
        assert "alpha" in ev.tags

    def test_get_by_id_found(self):
        ev = _make_event(self.engine)
        found = self.engine.get_by_id(ev.id)
        assert found is not None
        assert found.id == ev.id

    def test_get_by_id_not_found(self):
        assert self.engine.get_by_id("nonexistent") is None

    def test_all_events_empty_initially(self):
        assert self.engine.all_events() == []

    def test_all_events_returns_list(self):
        _make_event(self.engine)
        _make_event(self.engine, ticker="GOOG")
        evs = self.engine.all_events()
        assert len(evs) == 2

    def test_filter_by_ticker(self):
        _make_event(self.engine, ticker="AAPL")
        _make_event(self.engine, ticker="MSFT")
        res = self.engine.filter(ticker="AAPL")
        assert all(e.ticker == "AAPL" for e in res)
        assert len(res) == 1

    def test_filter_by_sector(self):
        _make_event(self.engine, sector="technology")
        _make_event(self.engine, sector="healthcare")
        res = self.engine.filter(sector="healthcare")
        assert len(res) == 1
        assert res[0].sector == "healthcare"

    def test_filter_by_country(self):
        _make_event(self.engine, country="US")
        _make_event(self.engine, country="GB")
        res = self.engine.filter(country="GB")
        assert len(res) == 1

    def test_filter_by_event_type(self):
        _make_event(self.engine, event_type=CorporateEventType.EARNINGS)
        _make_event(self.engine, event_type=CorporateEventType.DIVIDEND)
        res = self.engine.filter(event_type=CorporateEventType.DIVIDEND)
        assert len(res) == 1

    def test_filter_by_importance(self):
        _make_event(self.engine, importance=EventImportance.HIGH)
        _make_event(self.engine, importance=EventImportance.LOW)
        res = self.engine.filter(importance=EventImportance.LOW)
        assert len(res) == 1

    def test_filter_by_since(self):
        _make_event(self.engine, timestamp=1000.0)
        _make_event(self.engine, timestamp=2000.0)
        res = self.engine.filter(since=1500.0)
        assert len(res) == 1
        assert res[0].timestamp == 2000.0

    def test_filter_by_until(self):
        _make_event(self.engine, timestamp=1000.0)
        _make_event(self.engine, timestamp=2000.0)
        res = self.engine.filter(until=1500.0)
        assert len(res) == 1
        assert res[0].timestamp == 1000.0

    def test_filter_by_tag(self):
        _make_event(self.engine, tags=["earnings", "beat"])
        _make_event(self.engine, tags=["dividend"])
        res = self.engine.filter(tags=["earnings"])
        assert len(res) == 1

    def test_filter_no_conditions_returns_all(self):
        _make_event(self.engine)
        _make_event(self.engine)
        res = self.engine.filter()
        assert len(res) == 2

    def test_statistics_structure(self):
        _make_event(self.engine)
        stats = self.engine.statistics()
        assert "total" in stats
        assert "by_type" in stats
        assert "by_importance" in stats
        assert "by_severity" in stats

    def test_statistics_total(self):
        _make_event(self.engine)
        _make_event(self.engine)
        stats = self.engine.statistics()
        assert stats["total"] == 2

    def test_statistics_by_type(self):
        _make_event(self.engine, event_type=CorporateEventType.EARNINGS)
        _make_event(self.engine, event_type=CorporateEventType.EARNINGS)
        stats = self.engine.statistics()
        assert stats["by_type"]["earnings"] == 2

    def test_statistics_by_importance(self):
        _make_event(self.engine, importance=EventImportance.HIGH)
        stats = self.engine.statistics()
        assert stats["by_importance"]["high"] >= 1

    def test_all_28_event_types_exist(self):
        types = list(CorporateEventType)
        assert len(types) == 28

    def test_event_types_include_bankruptcy(self):
        assert CorporateEventType.BANKRUPTCY in CorporateEventType

    def test_event_types_include_fda_approval(self):
        assert CorporateEventType.FDA_APPROVAL in CorporateEventType

    def test_event_importance_levels(self):
        levels = list(EventImportance)
        assert EventImportance.CRITICAL in levels
        assert EventImportance.LOW in levels

    def test_event_severity_levels(self):
        levels = list(EventSeverity)
        assert EventSeverity.EXTREME in levels
        assert EventSeverity.MINIMAL in levels

    def test_singleton_same_instance(self):
        a = get_corporate_event_engine()
        b = get_corporate_event_engine()
        assert a is b

    def test_multiple_filters_combined(self):
        _make_event(self.engine, ticker="AAPL", sector="technology", importance=EventImportance.HIGH)
        _make_event(self.engine, ticker="AAPL", sector="technology", importance=EventImportance.LOW)
        _make_event(self.engine, ticker="MSFT", sector="technology", importance=EventImportance.HIGH)
        res = self.engine.filter(ticker="AAPL", importance=EventImportance.HIGH)
        assert len(res) == 1

    def test_event_metadata_stored(self):
        ev = _make_event(self.engine, metadata={"key": "value"})
        assert ev.metadata["key"] == "value"

    def test_event_description_stored(self):
        ev = _make_event(self.engine, description="Test description")
        assert ev.description == "Test description"

    def test_event_country_stored(self):
        ev = _make_event(self.engine, country="DE")
        assert ev.country == "DE"

    def test_engine_independent_instances(self):
        e1 = CorporateEventEngine()
        e2 = CorporateEventEngine()
        _make_event(e1)
        assert e2.all_events() == []

    def test_statistics_empty_engine(self):
        stats = self.engine.statistics()
        assert stats["total"] == 0
