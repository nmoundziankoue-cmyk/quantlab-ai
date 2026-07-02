"""M15 Phase 1 — Corporate Event Engine.

Institutional corporate event catalogue with 28 event types.
Pure Python, in-memory, fully deterministic — no DB, no network.
"""
from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CorporateEventType(str, Enum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    REVENUE_BEAT = "revenue_beat"
    EPS_BEAT = "eps_beat"
    DIVIDEND = "dividend"
    DIVIDEND_INCREASE = "dividend_increase"
    DIVIDEND_CUT = "dividend_cut"
    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    BUYBACK = "buyback"
    SHARE_ISSUANCE = "share_issuance"
    IPO = "ipo"
    SECONDARY_OFFERING = "secondary_offering"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    CEO_CHANGE = "ceo_change"
    CFO_CHANGE = "cfo_change"
    INSIDER_BUY = "insider_buy"
    INSIDER_SELL = "insider_sell"
    SEC_FILING = "sec_filing"
    FDA_APPROVAL = "fda_approval"
    PRODUCT_LAUNCH = "product_launch"
    PARTNERSHIP = "partnership"
    LITIGATION = "litigation"
    CREDIT_UPGRADE = "credit_upgrade"
    CREDIT_DOWNGRADE = "credit_downgrade"
    BANKRUPTCY = "bankruptcy"
    RESTRUCTURING = "restructuring"


class EventImportance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EventSeverity(str, Enum):
    EXTREME = "extreme"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


# ---------------------------------------------------------------------------
# Importance map — default importance per event type
# ---------------------------------------------------------------------------

_DEFAULT_IMPORTANCE: Dict[CorporateEventType, EventImportance] = {
    CorporateEventType.EARNINGS: EventImportance.CRITICAL,
    CorporateEventType.GUIDANCE: EventImportance.HIGH,
    CorporateEventType.REVENUE_BEAT: EventImportance.HIGH,
    CorporateEventType.EPS_BEAT: EventImportance.HIGH,
    CorporateEventType.DIVIDEND: EventImportance.MEDIUM,
    CorporateEventType.DIVIDEND_INCREASE: EventImportance.MEDIUM,
    CorporateEventType.DIVIDEND_CUT: EventImportance.HIGH,
    CorporateEventType.STOCK_SPLIT: EventImportance.MEDIUM,
    CorporateEventType.REVERSE_SPLIT: EventImportance.HIGH,
    CorporateEventType.BUYBACK: EventImportance.MEDIUM,
    CorporateEventType.SHARE_ISSUANCE: EventImportance.HIGH,
    CorporateEventType.IPO: EventImportance.HIGH,
    CorporateEventType.SECONDARY_OFFERING: EventImportance.MEDIUM,
    CorporateEventType.MERGER: EventImportance.CRITICAL,
    CorporateEventType.ACQUISITION: EventImportance.CRITICAL,
    CorporateEventType.CEO_CHANGE: EventImportance.HIGH,
    CorporateEventType.CFO_CHANGE: EventImportance.MEDIUM,
    CorporateEventType.INSIDER_BUY: EventImportance.LOW,
    CorporateEventType.INSIDER_SELL: EventImportance.LOW,
    CorporateEventType.SEC_FILING: EventImportance.LOW,
    CorporateEventType.FDA_APPROVAL: EventImportance.CRITICAL,
    CorporateEventType.PRODUCT_LAUNCH: EventImportance.MEDIUM,
    CorporateEventType.PARTNERSHIP: EventImportance.LOW,
    CorporateEventType.LITIGATION: EventImportance.MEDIUM,
    CorporateEventType.CREDIT_UPGRADE: EventImportance.MEDIUM,
    CorporateEventType.CREDIT_DOWNGRADE: EventImportance.HIGH,
    CorporateEventType.BANKRUPTCY: EventImportance.CRITICAL,
    CorporateEventType.RESTRUCTURING: EventImportance.HIGH,
}

_DEFAULT_SEVERITY: Dict[CorporateEventType, EventSeverity] = {
    CorporateEventType.EARNINGS: EventSeverity.HIGH,
    CorporateEventType.GUIDANCE: EventSeverity.HIGH,
    CorporateEventType.REVENUE_BEAT: EventSeverity.MEDIUM,
    CorporateEventType.EPS_BEAT: EventSeverity.MEDIUM,
    CorporateEventType.DIVIDEND: EventSeverity.LOW,
    CorporateEventType.DIVIDEND_INCREASE: EventSeverity.LOW,
    CorporateEventType.DIVIDEND_CUT: EventSeverity.HIGH,
    CorporateEventType.STOCK_SPLIT: EventSeverity.LOW,
    CorporateEventType.REVERSE_SPLIT: EventSeverity.HIGH,
    CorporateEventType.BUYBACK: EventSeverity.LOW,
    CorporateEventType.SHARE_ISSUANCE: EventSeverity.MEDIUM,
    CorporateEventType.IPO: EventSeverity.HIGH,
    CorporateEventType.SECONDARY_OFFERING: EventSeverity.MEDIUM,
    CorporateEventType.MERGER: EventSeverity.EXTREME,
    CorporateEventType.ACQUISITION: EventSeverity.EXTREME,
    CorporateEventType.CEO_CHANGE: EventSeverity.HIGH,
    CorporateEventType.CFO_CHANGE: EventSeverity.MEDIUM,
    CorporateEventType.INSIDER_BUY: EventSeverity.MINIMAL,
    CorporateEventType.INSIDER_SELL: EventSeverity.MINIMAL,
    CorporateEventType.SEC_FILING: EventSeverity.MINIMAL,
    CorporateEventType.FDA_APPROVAL: EventSeverity.EXTREME,
    CorporateEventType.PRODUCT_LAUNCH: EventSeverity.MEDIUM,
    CorporateEventType.PARTNERSHIP: EventSeverity.LOW,
    CorporateEventType.LITIGATION: EventSeverity.MEDIUM,
    CorporateEventType.CREDIT_UPGRADE: EventSeverity.MEDIUM,
    CorporateEventType.CREDIT_DOWNGRADE: EventSeverity.HIGH,
    CorporateEventType.BANKRUPTCY: EventSeverity.EXTREME,
    CorporateEventType.RESTRUCTURING: EventSeverity.HIGH,
}


# ---------------------------------------------------------------------------
# CorporateEvent dataclass
# ---------------------------------------------------------------------------

@dataclass
class CorporateEvent:
    """Institutional corporate event record."""

    id: str
    ticker: str
    company: str
    sector: str
    industry: str
    country: str
    timestamp: float
    event_type: CorporateEventType
    importance: EventImportance
    severity: EventSeverity
    confidence: float
    source: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "company": self.company,
            "sector": self.sector,
            "industry": self.industry,
            "country": self.country,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "importance": self.importance.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "source": self.source,
            "description": self.description,
            "metadata": self.metadata,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# CorporateEventEngine
# ---------------------------------------------------------------------------

class CorporateEventEngine:
    """Registry and factory for institutional corporate events."""

    def __init__(self) -> None:
        self._events: List[CorporateEvent] = []

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def add_event(
        self,
        ticker: str,
        company: str,
        event_type: CorporateEventType,
        description: str,
        *,
        sector: str = "unknown",
        industry: str = "unknown",
        country: str = "US",
        confidence: float = 0.9,
        source: str = "internal",
        timestamp: Optional[float] = None,
        importance: Optional[EventImportance] = None,
        severity: Optional[EventSeverity] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        event_id: Optional[str] = None,
    ) -> CorporateEvent:
        """Create and register a corporate event."""
        ev = CorporateEvent(
            id=event_id or str(uuid.uuid4()),
            ticker=ticker.upper(),
            company=company,
            sector=sector,
            industry=industry,
            country=country,
            timestamp=timestamp if timestamp is not None else time.time(),
            event_type=event_type,
            importance=importance or _DEFAULT_IMPORTANCE[event_type],
            severity=severity or _DEFAULT_SEVERITY[event_type],
            confidence=max(0.0, min(1.0, confidence)),
            source=source,
            description=description,
            metadata=metadata or {},
            tags=tags or [],
        )
        self._events.append(ev)
        return ev

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_by_id(self, event_id: str) -> Optional[CorporateEvent]:
        """Return the event with the given id, or None."""
        for ev in self._events:
            if ev.id == event_id:
                return ev
        return None

    def filter(
        self,
        *,
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
        country: Optional[str] = None,
        event_type: Optional[CorporateEventType] = None,
        importance: Optional[EventImportance] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        tags: Optional[List[str]] = None,
    ) -> List[CorporateEvent]:
        """Return events matching all supplied filters."""
        result = self._events
        if ticker:
            t = ticker.upper()
            result = [e for e in result if e.ticker == t]
        if sector:
            s = sector.lower()
            result = [e for e in result if e.sector.lower() == s]
        if country:
            result = [e for e in result if e.country.upper() == country.upper()]
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        if importance:
            result = [e for e in result if e.importance == importance]
        if since is not None:
            result = [e for e in result if e.timestamp >= since]
        if until is not None:
            result = [e for e in result if e.timestamp <= until]
        if tags:
            tag_set = set(t.lower() for t in tags)
            result = [e for e in result if tag_set.intersection(e.tags)]
        return sorted(result, key=lambda e: e.timestamp, reverse=True)

    def all_events(self) -> List[CorporateEvent]:
        """Return all events sorted newest-first."""
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def ticker_events(self, ticker: str) -> List[CorporateEvent]:
        return self.filter(ticker=ticker)

    def recent(self, n: int = 20) -> List[CorporateEvent]:
        return self.all_events()[:n]

    def statistics(self) -> Dict[str, Any]:
        """Aggregate statistics across all events."""
        if not self._events:
            return {
                "total": 0,
                "by_type": {},
                "by_importance": {},
                "by_severity": {},
                "unique_tickers": 0,
            }
        by_type: Dict[str, int] = {}
        by_importance: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        tickers: set = set()
        for ev in self._events:
            by_type[ev.event_type.value] = by_type.get(ev.event_type.value, 0) + 1
            by_importance[ev.importance.value] = by_importance.get(ev.importance.value, 0) + 1
            by_severity[ev.severity.value] = by_severity.get(ev.severity.value, 0) + 1
            tickers.add(ev.ticker)
        return {
            "total": len(self._events),
            "by_type": by_type,
            "by_importance": by_importance,
            "by_severity": by_severity,
            "unique_tickers": len(tickers),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[CorporateEventEngine] = None


def get_corporate_event_engine() -> CorporateEventEngine:
    """Return the process-level singleton CorporateEventEngine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = CorporateEventEngine()
    return _default_engine
