"""Tests for M15 MarketCatalystEngine."""
import pytest
from services.event_engine import (
    CorporateEvent,
    CorporateEventType,
    EventImportance,
    EventSeverity,
)
from services.market_catalyst import (
    CatalystDirection,
    CatalystScore,
    CatalystTheme,
    MarketCatalystEngine,
)


def _make_corp_event(
    event_type: CorporateEventType = CorporateEventType.EARNINGS,
    importance: EventImportance = EventImportance.HIGH,
    severity: EventSeverity = EventSeverity.MEDIUM,
    ticker: str = "AAPL",
    sector: str = "technology",
    description: str = "Quarterly earnings beat",
    confidence: float = 0.9,
    tags: list | None = None,
) -> CorporateEvent:
    return CorporateEvent(
        id="evt-001",
        ticker=ticker,
        company="Apple Inc.",
        sector=sector,
        industry="consumer electronics",
        country="US",
        timestamp=1700000000.0,
        event_type=event_type,
        importance=importance,
        severity=severity,
        confidence=confidence,
        source="sec",
        description=description,
        metadata={},
        tags=tags or [],
    )


class TestMarketCatalystEngine:
    def setup_method(self):
        self.engine = MarketCatalystEngine()

    def test_classify_returns_catalyst_score(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert isinstance(score, CatalystScore)

    def test_classify_event_id_stored(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert score.event_id == "evt-001"

    def test_classify_ticker_stored(self):
        ev = _make_corp_event(ticker="TSLA")
        score = self.engine.classify(ev)
        assert score.ticker == "TSLA"

    def test_classify_direction_is_enum(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert isinstance(score.direction, CatalystDirection)

    def test_classify_theme_is_enum(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert isinstance(score.theme, CatalystTheme)

    def test_classify_composite_score_in_range(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert 0.0 <= score.composite_score <= 1.0

    def test_classify_earnings_bullish(self):
        ev = _make_corp_event(event_type=CorporateEventType.EARNINGS, importance=EventImportance.HIGH)
        score = self.engine.classify(ev)
        assert score.direction == CatalystDirection.BULLISH

    def test_classify_dividend_cut_bearish(self):
        ev = _make_corp_event(event_type=CorporateEventType.DIVIDEND_CUT)
        score = self.engine.classify(ev)
        assert score.direction == CatalystDirection.BEARISH

    def test_classify_bankruptcy_bearish(self):
        ev = _make_corp_event(event_type=CorporateEventType.BANKRUPTCY)
        score = self.engine.classify(ev)
        assert score.direction == CatalystDirection.BEARISH

    def test_classify_dividend_increase_bullish(self):
        ev = _make_corp_event(event_type=CorporateEventType.DIVIDEND_INCREASE)
        score = self.engine.classify(ev)
        assert score.direction == CatalystDirection.BULLISH

    def test_classify_credit_upgrade_bullish(self):
        ev = _make_corp_event(event_type=CorporateEventType.CREDIT_UPGRADE)
        score = self.engine.classify(ev)
        assert score.direction == CatalystDirection.BULLISH

    def test_classify_credit_downgrade_bearish(self):
        ev = _make_corp_event(event_type=CorporateEventType.CREDIT_DOWNGRADE)
        score = self.engine.classify(ev)
        assert score.direction == CatalystDirection.BEARISH

    def test_classify_raw_score_float(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert isinstance(score.raw_score, float)

    def test_classify_importance_score_in_range(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert 0.0 <= score.importance_score <= 1.0

    def test_classify_severity_score_in_range(self):
        ev = _make_corp_event()
        score = self.engine.classify(ev)
        assert 0.0 <= score.severity_score <= 1.0

    def test_classify_confidence_score_in_range(self):
        ev = _make_corp_event(confidence=0.8)
        score = self.engine.classify(ev)
        assert 0.0 <= score.confidence_score <= 1.0

    def test_classify_critical_higher_than_low(self):
        high_ev = _make_corp_event(importance=EventImportance.CRITICAL)
        low_ev = _make_corp_event(importance=EventImportance.LOW)
        high_score = self.engine.classify(high_ev)
        low_score = self.engine.classify(low_ev)
        assert high_score.importance_score > low_score.importance_score

    def test_classify_technology_theme(self):
        ev = _make_corp_event(sector="technology")
        score = self.engine.classify(ev)
        assert score.theme in (CatalystTheme.TECHNOLOGY, CatalystTheme.AI, CatalystTheme.EARNINGS)

    def test_classify_healthcare_theme(self):
        ev = _make_corp_event(sector="healthcare", event_type=CorporateEventType.FDA_APPROVAL)
        score = self.engine.classify(ev)
        assert score.theme == CatalystTheme.HEALTHCARE

    def test_classify_batch_returns_list(self):
        evs = [_make_corp_event(), _make_corp_event(event_type=CorporateEventType.DIVIDEND)]
        scores = self.engine.classify_batch(evs)
        assert len(scores) == 2
        assert all(isinstance(s, CatalystScore) for s in scores)

    def test_classify_batch_empty(self):
        assert self.engine.classify_batch([]) == []

    def test_top_catalysts_returns_n(self):
        evs = [_make_corp_event(event_type=CorporateEventType.EARNINGS, importance=EventImportance.CRITICAL)] * 5
        scores = self.engine.top_catalysts(evs, n=3)
        assert len(scores) <= 3

    def test_top_catalysts_direction_filter(self):
        evs = [
            _make_corp_event(event_type=CorporateEventType.EARNINGS),
            _make_corp_event(event_type=CorporateEventType.DIVIDEND_CUT),
        ]
        bullish = self.engine.top_catalysts(evs, direction=CatalystDirection.BULLISH)
        assert all(s.direction == CatalystDirection.BULLISH for s in bullish)

    def test_theme_distribution_returns_dict(self):
        evs = [_make_corp_event(), _make_corp_event(sector="healthcare", event_type=CorporateEventType.FDA_APPROVAL)]
        dist = self.engine.theme_distribution(evs)
        assert isinstance(dist, dict)

    def test_direction_distribution_returns_dict(self):
        evs = [_make_corp_event(), _make_corp_event(event_type=CorporateEventType.DIVIDEND_CUT)]
        dist = self.engine.direction_distribution(evs)
        assert isinstance(dist, dict)
        assert sum(dist.values()) == 2

    def test_catalyst_direction_values(self):
        assert CatalystDirection.BULLISH in CatalystDirection
        assert CatalystDirection.BEARISH in CatalystDirection
        assert CatalystDirection.NEUTRAL in CatalystDirection

    def test_catalyst_theme_has_macro(self):
        assert CatalystTheme.MACRO in CatalystTheme

    def test_catalyst_theme_has_earnings(self):
        assert CatalystTheme.EARNINGS in CatalystTheme

    def test_tags_stored_in_score(self):
        ev = _make_corp_event(tags=["beat", "guidance"])
        score = self.engine.classify(ev)
        assert isinstance(score.tags, list)
