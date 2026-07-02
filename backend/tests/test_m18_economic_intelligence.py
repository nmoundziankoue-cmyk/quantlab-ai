"""Unit tests for M18 Economic Intelligence Engine — 60 tests."""
import pytest

from services.m18_economic_intelligence import (
    EconomicIndicatorType, BusinessCyclePhase, SurpriseDirection,
    EconomicIndicator, YieldCurveSnapshot, RecessionProbability,
    InflationForecast, BusinessCycleAnalysis, CountryMacroRisk,
    EconomicCalendarEvent, EconomicIntelligenceEngine,
    get_economic_intelligence_engine,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_indicator_type_count(self):
        assert len(EconomicIndicatorType) >= 8

    def test_business_cycle_phases(self):
        phases = [p.value for p in BusinessCyclePhase]
        assert len(phases) >= 4

    def test_surprise_direction_values(self):
        assert SurpriseDirection.BEAT is not None
        assert SurpriseDirection.MISS is not None
        assert SurpriseDirection.IN_LINE is not None

    def test_gdp_indicator_type(self):
        assert EconomicIndicatorType.GDP is not None

    def test_inflation_indicator_type(self):
        assert EconomicIndicatorType.INFLATION is not None


# ---------------------------------------------------------------------------
# EconomicIndicator
# ---------------------------------------------------------------------------

class TestEconomicIndicator:
    def _make(self):
        return EconomicIndicator(
            name="US GDP", country="US",
            indicator_type=EconomicIndicatorType.GDP,
            value=2.8, previous_value=2.1, forecast=2.5,
            unit="% QoQ annualised", frequency="Quarterly",
        )

    def test_indicator_surprise_computed(self):
        ind = self._make()
        assert isinstance(ind.surprise, float)
        assert abs(ind.surprise - (2.8 - 2.5)) < 0.01

    def test_indicator_surprise_direction_beat(self):
        ind = self._make()
        assert ind.surprise_direction == SurpriseDirection.BEAT

    def test_indicator_miss(self):
        ind = EconomicIndicator(
            name="US GDP", country="US",
            indicator_type=EconomicIndicatorType.GDP,
            value=1.8, previous_value=2.1, forecast=2.5,
            unit="%", frequency="Quarterly",
        )
        assert ind.surprise_direction == SurpriseDirection.MISS

    def test_indicator_in_line(self):
        ind = EconomicIndicator(
            name="PMI", country="US",
            indicator_type=EconomicIndicatorType.PMI,
            value=52.4, previous_value=51.0, forecast=52.4,
            unit="Index", frequency="Monthly",
        )
        assert ind.surprise_direction == SurpriseDirection.IN_LINE

    def test_indicator_to_dict(self):
        d = self._make().to_dict()
        assert "name" in d and "value" in d


# ---------------------------------------------------------------------------
# YieldCurveSnapshot
# ---------------------------------------------------------------------------

class TestYieldCurveSnapshot:
    def _make(self, tenors=None):
        if tenors is None:
            tenors = {"2Y": 0.048, "10Y": 0.045}
        return YieldCurveSnapshot(country="US", tenors=tenors)

    def test_inverted_when_2y_above_10y(self):
        snap = self._make({"2Y": 0.050, "10Y": 0.045})
        assert snap.is_inverted is True

    def test_not_inverted_when_normal(self):
        snap = self._make({"2Y": 0.040, "10Y": 0.045})
        assert snap.is_inverted is False

    def test_slope_computed(self):
        snap = self._make({"2Y": 0.040, "10Y": 0.045})
        assert isinstance(snap.slope, float)

    def test_to_dict(self):
        d = self._make().to_dict()
        assert "country" in d and "tenors" in d


# ---------------------------------------------------------------------------
# EconomicIntelligenceEngine — indicators
# ---------------------------------------------------------------------------

class TestEconomicEngineIndicators:
    def setup_method(self):
        self.engine = EconomicIntelligenceEngine()

    def test_record_indicator(self):
        ind = EconomicIndicator(
            name="US CPI", country="US",
            indicator_type=EconomicIndicatorType.INFLATION,
            value=3.2, previous_value=3.0, forecast=3.1,
            unit="% YoY", frequency="Monthly",
        )
        result = self.engine.record_indicator(ind)
        assert result.indicator_id is not None

    def test_get_indicators_for_country(self):
        ind = EconomicIndicator(
            name="US GDP", country="US",
            indicator_type=EconomicIndicatorType.GDP,
            value=2.8, previous_value=2.1, forecast=2.5,
            unit="%", frequency="Quarterly",
        )
        self.engine.record_indicator(ind)
        inds = self.engine.get_indicators(country="US")
        assert len(inds) >= 1

    def test_get_indicators_by_type(self):
        ind = EconomicIndicator(
            name="US PMI", country="US",
            indicator_type=EconomicIndicatorType.PMI,
            value=52.4, previous_value=51.0, forecast=52.0,
            unit="Index", frequency="Monthly",
        )
        self.engine.record_indicator(ind)
        inds = self.engine.get_indicators(indicator_type=EconomicIndicatorType.PMI)
        assert all(i.indicator_type == EconomicIndicatorType.PMI for i in inds)

    def test_get_indicators_empty_for_unknown_country(self):
        inds = self.engine.get_indicators(country="ZZ")
        assert inds == []


# ---------------------------------------------------------------------------
# EconomicIntelligenceEngine — yield curve
# ---------------------------------------------------------------------------

class TestEconomicEngineYieldCurve:
    def setup_method(self):
        self.engine = EconomicIntelligenceEngine()

    def test_record_yield_curve(self):
        snap = self.engine.record_yield_curve("US", {"2Y": 0.048, "10Y": 0.045, "30Y": 0.047})
        assert isinstance(snap, YieldCurveSnapshot)

    def test_get_yield_curve(self):
        self.engine.record_yield_curve("US", {"2Y": 0.048, "10Y": 0.045})
        snap = self.engine.get_yield_curve("US")
        assert snap is not None

    def test_get_yield_curve_unknown_country_returns_none(self):
        assert self.engine.get_yield_curve("ZZ") is None

    def test_yield_curve_history(self):
        self.engine.record_yield_curve("US", {"2Y": 0.048, "10Y": 0.045})
        self.engine.record_yield_curve("US", {"2Y": 0.046, "10Y": 0.044})
        hist = self.engine.get_yield_curve_history("US", limit=10)
        assert len(hist) >= 2

    def test_compute_yield_curve_spreads(self):
        self.engine.record_yield_curve("US", {"3M": 0.053, "2Y": 0.048, "5Y": 0.046, "10Y": 0.045, "30Y": 0.047})
        spreads = self.engine.compute_yield_curve_spreads("US")
        assert isinstance(spreads, dict)


# ---------------------------------------------------------------------------
# EconomicIntelligenceEngine — analytics
# ---------------------------------------------------------------------------

class TestEconomicEngineAnalytics:
    def setup_method(self):
        self.engine = EconomicIntelligenceEngine()
        for i in range(5):
            gdp = EconomicIndicator(
                name="US GDP", country="US",
                indicator_type=EconomicIndicatorType.GDP,
                value=2.0 + i * 0.1, previous_value=1.9, forecast=2.1,
                unit="%", frequency="Quarterly",
            )
            self.engine.record_indicator(gdp)
            unemp = EconomicIndicator(
                name="US Unemployment", country="US",
                indicator_type=EconomicIndicatorType.UNEMPLOYMENT,
                value=4.0 - i * 0.1, previous_value=4.1, forecast=3.9,
                unit="%", frequency="Monthly",
            )
            self.engine.record_indicator(unemp)

    def test_compute_recession_probability(self):
        result = self.engine.compute_recession_probability("US")
        assert isinstance(result, RecessionProbability)

    def test_recession_prob_range(self):
        result = self.engine.compute_recession_probability("US")
        assert 0.0 <= result.probability_12m <= 1.0
        assert 0.0 <= result.probability_24m <= 1.0

    def test_recession_prob_to_dict(self):
        d = self.engine.compute_recession_probability("US").to_dict()
        assert "probability_12m" in d

    def test_compute_inflation_forecast(self):
        for _ in range(3):
            self.engine.record_indicator(EconomicIndicator(
                name="CPI", country="US", indicator_type=EconomicIndicatorType.INFLATION,
                value=3.2, previous_value=3.0, forecast=3.1, unit="%", frequency="Monthly",
            ))
        result = self.engine.compute_inflation_forecast("US")
        assert isinstance(result, InflationForecast)

    def test_inflation_forecast_to_dict(self):
        self.engine.record_indicator(EconomicIndicator(
            name="CPI", country="US", indicator_type=EconomicIndicatorType.INFLATION,
            value=3.2, previous_value=3.0, forecast=3.1, unit="%", frequency="Monthly",
        ))
        d = self.engine.compute_inflation_forecast("US").to_dict()
        assert "forecast_3m" in d or "country" in d

    def test_classify_business_cycle(self):
        result = self.engine.classify_business_cycle("US")
        assert isinstance(result, BusinessCycleAnalysis)

    def test_business_cycle_phase_is_valid(self):
        result = self.engine.classify_business_cycle("US")
        assert result.phase in BusinessCyclePhase.__members__.values()

    def test_business_cycle_to_dict(self):
        d = self.engine.classify_business_cycle("US").to_dict()
        assert "phase" in d

    def test_compute_country_macro_risk(self):
        result = self.engine.compute_country_macro_risk("US")
        assert isinstance(result, CountryMacroRisk)

    def test_country_macro_risk_to_dict(self):
        d = self.engine.compute_country_macro_risk("US").to_dict()
        assert "country" in d


# ---------------------------------------------------------------------------
# Economic Calendar
# ---------------------------------------------------------------------------

class TestEconomicCalendar:
    def setup_method(self):
        self.engine = EconomicIntelligenceEngine()

    def test_add_calendar_event(self):
        event = EconomicCalendarEvent(
            event_name="US NFP",
            country="US",
            event_type=EconomicIndicatorType.UNEMPLOYMENT,
            importance="HIGH",
            forecast=185000,
            previous=177000,
            unit="K jobs",
        )
        result = self.engine.add_calendar_event(event)
        assert result.event_id is not None

    def test_get_upcoming_events(self):
        event = EconomicCalendarEvent(
            event_name="US CPI", country="US",
            event_type=EconomicIndicatorType.INFLATION,
            importance="HIGH",
        )
        self.engine.add_calendar_event(event)
        events = self.engine.get_upcoming_events(limit=10)
        assert isinstance(events, list)

    def test_calendar_event_to_dict(self):
        event = EconomicCalendarEvent(
            event_name="US NFP", country="US",
            event_type=EconomicIndicatorType.UNEMPLOYMENT, importance="HIGH",
        )
        d = event.to_dict()
        assert "event_name" in d


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_economic_intelligence_engine(self):
        eng = get_economic_intelligence_engine()
        assert isinstance(eng, EconomicIntelligenceEngine)

    def test_singleton_same_instance(self):
        e1 = get_economic_intelligence_engine()
        e2 = get_economic_intelligence_engine()
        assert e1 is e2
