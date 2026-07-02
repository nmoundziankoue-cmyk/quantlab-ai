"""Tests for M15 MarketIntelligenceScorer."""
import pytest
from services.event_engine import (
    CorporateEvent,
    CorporateEventType,
    EventImportance,
    EventSeverity,
)
from services.macro_event_engine import MacroEvent, MacroEventType
from services.market_intelligence_score import MarketIntelligenceScore, MarketIntelligenceScorer


def _corp(
    importance: EventImportance = EventImportance.HIGH,
    severity: EventSeverity = EventSeverity.MEDIUM,
    confidence: float = 0.9,
    event_type: CorporateEventType = CorporateEventType.EARNINGS,
) -> CorporateEvent:
    return CorporateEvent(
        id="evt-001",
        ticker="AAPL",
        company="Apple Inc.",
        sector="technology",
        industry="consumer electronics",
        country="US",
        timestamp=1700000000.0,
        event_type=event_type,
        importance=importance,
        severity=severity,
        confidence=confidence,
        source="sec",
        description="Earnings beat",
        metadata={},
        tags=["earnings"],
    )


def _macro(
    importance: EventImportance = EventImportance.HIGH,
    actual: float = 3.2,
    forecast: float = 3.1,
) -> MacroEvent:
    return MacroEvent(
        id="mac-001",
        event_type=MacroEventType.CPI,
        country="US",
        timestamp=1700000000.0,
        importance=importance,
        description="CPI report",
        actual=actual,
        forecast=forecast,
        previous=3.0,
        surprise=actual - forecast,
        surprise_pct=(actual - forecast) / abs(forecast) * 100 if forecast else 0.0,
        historical_percentile=0.7,
        volatility_expectation=0.5,
        metadata={},
    )


class TestMarketIntelligenceScorer:
    def setup_method(self):
        self.scorer = MarketIntelligenceScorer()

    def test_score_corporate_returns_score(self):
        result = self.scorer.score_corporate(_corp())
        assert isinstance(result, MarketIntelligenceScore)

    def test_corporate_overall_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.overall_score <= 1.0

    def test_corporate_positive_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.positive_score <= 1.0

    def test_corporate_negative_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.negative_score <= 1.0

    def test_corporate_confidence_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.confidence_score <= 1.0

    def test_corporate_importance_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.importance_score <= 1.0

    def test_corporate_novelty_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.novelty_score <= 1.0

    def test_corporate_expected_volatility_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.expected_volatility <= 1.0

    def test_corporate_expected_liquidity_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.expected_liquidity <= 1.0

    def test_corporate_institutional_interest_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.institutional_interest <= 1.0

    def test_corporate_portfolio_relevance_in_range(self):
        result = self.scorer.score_corporate(_corp())
        assert 0.0 <= result.portfolio_relevance <= 1.0

    def test_corporate_critical_higher_overall_than_low(self):
        crit = self.scorer.score_corporate(_corp(importance=EventImportance.CRITICAL))
        low = self.scorer.score_corporate(_corp(importance=EventImportance.LOW))
        assert crit.overall_score >= low.overall_score

    def test_corporate_high_confidence_higher_than_low_confidence(self):
        high_conf = self.scorer.score_corporate(_corp(confidence=0.95))
        low_conf = self.scorer.score_corporate(_corp(confidence=0.1))
        assert high_conf.confidence_score >= low_conf.confidence_score

    def test_corporate_extreme_severity_higher_volatility(self):
        ext = self.scorer.score_corporate(_corp(severity=EventSeverity.EXTREME))
        min_ = self.scorer.score_corporate(_corp(severity=EventSeverity.MINIMAL))
        assert ext.expected_volatility >= min_.expected_volatility

    def test_score_macro_returns_score(self):
        result = self.scorer.score_macro(_macro())
        assert isinstance(result, MarketIntelligenceScore)

    def test_macro_all_dimensions_in_range(self):
        result = self.scorer.score_macro(_macro())
        for attr in [
            "positive_score", "negative_score", "confidence_score", "importance_score",
            "novelty_score", "expected_volatility", "expected_liquidity",
            "institutional_interest", "portfolio_relevance", "overall_score",
        ]:
            val = getattr(result, attr)
            assert 0.0 <= val <= 1.0, f"{attr} out of range: {val}"

    def test_macro_positive_surprise_higher_positive_score(self):
        pos = self.scorer.score_macro(_macro(actual=3.5, forecast=3.0))
        neg = self.scorer.score_macro(_macro(actual=2.5, forecast=3.0))
        assert pos.positive_score >= neg.positive_score

    def test_score_batch_corporate(self):
        evs = [_corp(), _corp(importance=EventImportance.LOW)]
        results = self.scorer.score_batch(evs)
        assert len(results) == 2
        assert all(isinstance(r, MarketIntelligenceScore) for r in results)

    def test_score_batch_corporate_with_catalysts(self):
        evs = [_corp(), _corp(importance=EventImportance.CRITICAL)]
        results = self.scorer.score_batch(evs, catalysts=None)
        assert len(results) == 2

    def test_score_batch_empty_returns_empty(self):
        assert self.scorer.score_batch([]) == []

    def test_score_corporate_all_event_types_no_error(self):
        for etype in CorporateEventType:
            ev = _corp(event_type=etype)
            result = self.scorer.score_corporate(ev)
            assert isinstance(result, MarketIntelligenceScore)

    def test_score_macro_all_event_types_no_error(self):
        for etype in MacroEventType:
            m = MacroEvent(
                id="x", event_type=etype, country="US", timestamp=1700000000.0,
                importance=EventImportance.MEDIUM, description="test",
                actual=1.0, forecast=1.0, previous=1.0,
                surprise=0.0, surprise_pct=0.0,
                historical_percentile=0.5, volatility_expectation=0.4,
                metadata={},
            )
            result = self.scorer.score_macro(m)
            assert isinstance(result, MarketIntelligenceScore)

    def test_score_is_deterministic(self):
        ev = _corp()
        a = self.scorer.score_corporate(ev)
        b = self.scorer.score_corporate(ev)
        assert a.overall_score == b.overall_score
