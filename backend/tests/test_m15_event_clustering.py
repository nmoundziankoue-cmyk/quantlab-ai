"""Tests for M15 EventClusteringEngine."""
import pytest
from services.event_engine import (
    CorporateEvent,
    CorporateEventType,
    EventImportance,
    EventSeverity,
)
from services.macro_event_engine import MacroEvent, MacroEventType
from services.event_clustering import (
    ClusterResult,
    EventCluster,
    EventClusteringEngine,
)


def _corp(
    description: str = "AI chip launch for data centers",
    sector: str = "technology",
    event_type: CorporateEventType = CorporateEventType.PRODUCT_LAUNCH,
    tags: list | None = None,
) -> CorporateEvent:
    return CorporateEvent(
        id="evt-001",
        ticker="NVDA",
        company="Nvidia Corp.",
        sector=sector,
        industry="semiconductors",
        country="US",
        timestamp=1700000000.0,
        event_type=event_type,
        importance=EventImportance.HIGH,
        severity=EventSeverity.MEDIUM,
        confidence=0.9,
        source="press_release",
        description=description,
        metadata={},
        tags=tags or [],
    )


def _macro(event_type: MacroEventType = MacroEventType.FOMC) -> MacroEvent:
    return MacroEvent(
        id="mac-001",
        event_type=event_type,
        country="US",
        timestamp=1700000000.0,
        importance=EventImportance.HIGH,
        description="Federal Reserve rate decision",
        actual=5.5,
        forecast=5.5,
        previous=5.25,
        surprise=0.0,
        surprise_pct=0.0,
        historical_percentile=0.6,
        volatility_expectation=0.5,
        metadata={},
    )


class TestEventClusteringEngine:
    def setup_method(self):
        self.engine = EventClusteringEngine()

    def test_classify_returns_cluster_result(self):
        ev = _corp()
        result = self.engine.classify(ev)
        assert isinstance(result, ClusterResult)

    def test_classify_event_id_stored(self):
        ev = _corp()
        result = self.engine.classify(ev)
        assert result.event_id == "evt-001"

    def test_classify_cluster_is_enum(self):
        ev = _corp()
        result = self.engine.classify(ev)
        assert isinstance(result.cluster, EventCluster)

    def test_classify_ai_description(self):
        ev = _corp(description="artificial intelligence and machine learning platform")
        result = self.engine.classify(ev)
        assert result.cluster in (EventCluster.ARTIFICIAL_INTELLIGENCE, EventCluster.CLOUD, EventCluster.ENTERPRISE_SOFTWARE)

    def test_classify_semiconductor_description(self):
        ev = _corp(description="chip fabrication semiconductor process node")
        result = self.engine.classify(ev)
        assert result.cluster in (EventCluster.SEMICONDUCTORS, EventCluster.GENERAL)

    def test_classify_ev_description(self):
        ev = _corp(description="electric vehicle battery range improvement")
        result = self.engine.classify(ev)
        assert result.cluster in (EventCluster.EV, EventCluster.ENERGY, EventCluster.GENERAL)

    def test_classify_cybersecurity_description(self):
        ev = _corp(description="cybersecurity breach data protection threat")
        result = self.engine.classify(ev)
        assert result.cluster in (EventCluster.CYBERSECURITY, EventCluster.GENERAL)

    def test_classify_healthcare_keyword(self):
        ev = _corp(description="pharmaceutical drug clinical trial phase three", sector="healthcare")
        result = self.engine.classify(ev)
        assert result.cluster in (EventCluster.HEALTHCARE, EventCluster.GENERAL)

    def test_classify_energy_keyword(self):
        ev = _corp(description="wind solar renewable power generation capacity", sector="energy")
        result = self.engine.classify(ev)
        assert result.cluster in (EventCluster.ENERGY, EventCluster.OIL, EventCluster.GENERAL)

    def test_classify_macro_fomc(self):
        ev = _macro(MacroEventType.FOMC)
        result = self.engine.classify_macro(ev)
        assert isinstance(result, ClusterResult)

    def test_classify_macro_cpi(self):
        ev = _macro(MacroEventType.CPI)
        result = self.engine.classify_macro(ev)
        assert isinstance(result, ClusterResult)

    def test_cluster_batch_returns_list(self):
        evs = [_corp(), _corp(description="cloud computing platform")]
        results = self.engine.cluster_batch(evs)
        assert len(results) == 2
        assert all(isinstance(r, ClusterResult) for r in results)

    def test_cluster_batch_empty(self):
        assert self.engine.cluster_batch([]) == []

    def test_cluster_distribution_returns_dict(self):
        evs = [_corp(), _corp(description="cloud storage service")]
        dist = self.engine.cluster_distribution(evs)
        assert isinstance(dist, dict)
        assert sum(dist.values()) == 2

    def test_events_by_cluster_returns_dict(self):
        evs = [_corp(), _corp(description="cloud storage service")]
        by_cluster = self.engine.events_by_cluster(evs)
        assert isinstance(by_cluster, dict)

    def test_events_by_cluster_values_are_lists(self):
        evs = [_corp()]
        by_cluster = self.engine.events_by_cluster(evs)
        for v in by_cluster.values():
            assert isinstance(v, list)

    def test_event_cluster_enum_has_values(self):
        assert len(list(EventCluster)) >= 15

    def test_event_cluster_has_defense(self):
        assert EventCluster.DEFENSE in EventCluster

    def test_event_cluster_has_space(self):
        assert EventCluster.SPACE in EventCluster

    def test_cluster_result_confidence_in_range(self):
        ev = _corp()
        result = self.engine.classify(ev)
        assert 0.0 <= result.confidence <= 1.0

    def test_cluster_result_keywords_is_list(self):
        ev = _corp()
        result = self.engine.classify(ev)
        assert isinstance(result.matched_keywords, list)

    def test_classify_all_event_types_no_error(self):
        for etype in CorporateEventType:
            ev = _corp(event_type=etype)
            result = self.engine.classify(ev)
            assert isinstance(result, ClusterResult)

    def test_classify_all_macro_types_no_error(self):
        for etype in MacroEventType:
            ev = _macro(event_type=etype)
            result = self.engine.classify_macro(ev)
            assert isinstance(result, ClusterResult)
