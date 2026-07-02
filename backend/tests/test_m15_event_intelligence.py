"""Tests for M15 EventIntelligenceEngine."""
import pytest
from services.event_engine import (
    CorporateEvent,
    CorporateEventType,
    EventImportance,
    EventSeverity,
)
from services.macro_event_engine import MacroEvent, MacroEventType
from services.event_intelligence import (
    EventIntelligence,
    EventIntelligenceEngine,
    MacroEventIntelligence,
)


def _corp_event(event_type=CorporateEventType.EARNINGS) -> CorporateEvent:
    return CorporateEvent(
        id="evt-001",
        ticker="AAPL",
        company="Apple Inc.",
        sector="technology",
        industry="consumer electronics",
        country="US",
        timestamp=1700000000.0,
        event_type=event_type,
        importance=EventImportance.HIGH,
        severity=EventSeverity.MEDIUM,
        confidence=0.9,
        source="sec",
        description="Quarterly earnings announcement",
        metadata={},
        tags=["earnings"],
    )


def _macro_event(event_type=MacroEventType.CPI) -> MacroEvent:
    return MacroEvent(
        id="mac-001",
        event_type=event_type,
        country="US",
        timestamp=1700000000.0,
        importance=EventImportance.HIGH,
        description="CPI rose 0.3% MoM",
        actual=3.2,
        forecast=3.1,
        previous=3.0,
        surprise=0.1,
        surprise_pct=3.23,
        historical_percentile=0.7,
        volatility_expectation=0.5,
        metadata={},
    )


class TestEventIntelligenceEngine:
    def setup_method(self):
        self.engine = EventIntelligenceEngine()

    def test_analyse_corporate_returns_event_intelligence(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert isinstance(result, EventIntelligence)

    def test_corporate_event_id_stored(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.event_id == "evt-001"

    def test_corporate_ticker_stored(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.ticker == "AAPL"

    def test_corporate_executive_summary_nonempty(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.executive_summary and len(result.executive_summary) > 0

    def test_corporate_bull_case_nonempty(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.bull_case and len(result.bull_case) > 0

    def test_corporate_bear_case_nonempty(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.bear_case and len(result.bear_case) > 0

    def test_corporate_neutral_view_nonempty(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.neutral_view and len(result.neutral_view) > 0

    def test_corporate_key_risks_is_list(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert isinstance(result.key_risks, list)

    def test_corporate_key_opportunities_is_list(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert isinstance(result.key_opportunities, list)

    def test_corporate_historical_analogues_is_list(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert isinstance(result.historical_analogues, list)

    def test_corporate_portfolio_implications_nonempty(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.portfolio_implications

    def test_corporate_sector_implications_nonempty(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.sector_implications

    def test_corporate_macro_implications_nonempty(self):
        ev = _corp_event()
        result = self.engine.analyse_corporate(ev)
        assert result.macro_implications

    def test_corporate_all_28_types_no_error(self):
        for etype in CorporateEventType:
            ev = _corp_event(event_type=etype)
            result = self.engine.analyse_corporate(ev)
            assert isinstance(result, EventIntelligence)

    def test_analyse_macro_returns_macro_event_intelligence(self):
        ev = _macro_event()
        result = self.engine.analyse_macro(ev)
        assert isinstance(result, MacroEventIntelligence)

    def test_macro_event_id_stored(self):
        ev = _macro_event()
        result = self.engine.analyse_macro(ev)
        assert result.event_id == "mac-001"

    def test_macro_executive_summary_nonempty(self):
        ev = _macro_event()
        result = self.engine.analyse_macro(ev)
        assert result.executive_summary

    def test_macro_market_context_nonempty(self):
        ev = _macro_event()
        result = self.engine.analyse_macro(ev)
        assert result.market_context

    def test_macro_sector_implications_nonempty(self):
        ev = _macro_event()
        result = self.engine.analyse_macro(ev)
        assert result.sector_implications

    def test_macro_all_19_types_no_error(self):
        for etype in MacroEventType:
            ev = _macro_event(event_type=etype)
            result = self.engine.analyse_macro(ev)
            assert isinstance(result, MacroEventIntelligence)

    def test_macro_key_risks_is_list(self):
        ev = _macro_event()
        result = self.engine.analyse_macro(ev)
        assert isinstance(result.key_risks, list)

    def test_macro_portfolio_implications_nonempty(self):
        ev = _macro_event()
        result = self.engine.analyse_macro(ev)
        assert result.portfolio_implications

    def test_corporate_deterministic(self):
        ev = _corp_event()
        a = self.engine.analyse_corporate(ev)
        b = self.engine.analyse_corporate(ev)
        assert a.bull_case == b.bull_case
        assert a.bear_case == b.bear_case
