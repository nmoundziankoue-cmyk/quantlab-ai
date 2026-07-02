"""Tests for M15 EventSearchEngine."""
import pytest
from services.event_engine import CorporateEventEngine, CorporateEventType, EventImportance, EventSeverity
from services.macro_event_engine import MacroEventEngine, MacroEventType
from services.event_search import EventSearchEngine, EventSearchHit, EventSearchQuery


def _corp_events():
    engine = CorporateEventEngine()
    for i, (ticker, etype, desc, sector) in enumerate([
        ("AAPL", CorporateEventType.EARNINGS, "Apple quarterly earnings beat expectations significantly", "technology"),
        ("MSFT", CorporateEventType.PRODUCT_LAUNCH, "Microsoft Azure cloud platform expansion announced", "technology"),
        ("JNJ", CorporateEventType.FDA_APPROVAL, "Johnson Johnson FDA drug approval for oncology treatment", "healthcare"),
        ("XOM", CorporateEventType.PARTNERSHIP, "ExxonMobil energy partnership for renewable projects", "energy"),
        ("GS", CorporateEventType.SEC_FILING, "Goldman Sachs annual SEC report regulatory filing", "financials"),
    ]):
        engine.add_event(
            ticker=ticker, company=f"Company {i}", event_type=etype, description=desc,
            sector=sector, industry="general", country="US", confidence=0.9, source="test",
            timestamp=1700000000.0 + i * 86400, importance=EventImportance.HIGH,
            severity=EventSeverity.MEDIUM, metadata={}, tags=[], event_id=f"corp-{i:03d}",
        )
    return engine.all_events()


def _macro_events():
    engine = MacroEventEngine()
    for i, (etype, country, desc) in enumerate([
        (MacroEventType.CPI, "US", "Consumer price index inflation monthly reading report"),
        (MacroEventType.FOMC, "US", "Federal reserve interest rate decision committee meeting"),
        (MacroEventType.GDP, "EU", "European Union GDP growth quarterly economic release"),
    ]):
        engine.add_event(
            event_type=etype, country=country, timestamp=1700000000.0 + i * 86400,
            importance=EventImportance.HIGH, description=desc,
            actual=3.2, forecast=3.1, previous=3.0, metadata={}, event_id=f"mac-{i:03d}",
        )
    return engine.all_events()


class TestEventSearchEngine:
    def setup_method(self):
        self.engine = EventSearchEngine()
        self.corp = _corp_events()
        self.macro = _macro_events()

    def test_search_returns_list(self):
        result = self.engine.search(EventSearchQuery(query="earnings"), self.corp, self.macro)
        assert isinstance(result, list)

    def test_search_hits_are_event_search_hit(self):
        result = self.engine.search(EventSearchQuery(query="earnings"), self.corp, self.macro)
        for h in result:
            assert isinstance(h, EventSearchHit)

    def test_search_earnings_finds_aapl(self):
        result = self.engine.search(EventSearchQuery(query="earnings"), self.corp, self.macro)
        ids = [h.event_id for h in result]
        assert "corp-000" in ids

    def test_search_cloud_finds_msft(self):
        result = self.engine.search(EventSearchQuery(query="cloud"), self.corp, self.macro)
        ids = [h.event_id for h in result]
        assert "corp-001" in ids

    def test_search_no_query_returns_all(self):
        result = self.engine.search(EventSearchQuery(query=None), self.corp, self.macro)
        assert len(result) == 8

    def test_search_kind_corporate_only(self):
        result = self.engine.search(EventSearchQuery(kind="corporate"), self.corp, self.macro)
        assert all(h.kind == "corporate" for h in result)
        assert len(result) == 5

    def test_search_kind_macro_only(self):
        result = self.engine.search(EventSearchQuery(kind="macro"), self.corp, self.macro)
        assert all(h.kind == "macro" for h in result)
        assert len(result) == 3

    def test_search_by_ticker_filter(self):
        result = self.engine.search(EventSearchQuery(tickers=["JNJ"]), self.corp, self.macro)
        corp_hits = [h for h in result if h.kind == "corporate"]
        assert len(corp_hits) == 1
        assert corp_hits[0].event_id == "corp-002"

    def test_search_by_sector_filter(self):
        result = self.engine.search(EventSearchQuery(sectors=["healthcare"]), self.corp, self.macro)
        corp_hits = [h for h in result if h.kind == "corporate"]
        assert all(h.event_data.get("sector") == "healthcare" for h in corp_hits)

    def test_search_by_country_filter(self):
        result = self.engine.search(EventSearchQuery(countries=["EU"]), self.corp, self.macro)
        macro_hits = [h for h in result if h.kind == "macro"]
        assert all(h.event_data.get("country") == "EU" for h in macro_hits)

    def test_search_limit_respected(self):
        result = self.engine.search(EventSearchQuery(limit=3), self.corp, self.macro)
        assert len(result) <= 3

    def test_search_hits_have_score(self):
        result = self.engine.search(EventSearchQuery(query="earnings"), self.corp, self.macro)
        for h in result:
            assert isinstance(h.score, float)
            assert h.score >= 0.0

    def test_search_hits_have_kind(self):
        result = self.engine.search(EventSearchQuery(query="earnings"), self.corp, self.macro)
        for h in result:
            assert h.kind in ("corporate", "macro")

    def test_search_hits_have_event_data(self):
        result = self.engine.search(EventSearchQuery(query="earnings"), self.corp, self.macro)
        for h in result:
            assert isinstance(h.event_data, dict)

    def test_search_results_ordered_by_score_desc(self):
        result = self.engine.search(EventSearchQuery(query="earnings"), self.corp, self.macro)
        scores = [h.score for h in result]
        assert scores == sorted(scores, reverse=True)

    def test_facets_returns_dict(self):
        facets = self.engine.facets(self.corp, self.macro)
        assert isinstance(facets, dict)

    def test_facets_has_sectors(self):
        facets = self.engine.facets(self.corp, self.macro)
        assert "sectors" in facets

    def test_facets_has_countries(self):
        facets = self.engine.facets(self.corp, self.macro)
        assert "countries" in facets

    def test_facets_has_event_types(self):
        facets = self.engine.facets(self.corp, self.macro)
        assert "event_types" in facets

    def test_autocomplete_returns_list(self):
        suggestions = self.engine.autocomplete("AAPL", self.corp)
        assert isinstance(suggestions, list)

    def test_autocomplete_prefix_match(self):
        suggestions = self.engine.autocomplete("MS", self.corp)
        assert any("MSFT" in s or "MS" in s for s in suggestions)

    def test_autocomplete_empty_prefix(self):
        suggestions = self.engine.autocomplete("", self.corp)
        assert isinstance(suggestions, list)

    def test_search_fomc_finds_macro(self):
        result = self.engine.search(EventSearchQuery(query="federal reserve interest rate"), self.corp, self.macro)
        macro_hits = [h for h in result if h.kind == "macro"]
        assert len(macro_hits) > 0

    def test_search_importance_filter(self):
        result = self.engine.search(EventSearchQuery(importance=["high"]), self.corp, self.macro)
        assert len(result) > 0

    def test_search_empty_corpus(self):
        result = self.engine.search(EventSearchQuery(query="anything"), [], [])
        assert result == []
