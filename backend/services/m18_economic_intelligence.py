"""M18 — Economic Intelligence: macroeconomic data, indicators, and forecasting.

Manages an economic indicator database, business cycle detection, recession
probability modelling, yield curve analysis, inflation forecasting, and
country/sector macro-risk scoring.

Pure Python, no external libraries.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EconomicIndicatorType(str, Enum):
    """Category of economic indicator."""
    GDP = "GDP"
    INFLATION = "INFLATION"
    UNEMPLOYMENT = "UNEMPLOYMENT"
    INTEREST_RATE = "INTEREST_RATE"
    PMI = "PMI"
    CONSUMER_CONFIDENCE = "CONSUMER_CONFIDENCE"
    RETAIL_SALES = "RETAIL_SALES"
    TRADE_BALANCE = "TRADE_BALANCE"
    HOUSING = "HOUSING"
    INDUSTRIAL_PRODUCTION = "INDUSTRIAL_PRODUCTION"
    MONEY_SUPPLY = "MONEY_SUPPLY"
    CREDIT = "CREDIT"
    LEADING = "LEADING"
    CURRENCY = "CURRENCY"
    COMMODITY = "COMMODITY"
    OTHER = "OTHER"


class BusinessCyclePhase(str, Enum):
    """Business cycle phase."""
    EXPANSION = "EXPANSION"
    PEAK = "PEAK"
    CONTRACTION = "CONTRACTION"
    TROUGH = "TROUGH"
    RECOVERY = "RECOVERY"
    UNKNOWN = "UNKNOWN"


class SurpriseDirection(str, Enum):
    """Direction of an economic data release surprise."""
    BEAT = "BEAT"
    MISS = "MISS"
    IN_LINE = "IN_LINE"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EconomicIndicator:
    """A stored economic indicator observation.

    Args:
        indicator_id: Unique ID.
        name: Human-readable name.
        country: ISO country code.
        indicator_type: Category.
        value: Observed value.
        previous_value: Prior release value.
        forecast: Consensus forecast.
        surprise: Actual minus forecast.
        surprise_direction: BEAT / MISS / IN_LINE.
        release_date: Date of release (UTC).
        next_release: Expected next release date (UTC).
        unit: Measurement unit (e.g. "% YoY").
        frequency: Reporting frequency (e.g. "Monthly").
    """

    indicator_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    country: str = ""
    indicator_type: EconomicIndicatorType = EconomicIndicatorType.OTHER
    value: float = 0.0
    previous_value: float = 0.0
    forecast: float = 0.0
    surprise: float = 0.0
    surprise_direction: SurpriseDirection = SurpriseDirection.IN_LINE
    release_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_release: Optional[datetime] = None
    unit: str = ""
    frequency: str = ""

    def __post_init__(self) -> None:
        self.surprise = self.value - self.forecast
        threshold = 0.001
        if abs(self.surprise) < threshold:
            self.surprise_direction = SurpriseDirection.IN_LINE
        elif self.surprise > 0:
            self.surprise_direction = SurpriseDirection.BEAT
        else:
            self.surprise_direction = SurpriseDirection.MISS

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "indicator_id": self.indicator_id,
            "name": self.name,
            "country": self.country,
            "indicator_type": self.indicator_type.value,
            "value": round(self.value, 6),
            "previous_value": round(self.previous_value, 6),
            "forecast": round(self.forecast, 6),
            "surprise": round(self.surprise, 6),
            "surprise_direction": self.surprise_direction.value,
            "release_date": self.release_date.isoformat(),
            "next_release": self.next_release.isoformat() if self.next_release else None,
            "unit": self.unit,
            "frequency": self.frequency,
        }


@dataclass
class YieldCurveSnapshot:
    """Yield curve snapshot at a single point in time.

    Args:
        snapshot_id: Unique ID.
        country: ISO country code.
        tenors: Mapping of tenor string to yield (e.g. "10Y" → 0.042).
        spread_2s10s: 10-year minus 2-year spread.
        spread_3m10y: 10-year minus 3-month spread.
        is_inverted: True if 2s10s < 0.
        steepness_percentile: Historical percentile of current slope.
        timestamp: Snapshot time UTC.
    """

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    country: str = ""
    tenors: Dict[str, float] = field(default_factory=dict)
    spread_2s10s: float = 0.0
    spread_3m10y: float = 0.0
    is_inverted: bool = False
    steepness_percentile: float = 50.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.tenors and self.spread_2s10s == 0.0:
            y2 = self.tenors.get("2Y", 0.0)
            y10 = self.tenors.get("10Y", 0.0)
            y3m = self.tenors.get("3M", 0.0)
            if y2 or y10:
                self.spread_2s10s = y10 - y2
                self.spread_3m10y = y10 - y3m
                self.is_inverted = self.spread_2s10s < 0

    @property
    def slope(self) -> float:
        """2s10s spread as a proxy for yield curve slope."""
        return self.spread_2s10s

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "country": self.country,
            "tenors": {k: round(v, 6) for k, v in self.tenors.items()},
            "spread_2s10s": round(self.spread_2s10s, 6),
            "spread_3m10y": round(self.spread_3m10y, 6),
            "is_inverted": self.is_inverted,
            "steepness_percentile": round(self.steepness_percentile, 2),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RecessionProbability:
    """Recession probability estimate.

    Args:
        country: ISO country code.
        probability_12m: Probability of recession in next 12 months (0-1).
        probability_24m: Probability in next 24 months.
        model: Model used (e.g. "PROBIT_YIELD_CURVE").
        key_drivers: Dict of driver → impact.
        timestamp: Estimate time.
    """

    country: str
    probability_12m: float
    probability_24m: float
    model: str
    key_drivers: Dict[str, float]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "country": self.country,
            "probability_12m": round(self.probability_12m, 4),
            "probability_24m": round(self.probability_24m, 4),
            "model": self.model,
            "key_drivers": {k: round(v, 4) for k, v in self.key_drivers.items()},
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class InflationForecast:
    """Multi-horizon inflation forecast.

    Args:
        country: ISO country code.
        current_cpi_yoy: Current CPI YoY.
        forecast_3m: 3-month ahead forecast.
        forecast_6m: 6-month ahead forecast.
        forecast_12m: 12-month ahead forecast.
        breakeven_inflation: Implied from yield curve.
        trend: Direction of inflation ("RISING", "FALLING", "STABLE").
        timestamp: Forecast timestamp.
    """

    country: str
    current_cpi_yoy: float
    forecast_3m: float
    forecast_6m: float
    forecast_12m: float
    breakeven_inflation: float
    trend: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "country": self.country,
            "current_cpi_yoy": round(self.current_cpi_yoy, 4),
            "forecast_3m": round(self.forecast_3m, 4),
            "forecast_6m": round(self.forecast_6m, 4),
            "forecast_12m": round(self.forecast_12m, 4),
            "breakeven_inflation": round(self.breakeven_inflation, 4),
            "trend": self.trend,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BusinessCycleAnalysis:
    """Business cycle phase analysis.

    Args:
        country: ISO country code.
        phase: Current business cycle phase.
        confidence: Model confidence in the phase assignment (0-1).
        leading_indicators_score: Aggregate leading indicator score.
        coincident_indicators_score: Aggregate coincident indicator score.
        lagging_indicators_score: Aggregate lagging indicator score.
        months_in_phase: Estimated duration in current phase.
        notes: Analyst notes.
        timestamp: Analysis time.
    """

    country: str
    phase: BusinessCyclePhase
    confidence: float
    leading_indicators_score: float
    coincident_indicators_score: float
    lagging_indicators_score: float
    months_in_phase: int
    notes: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "country": self.country,
            "phase": self.phase.value,
            "confidence": round(self.confidence, 4),
            "leading_indicators_score": round(self.leading_indicators_score, 4),
            "coincident_indicators_score": round(self.coincident_indicators_score, 4),
            "lagging_indicators_score": round(self.lagging_indicators_score, 4),
            "months_in_phase": self.months_in_phase,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CountryMacroRisk:
    """Macro-risk score for a single country.

    Args:
        country: ISO country code.
        composite_risk_score: Aggregate risk score 0 (low) to 100 (high).
        fiscal_risk: Government balance/debt risk.
        monetary_risk: Central bank policy risk.
        external_risk: Current account / FX risk.
        political_risk: Political stability risk.
        growth_outlook: GDP growth forecast.
        key_risks: Top 3 risk narratives.
        timestamp: Assessment time.
    """

    country: str
    composite_risk_score: float
    fiscal_risk: float
    monetary_risk: float
    external_risk: float
    political_risk: float
    growth_outlook: float
    key_risks: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "country": self.country,
            "composite_risk_score": round(self.composite_risk_score, 2),
            "fiscal_risk": round(self.fiscal_risk, 2),
            "monetary_risk": round(self.monetary_risk, 2),
            "external_risk": round(self.external_risk, 2),
            "political_risk": round(self.political_risk, 2),
            "growth_outlook": round(self.growth_outlook, 4),
            "key_risks": self.key_risks,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EconomicCalendarEvent:
    """A scheduled economic data release.

    Args:
        event_id: Unique ID.
        event_name: Event name (e.g. "US CPI MoM").
        country: ISO country code.
        event_type: Type of release.
        scheduled_time: UTC release time.
        forecast: Consensus forecast.
        previous: Prior reading.
        importance: HIGH / MEDIUM / LOW.
        unit: Unit of measurement.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_name: str = ""
    country: str = ""
    event_type: EconomicIndicatorType = EconomicIndicatorType.OTHER
    scheduled_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    forecast: float = 0.0
    previous: float = 0.0
    importance: str = "MEDIUM"
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "country": self.country,
            "event_type": self.event_type.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "forecast": round(self.forecast, 6),
            "previous": round(self.previous, 6),
            "importance": self.importance,
            "unit": self.unit,
        }


# ---------------------------------------------------------------------------
# Economic Intelligence Engine
# ---------------------------------------------------------------------------

class EconomicIntelligenceEngine:
    """Macroeconomic intelligence engine.

    Stores indicator releases, models yield curves, estimates recession
    probabilities, generates inflation forecasts, and assesses country risk.
    """

    def __init__(self) -> None:
        self._indicators: Dict[str, EconomicIndicator] = {}
        self._yield_curves: Dict[str, List[YieldCurveSnapshot]] = {}
        self._calendar: List[EconomicCalendarEvent] = []
        self._country_macro: Dict[str, CountryMacroRisk] = {}

    # ------------------------------------------------------------------
    # Indicator management
    # ------------------------------------------------------------------

    def record_indicator(self, indicator: "EconomicIndicator") -> "EconomicIndicator":
        """Store an EconomicIndicator observation.

        Args:
            indicator: Pre-built EconomicIndicator instance.

        Returns:
            The stored EconomicIndicator (same object).
        """
        key = f"{indicator.country.upper()}:{indicator.name}"
        indicator.country = indicator.country.upper()
        self._indicators[key] = indicator
        return indicator

    def get_indicator(self, country: str, name: str) -> Optional[EconomicIndicator]:
        """Retrieve the latest observation for a named indicator.

        Args:
            country: ISO country code.
            name: Indicator name.

        Returns:
            EconomicIndicator or None.
        """
        return self._indicators.get(f"{country.upper()}:{name}")

    def list_indicators(
        self,
        country: Optional[str] = None,
        indicator_type: Optional[EconomicIndicatorType] = None,
    ) -> List[EconomicIndicator]:
        """List all stored indicators with optional filters.

        Args:
            country: Filter by country.
            indicator_type: Filter by type.

        Returns:
            Filtered list.
        """
        results = list(self._indicators.values())
        if country:
            c = country.upper()
            results = [i for i in results if i.country == c]
        if indicator_type:
            results = [i for i in results if i.indicator_type == indicator_type]
        return results

    def get_indicators(
        self,
        country: Optional[str] = None,
        indicator_type: Optional[EconomicIndicatorType] = None,
    ) -> List[EconomicIndicator]:
        """Alias for list_indicators.

        Args:
            country: Filter by country.
            indicator_type: Filter by type.

        Returns:
            Filtered list.
        """
        return self.list_indicators(country=country, indicator_type=indicator_type)

    # ------------------------------------------------------------------
    # Yield curve
    # ------------------------------------------------------------------

    def record_yield_curve(
        self,
        country: str,
        tenors: Dict[str, float],
    ) -> YieldCurveSnapshot:
        """Record a yield curve snapshot.

        Args:
            country: ISO country code.
            tenors: Tenor string → yield fraction (e.g. {"2Y": 0.042}).

        Returns:
            YieldCurveSnapshot.
        """
        c = country.upper()
        y2 = tenors.get("2Y", 0.0)
        y10 = tenors.get("10Y", 0.0)
        y3m = tenors.get("3M", 0.0)
        spread_2s10s = y10 - y2
        spread_3m10y = y10 - y3m
        is_inverted = spread_2s10s < 0
        history = self._yield_curves.get(c, [])
        old_spreads = [s.spread_2s10s for s in history[-252:]]
        old_spreads_sorted = sorted(old_spreads)
        if old_spreads_sorted:
            rank = sum(1 for s in old_spreads_sorted if s <= spread_2s10s)
            pct = rank / len(old_spreads_sorted) * 100
        else:
            pct = 50.0
        snapshot = YieldCurveSnapshot(
            snapshot_id=str(uuid.uuid4()),
            country=c, tenors=tenors,
            spread_2s10s=spread_2s10s,
            spread_3m10y=spread_3m10y,
            is_inverted=is_inverted,
            steepness_percentile=pct,
            timestamp=datetime.now(timezone.utc),
        )
        if c not in self._yield_curves:
            self._yield_curves[c] = []
        self._yield_curves[c].append(snapshot)
        return snapshot

    def get_latest_yield_curve(self, country: str) -> Optional[YieldCurveSnapshot]:
        """Retrieve the most recent yield curve for a country.

        Args:
            country: ISO country code.

        Returns:
            YieldCurveSnapshot or None.
        """
        history = self._yield_curves.get(country.upper(), [])
        return history[-1] if history else None

    def get_yield_curve(self, country: str) -> Optional[YieldCurveSnapshot]:
        """Alias for get_latest_yield_curve.

        Args:
            country: ISO country code.

        Returns:
            YieldCurveSnapshot or None.
        """
        return self.get_latest_yield_curve(country)

    def get_yield_curve_history(
        self, country: str, limit: int = 50
    ) -> List[YieldCurveSnapshot]:
        """Return historical yield curve snapshots for a country.

        Args:
            country: ISO country code.
            limit: Maximum snapshots to return.

        Returns:
            List of YieldCurveSnapshot, most recent last.
        """
        history = self._yield_curves.get(country.upper(), [])
        return history[-limit:]

    def compute_yield_curve_spreads(self, country: str) -> Dict[str, float]:
        """Compute key spreads from the latest yield curve.

        Args:
            country: ISO country code.

        Returns:
            Dict of spread name → value, e.g. {"2s10s": 0.003, "3m10y": -0.002}.
        """
        yc = self.get_latest_yield_curve(country)
        if not yc:
            return {}
        return {
            "2s10s": round(yc.spread_2s10s, 6),
            "3m10y": round(yc.spread_3m10y, 6),
            "is_inverted": yc.is_inverted,
            "steepness_percentile": round(yc.steepness_percentile, 2),
        }

    # ------------------------------------------------------------------
    # Recession probability
    # ------------------------------------------------------------------

    def compute_recession_probability(self, country: str) -> RecessionProbability:
        """Estimate recession probability using yield curve and indicator signals.

        Uses a simplified probit-style model: spread inversion contributes
        positively to recession probability; strong PMI and GDP growth reduce it.

        Args:
            country: ISO country code.

        Returns:
            RecessionProbability.
        """
        c = country.upper()
        yc = self.get_latest_yield_curve(c)
        spread = yc.spread_2s10s if yc else 0.01
        key_drivers: Dict[str, float] = {}
        spread_contribution = max(0.0, min(0.5, -spread * 20))
        key_drivers["yield_curve_inversion"] = spread_contribution
        gdp_key = f"{c}:GDP"
        gdp_ind = self._indicators.get(gdp_key)
        gdp_contribution = 0.0
        if gdp_ind and gdp_ind.value < 0:
            gdp_contribution = min(0.3, abs(gdp_ind.value) * 0.05)
        key_drivers["negative_gdp_growth"] = gdp_contribution
        unemployment_key = f"{c}:UNEMPLOYMENT"
        unemp_ind = self._indicators.get(unemployment_key)
        unemp_contribution = 0.0
        if unemp_ind and unemp_ind.surprise < 0:
            unemp_contribution = min(0.2, abs(unemp_ind.surprise) * 0.02)
        key_drivers["rising_unemployment"] = unemp_contribution
        raw_prob_12m = min(0.95, spread_contribution + gdp_contribution + unemp_contribution)
        raw_prob_24m = min(0.95, raw_prob_12m * 1.3)
        return RecessionProbability(
            country=c,
            probability_12m=raw_prob_12m,
            probability_24m=raw_prob_24m,
            model="PROBIT_YIELD_CURVE",
            key_drivers=key_drivers,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Inflation forecast
    # ------------------------------------------------------------------

    def compute_inflation_forecast(self, country: str) -> InflationForecast:
        """Estimate inflation trajectory for a country.

        Args:
            country: ISO country code.

        Returns:
            InflationForecast.
        """
        c = country.upper()
        cpi_key = f"{c}:CPI"
        cpi_ind = self._indicators.get(cpi_key)
        current_cpi = cpi_ind.value if cpi_ind else 0.03
        yc = self.get_latest_yield_curve(c)
        y10 = yc.tenors.get("10Y", 0.04) if yc else 0.04
        y10_tips = y10 - 0.015
        breakeven = max(0.0, y10 - y10_tips)
        mean_reversion_target = 0.02
        decay = 0.7
        forecast_3m = current_cpi * decay + mean_reversion_target * (1 - decay)
        forecast_6m = forecast_3m * decay + mean_reversion_target * (1 - decay)
        forecast_12m = forecast_6m * decay + mean_reversion_target * (1 - decay)
        if forecast_12m > current_cpi + 0.001:
            trend = "RISING"
        elif forecast_12m < current_cpi - 0.001:
            trend = "FALLING"
        else:
            trend = "STABLE"
        return InflationForecast(
            country=c,
            current_cpi_yoy=current_cpi,
            forecast_3m=forecast_3m,
            forecast_6m=forecast_6m,
            forecast_12m=forecast_12m,
            breakeven_inflation=breakeven,
            trend=trend,
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Business cycle
    # ------------------------------------------------------------------

    def classify_business_cycle(self, country: str) -> BusinessCycleAnalysis:
        """Alias for analyse_business_cycle.

        Args:
            country: ISO country code.

        Returns:
            BusinessCycleAnalysis.
        """
        return self.analyse_business_cycle(country)

    def analyse_business_cycle(self, country: str) -> BusinessCycleAnalysis:
        """Classify the current business cycle phase for a country.

        Args:
            country: ISO country code.

        Returns:
            BusinessCycleAnalysis.
        """
        c = country.upper()
        pmi_key = f"{c}:PMI"
        gdp_key = f"{c}:GDP"
        leading_key = f"{c}:LEADING"
        pmi_ind = self._indicators.get(pmi_key)
        gdp_ind = self._indicators.get(gdp_key)
        leading_ind = self._indicators.get(leading_key)
        pmi_val = pmi_ind.value if pmi_ind else 50.0
        gdp_val = gdp_ind.value if gdp_ind else 2.0
        leading_val = leading_ind.value if leading_ind else 0.0
        leading_score = (pmi_val - 50.0) / 10.0 + leading_val * 0.1
        coincident_score = gdp_val / 3.0
        lagging_score = 0.5
        if leading_score > 0.5 and coincident_score > 0.5:
            phase = BusinessCyclePhase.EXPANSION
            confidence = 0.75
        elif leading_score < -0.5 and coincident_score < 0:
            phase = BusinessCyclePhase.CONTRACTION
            confidence = 0.70
        elif leading_score > 0 and coincident_score < 0:
            phase = BusinessCyclePhase.RECOVERY
            confidence = 0.60
        elif leading_score < 0 and coincident_score > 0.5:
            phase = BusinessCyclePhase.PEAK
            confidence = 0.55
        else:
            phase = BusinessCyclePhase.UNKNOWN
            confidence = 0.30
        return BusinessCycleAnalysis(
            country=c, phase=phase, confidence=confidence,
            leading_indicators_score=leading_score,
            coincident_indicators_score=coincident_score,
            lagging_indicators_score=lagging_score,
            months_in_phase=12,
            notes=f"PMI={pmi_val:.1f}, GDP={gdp_val:.2f}%",
            timestamp=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Country macro risk
    # ------------------------------------------------------------------

    def assess_country_risk(
        self,
        country: str,
        fiscal_risk: float = 30.0,
        monetary_risk: float = 25.0,
        external_risk: float = 20.0,
        political_risk: float = 20.0,
        growth_outlook: float = 0.025,
        key_risks: Optional[List[str]] = None,
    ) -> CountryMacroRisk:
        """Assess and store macro-risk for a country.

        Args:
            country: ISO country code.
            fiscal_risk: Fiscal risk score 0-100.
            monetary_risk: Monetary risk score 0-100.
            external_risk: External/FX risk score 0-100.
            political_risk: Political risk score 0-100.
            growth_outlook: GDP growth rate forecast.
            key_risks: Top 3 risk narratives.

        Returns:
            CountryMacroRisk.
        """
        c = country.upper()
        composite = (fiscal_risk * 0.30 + monetary_risk * 0.25
                     + external_risk * 0.25 + political_risk * 0.20)
        risk = CountryMacroRisk(
            country=c,
            composite_risk_score=composite,
            fiscal_risk=fiscal_risk,
            monetary_risk=monetary_risk,
            external_risk=external_risk,
            political_risk=political_risk,
            growth_outlook=growth_outlook,
            key_risks=key_risks or [],
            timestamp=datetime.now(timezone.utc),
        )
        self._country_macro[c] = risk
        return risk

    def get_country_risk(self, country: str) -> Optional[CountryMacroRisk]:
        """Retrieve the latest macro-risk assessment for a country.

        Args:
            country: ISO country code.

        Returns:
            CountryMacroRisk or None.
        """
        return self._country_macro.get(country.upper())

    def compute_country_macro_risk(self, country: str) -> CountryMacroRisk:
        """Compute or retrieve macro-risk for a country using stored indicator data.

        Args:
            country: ISO country code.

        Returns:
            CountryMacroRisk.
        """
        existing = self.get_country_risk(country)
        if existing:
            return existing
        return self.assess_country_risk(country)

    # ------------------------------------------------------------------
    # Economic calendar
    # ------------------------------------------------------------------

    def add_calendar_event(self, event: "EconomicCalendarEvent") -> "EconomicCalendarEvent":
        """Add a pre-built EconomicCalendarEvent to the calendar.

        Args:
            event: Calendar event to store.

        Returns:
            The stored event.
        """
        self._calendar.append(event)
        return event

    def schedule_event(
        self,
        name: str,
        country: str,
        indicator_type: EconomicIndicatorType,
        scheduled_time: datetime,
        forecast: float = 0.0,
        previous: float = 0.0,
        importance: str = "MEDIUM",
    ) -> EconomicCalendarEvent:
        """Add an event to the economic calendar.

        Args:
            name: Event name.
            country: ISO country code.
            indicator_type: Indicator category.
            scheduled_time: Scheduled release time (UTC).
            forecast: Consensus forecast.
            previous: Prior reading.
            importance: HIGH / MEDIUM / LOW.

        Returns:
            EconomicCalendarEvent.
        """
        event = EconomicCalendarEvent(
            event_id=str(uuid.uuid4()),
            event_name=name, country=country.upper(),
            event_type=indicator_type,
            scheduled_time=scheduled_time,
            forecast=forecast, previous=previous,
            importance=importance,
        )
        self._calendar.append(event)
        return event

    def get_upcoming_events(
        self, limit: int = 20, country: Optional[str] = None
    ) -> List[EconomicCalendarEvent]:
        """Return calendar events sorted by scheduled time.

        Args:
            limit: Maximum events to return.
            country: Optional country filter.

        Returns:
            List of EconomicCalendarEvent.
        """
        events = list(self._calendar)
        if country:
            c = country.upper()
            events = [e for e in events if e.country == c]
        events.sort(key=lambda e: e.scheduled_time)
        return events[:limit]

    def get_calendar(self, limit: int = 50) -> List[EconomicCalendarEvent]:
        """Return all scheduled events (past and future), newest first.

        Args:
            limit: Maximum events.

        Returns:
            List of EconomicCalendarEvent.
        """
        sorted_events = sorted(
            self._calendar, key=lambda e: e.scheduled_time, reverse=True
        )
        return sorted_events[:limit]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[EconomicIntelligenceEngine] = None


def get_economic_intelligence_engine() -> EconomicIntelligenceEngine:
    """Return the singleton EconomicIntelligenceEngine.

    Returns:
        Shared EconomicIntelligenceEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = EconomicIntelligenceEngine()
    return _default_engine
