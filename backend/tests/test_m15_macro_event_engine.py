"""Tests for M15 MacroEventEngine."""
import pytest
from services.macro_event_engine import (
    MacroEvent,
    MacroEventEngine,
    MacroEventType,
    EventImportance,
    get_macro_event_engine,
)


def _make_macro(engine: MacroEventEngine, **overrides) -> MacroEvent:
    kwargs = dict(
        event_type=MacroEventType.CPI,
        country="US",
        timestamp=1700000000.0,
        importance=EventImportance.HIGH,
        description="CPI release",
        actual=3.2,
        forecast=3.1,
        previous=3.0,
        metadata={},
        event_id=None,
    )
    kwargs.update(overrides)
    return engine.add_event(**kwargs)


class TestMacroEventEngine:
    def setup_method(self):
        self.engine = MacroEventEngine()

    def test_add_returns_macro_event(self):
        ev = _make_macro(self.engine)
        assert isinstance(ev, MacroEvent)

    def test_add_assigns_id(self):
        ev = _make_macro(self.engine)
        assert ev.id and len(ev.id) > 0

    def test_custom_id(self):
        ev = _make_macro(self.engine, event_id="mac-001")
        assert ev.id == "mac-001"

    def test_surprise_computed(self):
        ev = _make_macro(self.engine, actual=3.2, forecast=3.1)
        assert abs(ev.surprise - 0.1) < 1e-9

    def test_surprise_pct_computed(self):
        ev = _make_macro(self.engine, actual=3.2, forecast=3.1)
        assert ev.surprise_pct is not None

    def test_surprise_pct_formula(self):
        ev = _make_macro(self.engine, actual=3.2, forecast=3.1)
        expected_pct = (3.2 - 3.1) / abs(3.1) * 100
        assert abs(ev.surprise_pct - expected_pct) < 1e-3

    def test_surprise_zero_forecast(self):
        ev = _make_macro(self.engine, actual=1.0, forecast=0.0)
        assert ev.surprise == 1.0
        assert ev.surprise_pct is not None

    def test_surprise_negative(self):
        ev = _make_macro(self.engine, actual=2.9, forecast=3.1)
        assert ev.surprise < 0

    def test_historical_percentile_optional(self):
        ev = _make_macro(self.engine)
        if ev.historical_percentile is not None:
            assert 0.0 <= ev.historical_percentile <= 1.0

    def test_volatility_expectation_set(self):
        ev = _make_macro(self.engine)
        assert ev.volatility_expectation is not None
        assert ev.volatility_expectation >= 0.0

    def test_stores_event_type(self):
        ev = _make_macro(self.engine, event_type=MacroEventType.NFP)
        assert ev.event_type == MacroEventType.NFP

    def test_stores_country(self):
        ev = _make_macro(self.engine, country="GB")
        assert ev.country == "GB"

    def test_stores_importance(self):
        ev = _make_macro(self.engine, importance=EventImportance.CRITICAL)
        assert ev.importance == EventImportance.CRITICAL

    def test_all_events_empty(self):
        assert self.engine.all_events() == []

    def test_all_events_returns_added(self):
        _make_macro(self.engine)
        _make_macro(self.engine, country="EU")
        assert len(self.engine.all_events()) == 2

    def test_filter_by_event_type(self):
        _make_macro(self.engine, event_type=MacroEventType.CPI)
        _make_macro(self.engine, event_type=MacroEventType.NFP)
        res = self.engine.filter(event_type=MacroEventType.CPI)
        assert len(res) == 1

    def test_filter_by_country(self):
        _make_macro(self.engine, country="US")
        _make_macro(self.engine, country="EU")
        res = self.engine.filter(country="EU")
        assert len(res) == 1

    def test_filter_by_importance(self):
        _make_macro(self.engine, importance=EventImportance.HIGH)
        _make_macro(self.engine, importance=EventImportance.LOW)
        res = self.engine.filter(importance=EventImportance.LOW)
        assert len(res) == 1

    def test_filter_by_since(self):
        _make_macro(self.engine, timestamp=1000.0)
        _make_macro(self.engine, timestamp=3000.0)
        res = self.engine.filter(since=2000.0)
        assert len(res) == 1
        assert res[0].timestamp == 3000.0

    def test_filter_by_until(self):
        _make_macro(self.engine, timestamp=1000.0)
        _make_macro(self.engine, timestamp=3000.0)
        res = self.engine.filter(until=2000.0)
        assert len(res) == 1

    def test_filter_surprise_positive(self):
        _make_macro(self.engine, actual=3.5, forecast=3.0)
        _make_macro(self.engine, actual=2.8, forecast=3.0)
        res = self.engine.filter(surprise_positive=True)
        assert len(res) == 1
        assert res[0].surprise > 0

    def test_filter_surprise_negative(self):
        _make_macro(self.engine, actual=3.5, forecast=3.0)
        _make_macro(self.engine, actual=2.8, forecast=3.0)
        res = self.engine.filter(surprise_positive=False)
        assert len(res) == 1
        assert res[0].surprise < 0

    def test_filter_no_args_returns_all(self):
        _make_macro(self.engine)
        _make_macro(self.engine)
        res = self.engine.filter()
        assert len(res) == 2

    def test_statistics_structure(self):
        _make_macro(self.engine)
        stats = self.engine.statistics()
        assert "total" in stats
        assert "by_type" in stats
        assert "by_country" in stats

    def test_statistics_total(self):
        _make_macro(self.engine)
        _make_macro(self.engine)
        stats = self.engine.statistics()
        assert stats["total"] == 2

    def test_all_19_macro_types(self):
        types = list(MacroEventType)
        assert len(types) == 19

    def test_fomc_type_exists(self):
        assert MacroEventType.FOMC in MacroEventType

    def test_gdp_type_exists(self):
        assert MacroEventType.GDP in MacroEventType

    def test_singleton(self):
        a = get_macro_event_engine()
        b = get_macro_event_engine()
        assert a is b

    def test_get_by_id_found(self):
        ev = _make_macro(self.engine)
        assert self.engine.get_by_id(ev.id) is not None

    def test_get_by_id_not_found(self):
        assert self.engine.get_by_id("missing") is None

    def test_metadata_stored(self):
        ev = _make_macro(self.engine, metadata={"source": "bloomberg"})
        assert ev.metadata["source"] == "bloomberg"

    def test_previous_stored(self):
        ev = _make_macro(self.engine, previous=2.9)
        assert ev.previous == 2.9
