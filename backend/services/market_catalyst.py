"""M15 Phase 6 — Market Catalyst Engine.

Classifies events as Bullish/Bearish/Neutral and assigns CatalystScore
across 12 thematic dimensions.
Pure Python, deterministic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from services.event_engine import CorporateEvent, CorporateEventType, EventImportance, EventSeverity


# ---------------------------------------------------------------------------
# Catalyst classification enums
# ---------------------------------------------------------------------------

class CatalystDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class CatalystTheme(str, Enum):
    MACRO = "macro"
    SECTOR = "sector"
    REGULATORY = "regulatory"
    TECHNOLOGY = "technology"
    AI = "ai"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    FINANCIAL = "financial"
    GEOPOLITICAL = "geopolitical"
    SUPPLY_CHAIN = "supply_chain"
    EARNINGS = "earnings"
    CORPORATE_ACTION = "corporate_action"


# ---------------------------------------------------------------------------
# Direction rules — deterministic mapping from event type
# ---------------------------------------------------------------------------

_DIRECTION_MAP: Dict[CorporateEventType, CatalystDirection] = {
    CorporateEventType.EARNINGS: CatalystDirection.BULLISH,
    CorporateEventType.GUIDANCE: CatalystDirection.BULLISH,
    CorporateEventType.REVENUE_BEAT: CatalystDirection.BULLISH,
    CorporateEventType.EPS_BEAT: CatalystDirection.BULLISH,
    CorporateEventType.DIVIDEND: CatalystDirection.BULLISH,
    CorporateEventType.DIVIDEND_INCREASE: CatalystDirection.BULLISH,
    CorporateEventType.DIVIDEND_CUT: CatalystDirection.BEARISH,
    CorporateEventType.STOCK_SPLIT: CatalystDirection.BULLISH,
    CorporateEventType.REVERSE_SPLIT: CatalystDirection.BEARISH,
    CorporateEventType.BUYBACK: CatalystDirection.BULLISH,
    CorporateEventType.SHARE_ISSUANCE: CatalystDirection.BEARISH,
    CorporateEventType.IPO: CatalystDirection.NEUTRAL,
    CorporateEventType.SECONDARY_OFFERING: CatalystDirection.BEARISH,
    CorporateEventType.MERGER: CatalystDirection.BULLISH,
    CorporateEventType.ACQUISITION: CatalystDirection.BULLISH,
    CorporateEventType.CEO_CHANGE: CatalystDirection.NEUTRAL,
    CorporateEventType.CFO_CHANGE: CatalystDirection.NEUTRAL,
    CorporateEventType.INSIDER_BUY: CatalystDirection.BULLISH,
    CorporateEventType.INSIDER_SELL: CatalystDirection.BEARISH,
    CorporateEventType.SEC_FILING: CatalystDirection.NEUTRAL,
    CorporateEventType.FDA_APPROVAL: CatalystDirection.BULLISH,
    CorporateEventType.PRODUCT_LAUNCH: CatalystDirection.BULLISH,
    CorporateEventType.PARTNERSHIP: CatalystDirection.BULLISH,
    CorporateEventType.LITIGATION: CatalystDirection.BEARISH,
    CorporateEventType.CREDIT_UPGRADE: CatalystDirection.BULLISH,
    CorporateEventType.CREDIT_DOWNGRADE: CatalystDirection.BEARISH,
    CorporateEventType.BANKRUPTCY: CatalystDirection.BEARISH,
    CorporateEventType.RESTRUCTURING: CatalystDirection.BEARISH,
}

_THEME_MAP: Dict[CorporateEventType, CatalystTheme] = {
    CorporateEventType.EARNINGS: CatalystTheme.EARNINGS,
    CorporateEventType.GUIDANCE: CatalystTheme.EARNINGS,
    CorporateEventType.REVENUE_BEAT: CatalystTheme.EARNINGS,
    CorporateEventType.EPS_BEAT: CatalystTheme.EARNINGS,
    CorporateEventType.DIVIDEND: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.DIVIDEND_INCREASE: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.DIVIDEND_CUT: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.STOCK_SPLIT: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.REVERSE_SPLIT: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.BUYBACK: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.SHARE_ISSUANCE: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.IPO: CatalystTheme.FINANCIAL,
    CorporateEventType.SECONDARY_OFFERING: CatalystTheme.FINANCIAL,
    CorporateEventType.MERGER: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.ACQUISITION: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.CEO_CHANGE: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.CFO_CHANGE: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.INSIDER_BUY: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.INSIDER_SELL: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.SEC_FILING: CatalystTheme.REGULATORY,
    CorporateEventType.FDA_APPROVAL: CatalystTheme.REGULATORY,
    CorporateEventType.PRODUCT_LAUNCH: CatalystTheme.TECHNOLOGY,
    CorporateEventType.PARTNERSHIP: CatalystTheme.CORPORATE_ACTION,
    CorporateEventType.LITIGATION: CatalystTheme.REGULATORY,
    CorporateEventType.CREDIT_UPGRADE: CatalystTheme.FINANCIAL,
    CorporateEventType.CREDIT_DOWNGRADE: CatalystTheme.FINANCIAL,
    CorporateEventType.BANKRUPTCY: CatalystTheme.FINANCIAL,
    CorporateEventType.RESTRUCTURING: CatalystTheme.CORPORATE_ACTION,
}

# Sector → theme override
_SECTOR_THEME: Dict[str, CatalystTheme] = {
    "technology": CatalystTheme.TECHNOLOGY,
    "healthcare": CatalystTheme.HEALTHCARE,
    "energy": CatalystTheme.ENERGY,
    "financials": CatalystTheme.FINANCIAL,
    "finance": CatalystTheme.FINANCIAL,
    "materials": CatalystTheme.SUPPLY_CHAIN,
    "industrials": CatalystTheme.SUPPLY_CHAIN,
}

# Importance weight for scoring
_IMPORTANCE_WEIGHT: Dict[EventImportance, float] = {
    EventImportance.CRITICAL: 1.0,
    EventImportance.HIGH: 0.75,
    EventImportance.MEDIUM: 0.5,
    EventImportance.LOW: 0.25,
}

_SEVERITY_WEIGHT: Dict[EventSeverity, float] = {
    EventSeverity.EXTREME: 1.0,
    EventSeverity.HIGH: 0.8,
    EventSeverity.MEDIUM: 0.6,
    EventSeverity.LOW: 0.4,
    EventSeverity.MINIMAL: 0.2,
}


# ---------------------------------------------------------------------------
# CatalystScore dataclass
# ---------------------------------------------------------------------------

@dataclass
class CatalystScore:
    """Multi-dimensional catalyst classification and scoring."""

    event_id: str
    ticker: str
    direction: CatalystDirection
    theme: CatalystTheme
    raw_score: float
    importance_score: float
    severity_score: float
    confidence_score: float
    composite_score: float
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "ticker": self.ticker,
            "direction": self.direction.value,
            "theme": self.theme.value,
            "raw_score": self.raw_score,
            "importance_score": self.importance_score,
            "severity_score": self.severity_score,
            "confidence_score": self.confidence_score,
            "composite_score": self.composite_score,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# MarketCatalystEngine
# ---------------------------------------------------------------------------

class MarketCatalystEngine:
    """Classify and score corporate events as market catalysts."""

    def classify(self, event: CorporateEvent) -> CatalystScore:
        """Classify a corporate event and produce a CatalystScore.

        Args:
            event: CorporateEvent instance.

        Returns:
            CatalystScore with direction, theme, and composite score.
        """
        direction = _DIRECTION_MAP.get(event.event_type, CatalystDirection.NEUTRAL)
        # Theme: sector override takes precedence for relevant sectors
        theme = _SECTOR_THEME.get(event.sector.lower(), _THEME_MAP.get(event.event_type, CatalystTheme.CORPORATE_ACTION))

        imp_score = _IMPORTANCE_WEIGHT[event.importance]
        sev_score = _SEVERITY_WEIGHT[event.severity]
        conf_score = max(0.0, min(1.0, event.confidence))

        # Raw score: higher for bearish events to reflect risk asymmetry
        direction_multiplier = 1.0 if direction == CatalystDirection.BULLISH else (1.2 if direction == CatalystDirection.BEARISH else 0.5)
        raw = imp_score * sev_score * direction_multiplier
        composite = round((raw * 0.5 + conf_score * 0.3 + imp_score * 0.2), 6)

        tags = [event.event_type.value, direction.value, theme.value, event.sector.lower()]

        return CatalystScore(
            event_id=event.id,
            ticker=event.ticker,
            direction=direction,
            theme=theme,
            raw_score=round(raw, 6),
            importance_score=round(imp_score, 6),
            severity_score=round(sev_score, 6),
            confidence_score=round(conf_score, 6),
            composite_score=composite,
            tags=[t for t in tags if t],
        )

    def classify_batch(self, events: List[CorporateEvent]) -> List[CatalystScore]:
        return [self.classify(ev) for ev in events]

    def top_catalysts(
        self,
        events: List[CorporateEvent],
        n: int = 10,
        direction: Optional[CatalystDirection] = None,
    ) -> List[CatalystScore]:
        """Return top-n catalysts by composite score."""
        scores = self.classify_batch(events)
        if direction:
            scores = [s for s in scores if s.direction == direction]
        return sorted(scores, key=lambda s: s.composite_score, reverse=True)[:n]

    def theme_distribution(self, events: List[CorporateEvent]) -> Dict[str, int]:
        """Count events per catalyst theme."""
        dist: Dict[str, int] = {}
        for ev in events:
            score = self.classify(ev)
            k = score.theme.value
            dist[k] = dist.get(k, 0) + 1
        return dist

    def direction_distribution(self, events: List[CorporateEvent]) -> Dict[str, int]:
        """Count events per direction."""
        dist: Dict[str, int] = {}
        for ev in events:
            score = self.classify(ev)
            k = score.direction.value
            dist[k] = dist.get(k, 0) + 1
        return dist
