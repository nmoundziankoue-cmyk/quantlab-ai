"""M15 Phase 2 — Macro Event Engine.

Institutional macroeconomic event catalogue with surprise scoring,
historical percentile, and volatility expectation.
Pure Python, in-memory, fully deterministic.
"""
from __future__ import annotations

import uuid
import time
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from services.event_engine import EventImportance


# ---------------------------------------------------------------------------
# MacroEventType
# ---------------------------------------------------------------------------

class MacroEventType(str, Enum):
    CPI = "cpi"
    PPI = "ppi"
    GDP = "gdp"
    RETAIL_SALES = "retail_sales"
    PMI = "pmi"
    NFP = "nfp"
    FOMC = "fomc"
    ECB = "ecb"
    BOC = "boc"
    BOJ = "boj"
    FED_MINUTES = "fed_minutes"
    INTEREST_RATE_DECISION = "interest_rate_decision"
    INFLATION = "inflation"
    UNEMPLOYMENT = "unemployment"
    HOUSING_STARTS = "housing_starts"
    CONSUMER_CONFIDENCE = "consumer_confidence"
    INDUSTRIAL_PRODUCTION = "industrial_production"
    TRADE_BALANCE = "trade_balance"
    OIL_INVENTORIES = "oil_inventories"


# Inherent volatility expectation per macro event type (0–1 scale)
_VOL_EXPECTATION: Dict[MacroEventType, float] = {
    MacroEventType.CPI: 0.80,
    MacroEventType.PPI: 0.60,
    MacroEventType.GDP: 0.85,
    MacroEventType.RETAIL_SALES: 0.55,
    MacroEventType.PMI: 0.50,
    MacroEventType.NFP: 0.90,
    MacroEventType.FOMC: 0.95,
    MacroEventType.ECB: 0.85,
    MacroEventType.BOC: 0.70,
    MacroEventType.BOJ: 0.80,
    MacroEventType.FED_MINUTES: 0.65,
    MacroEventType.INTEREST_RATE_DECISION: 0.90,
    MacroEventType.INFLATION: 0.75,
    MacroEventType.UNEMPLOYMENT: 0.60,
    MacroEventType.HOUSING_STARTS: 0.35,
    MacroEventType.CONSUMER_CONFIDENCE: 0.40,
    MacroEventType.INDUSTRIAL_PRODUCTION: 0.45,
    MacroEventType.TRADE_BALANCE: 0.50,
    MacroEventType.OIL_INVENTORIES: 0.55,
}

_DEFAULT_IMPORTANCE: Dict[MacroEventType, EventImportance] = {
    MacroEventType.CPI: EventImportance.CRITICAL,
    MacroEventType.PPI: EventImportance.HIGH,
    MacroEventType.GDP: EventImportance.CRITICAL,
    MacroEventType.RETAIL_SALES: EventImportance.HIGH,
    MacroEventType.PMI: EventImportance.MEDIUM,
    MacroEventType.NFP: EventImportance.CRITICAL,
    MacroEventType.FOMC: EventImportance.CRITICAL,
    MacroEventType.ECB: EventImportance.CRITICAL,
    MacroEventType.BOC: EventImportance.HIGH,
    MacroEventType.BOJ: EventImportance.HIGH,
    MacroEventType.FED_MINUTES: EventImportance.HIGH,
    MacroEventType.INTEREST_RATE_DECISION: EventImportance.CRITICAL,
    MacroEventType.INFLATION: EventImportance.CRITICAL,
    MacroEventType.UNEMPLOYMENT: EventImportance.HIGH,
    MacroEventType.HOUSING_STARTS: EventImportance.MEDIUM,
    MacroEventType.CONSUMER_CONFIDENCE: EventImportance.MEDIUM,
    MacroEventType.INDUSTRIAL_PRODUCTION: EventImportance.MEDIUM,
    MacroEventType.TRADE_BALANCE: EventImportance.MEDIUM,
    MacroEventType.OIL_INVENTORIES: EventImportance.LOW,
}


# ---------------------------------------------------------------------------
# MacroEvent dataclass
# ---------------------------------------------------------------------------

@dataclass
class MacroEvent:
    """Institutional macro event with surprise scoring."""

    id: str
    event_type: MacroEventType
    country: str
    timestamp: float
    importance: EventImportance
    description: str
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    surprise: Optional[float] = None
    surprise_pct: Optional[float] = None
    historical_percentile: Optional[float] = None
    volatility_expectation: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "country": self.country,
            "timestamp": self.timestamp,
            "importance": self.importance.value,
            "description": self.description,
            "actual": self.actual,
            "forecast": self.forecast,
            "previous": self.previous,
            "surprise": self.surprise,
            "surprise_pct": self.surprise_pct,
            "historical_percentile": self.historical_percentile,
            "volatility_expectation": self.volatility_expectation,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Utility — surprise computations
# ---------------------------------------------------------------------------

def _compute_surprise(actual: Optional[float], forecast: Optional[float]) -> Optional[float]:
    if actual is None or forecast is None:
        return None
    return round(actual - forecast, 6)


def _compute_surprise_pct(actual: Optional[float], forecast: Optional[float]) -> Optional[float]:
    if actual is None or forecast is None:
        return None
    denom = abs(forecast) if forecast != 0.0 else 1.0
    return round((actual - forecast) / denom * 100.0, 4)


def _historical_percentile(
    actual: Optional[float],
    historical_values: Optional[List[float]],
) -> Optional[float]:
    """Rank actual value against historical series (0–100)."""
    if actual is None or not historical_values:
        return None
    sorted_hist = sorted(historical_values)
    below = sum(1 for v in sorted_hist if v <= actual)
    return round(below / len(sorted_hist) * 100.0, 2)


# ---------------------------------------------------------------------------
# MacroEventEngine
# ---------------------------------------------------------------------------

class MacroEventEngine:
    """Registry and analytics engine for macro economic events."""

    def __init__(self) -> None:
        self._events: List[MacroEvent] = []

    def add_event(
        self,
        event_type: MacroEventType,
        description: str,
        *,
        country: str = "US",
        actual: Optional[float] = None,
        forecast: Optional[float] = None,
        previous: Optional[float] = None,
        historical_values: Optional[List[float]] = None,
        timestamp: Optional[float] = None,
        importance: Optional[EventImportance] = None,
        metadata: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> MacroEvent:
        """Create and register a macro event with derived surprise metrics."""
        surprise = _compute_surprise(actual, forecast)
        surprise_pct = _compute_surprise_pct(actual, forecast)
        hist_pct = _historical_percentile(actual, historical_values)

        # Scale vol expectation by absolute surprise magnitude
        base_vol = _VOL_EXPECTATION[event_type]
        if surprise_pct is not None:
            magnitude_boost = min(0.2, abs(surprise_pct) / 100.0)
            vol_exp = round(min(1.0, base_vol + magnitude_boost), 4)
        else:
            vol_exp = base_vol

        ev = MacroEvent(
            id=event_id or str(uuid.uuid4()),
            event_type=event_type,
            country=country.upper(),
            timestamp=timestamp if timestamp is not None else time.time(),
            importance=importance or _DEFAULT_IMPORTANCE[event_type],
            description=description,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            surprise_pct=surprise_pct,
            historical_percentile=hist_pct,
            volatility_expectation=vol_exp,
            metadata=metadata or {},
        )
        self._events.append(ev)
        return ev

    def get_by_id(self, event_id: str) -> Optional[MacroEvent]:
        for ev in self._events:
            if ev.id == event_id:
                return ev
        return None

    def filter(
        self,
        *,
        event_type: Optional[MacroEventType] = None,
        country: Optional[str] = None,
        importance: Optional[EventImportance] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        surprise_positive: Optional[bool] = None,
    ) -> List[MacroEvent]:
        """Return filtered macro events sorted newest-first."""
        result = self._events
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        if country:
            result = [e for e in result if e.country == country.upper()]
        if importance:
            result = [e for e in result if e.importance == importance]
        if since is not None:
            result = [e for e in result if e.timestamp >= since]
        if until is not None:
            result = [e for e in result if e.timestamp <= until]
        if surprise_positive is not None:
            if surprise_positive:
                result = [e for e in result if e.surprise is not None and e.surprise > 0]
            else:
                result = [e for e in result if e.surprise is not None and e.surprise < 0]
        return sorted(result, key=lambda e: e.timestamp, reverse=True)

    def all_events(self) -> List[MacroEvent]:
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def high_impact_events(self) -> List[MacroEvent]:
        """Return CRITICAL and HIGH importance events."""
        return [
            e for e in self._events
            if e.importance in (EventImportance.CRITICAL, EventImportance.HIGH)
        ]

    def statistics(self) -> Dict[str, Any]:
        if not self._events:
            return {"total": 0, "by_type": {}, "by_country": {}, "avg_surprise_pct": None}
        by_type: Dict[str, int] = {}
        by_country: Dict[str, int] = {}
        surprises = []
        for ev in self._events:
            by_type[ev.event_type.value] = by_type.get(ev.event_type.value, 0) + 1
            by_country[ev.country] = by_country.get(ev.country, 0) + 1
            if ev.surprise_pct is not None:
                surprises.append(ev.surprise_pct)
        avg_surp = round(sum(surprises) / len(surprises), 4) if surprises else None
        return {
            "total": len(self._events),
            "by_type": by_type,
            "by_country": by_country,
            "avg_surprise_pct": avg_surp,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[MacroEventEngine] = None


def get_macro_event_engine() -> MacroEventEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = MacroEventEngine()
    return _default_engine
