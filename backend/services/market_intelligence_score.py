"""M15 Phase 9 — Market Intelligence Score Engine.

Computes a multi-dimensional intelligence score for each event:
Positive, Negative, Confidence, Importance, Novelty, Expected Volatility,
Expected Liquidity, Institutional Interest, Portfolio Relevance,
and Overall Intelligence Score.
Pure Python, deterministic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.event_engine import CorporateEvent, CorporateEventType, EventImportance, EventSeverity
from services.macro_event_engine import MacroEvent
from services.market_catalyst import CatalystDirection, CatalystScore


# ---------------------------------------------------------------------------
# Scoring weight tables
# ---------------------------------------------------------------------------

_IMPORTANCE_SCORE: Dict[EventImportance, float] = {
    EventImportance.CRITICAL: 1.0,
    EventImportance.HIGH: 0.75,
    EventImportance.MEDIUM: 0.50,
    EventImportance.LOW: 0.25,
}

_SEVERITY_SCORE: Dict[EventSeverity, float] = {
    EventSeverity.EXTREME: 1.0,
    EventSeverity.HIGH: 0.80,
    EventSeverity.MEDIUM: 0.60,
    EventSeverity.LOW: 0.40,
    EventSeverity.MINIMAL: 0.20,
}

# Novelty: how frequently each event type occurs (rare = higher novelty)
_TYPE_NOVELTY: Dict[CorporateEventType, float] = {
    CorporateEventType.EARNINGS: 0.30,
    CorporateEventType.GUIDANCE: 0.35,
    CorporateEventType.REVENUE_BEAT: 0.35,
    CorporateEventType.EPS_BEAT: 0.35,
    CorporateEventType.DIVIDEND: 0.40,
    CorporateEventType.DIVIDEND_INCREASE: 0.55,
    CorporateEventType.DIVIDEND_CUT: 0.70,
    CorporateEventType.STOCK_SPLIT: 0.60,
    CorporateEventType.REVERSE_SPLIT: 0.75,
    CorporateEventType.BUYBACK: 0.45,
    CorporateEventType.SHARE_ISSUANCE: 0.60,
    CorporateEventType.IPO: 0.80,
    CorporateEventType.SECONDARY_OFFERING: 0.65,
    CorporateEventType.MERGER: 0.90,
    CorporateEventType.ACQUISITION: 0.85,
    CorporateEventType.CEO_CHANGE: 0.80,
    CorporateEventType.CFO_CHANGE: 0.70,
    CorporateEventType.INSIDER_BUY: 0.30,
    CorporateEventType.INSIDER_SELL: 0.30,
    CorporateEventType.SEC_FILING: 0.20,
    CorporateEventType.FDA_APPROVAL: 0.90,
    CorporateEventType.PRODUCT_LAUNCH: 0.65,
    CorporateEventType.PARTNERSHIP: 0.50,
    CorporateEventType.LITIGATION: 0.60,
    CorporateEventType.CREDIT_UPGRADE: 0.65,
    CorporateEventType.CREDIT_DOWNGRADE: 0.75,
    CorporateEventType.BANKRUPTCY: 0.95,
    CorporateEventType.RESTRUCTURING: 0.70,
}

# Expected volatility per event type
_TYPE_VOL_EXPECTATION: Dict[CorporateEventType, float] = {
    CorporateEventType.EARNINGS: 0.80,
    CorporateEventType.GUIDANCE: 0.70,
    CorporateEventType.REVENUE_BEAT: 0.60,
    CorporateEventType.EPS_BEAT: 0.60,
    CorporateEventType.DIVIDEND: 0.25,
    CorporateEventType.DIVIDEND_INCREASE: 0.30,
    CorporateEventType.DIVIDEND_CUT: 0.65,
    CorporateEventType.STOCK_SPLIT: 0.30,
    CorporateEventType.REVERSE_SPLIT: 0.60,
    CorporateEventType.BUYBACK: 0.35,
    CorporateEventType.SHARE_ISSUANCE: 0.55,
    CorporateEventType.IPO: 0.75,
    CorporateEventType.SECONDARY_OFFERING: 0.50,
    CorporateEventType.MERGER: 0.90,
    CorporateEventType.ACQUISITION: 0.85,
    CorporateEventType.CEO_CHANGE: 0.70,
    CorporateEventType.CFO_CHANGE: 0.50,
    CorporateEventType.INSIDER_BUY: 0.20,
    CorporateEventType.INSIDER_SELL: 0.25,
    CorporateEventType.SEC_FILING: 0.15,
    CorporateEventType.FDA_APPROVAL: 0.95,
    CorporateEventType.PRODUCT_LAUNCH: 0.55,
    CorporateEventType.PARTNERSHIP: 0.35,
    CorporateEventType.LITIGATION: 0.50,
    CorporateEventType.CREDIT_UPGRADE: 0.40,
    CorporateEventType.CREDIT_DOWNGRADE: 0.65,
    CorporateEventType.BANKRUPTCY: 0.95,
    CorporateEventType.RESTRUCTURING: 0.60,
}

# Institutional interest: events that large institutions actively track
_TYPE_INST_INTEREST: Dict[CorporateEventType, float] = {
    CorporateEventType.EARNINGS: 0.95,
    CorporateEventType.GUIDANCE: 0.90,
    CorporateEventType.MERGER: 0.95,
    CorporateEventType.ACQUISITION: 0.95,
    CorporateEventType.FDA_APPROVAL: 0.90,
    CorporateEventType.CEO_CHANGE: 0.85,
    CorporateEventType.BUYBACK: 0.75,
    CorporateEventType.BANKRUPTCY: 0.80,
    CorporateEventType.IPO: 0.80,
    CorporateEventType.CREDIT_DOWNGRADE: 0.70,
    CorporateEventType.CREDIT_UPGRADE: 0.65,
    CorporateEventType.DIVIDEND: 0.70,
    CorporateEventType.RESTRUCTURING: 0.70,
    CorporateEventType.REVENUE_BEAT: 0.80,
    CorporateEventType.EPS_BEAT: 0.80,
}


def _inst_interest(event_type: CorporateEventType) -> float:
    return _TYPE_INST_INTEREST.get(event_type, 0.40)


# ---------------------------------------------------------------------------
# MarketIntelligenceScore dataclass
# ---------------------------------------------------------------------------

@dataclass
class MarketIntelligenceScore:
    """Composite market intelligence score for an event."""

    event_id: str
    positive_score: float
    negative_score: float
    confidence_score: float
    importance_score: float
    novelty_score: float
    expected_volatility: float
    expected_liquidity: float
    institutional_interest: float
    portfolio_relevance: float
    overall_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "positive_score": self.positive_score,
            "negative_score": self.negative_score,
            "confidence_score": self.confidence_score,
            "importance_score": self.importance_score,
            "novelty_score": self.novelty_score,
            "expected_volatility": self.expected_volatility,
            "expected_liquidity": self.expected_liquidity,
            "institutional_interest": self.institutional_interest,
            "portfolio_relevance": self.portfolio_relevance,
            "overall_score": self.overall_score,
        }


# ---------------------------------------------------------------------------
# MarketIntelligenceScorer
# ---------------------------------------------------------------------------

class MarketIntelligenceScorer:
    """Compute MarketIntelligenceScore for corporate and macro events."""

    def score_corporate(
        self,
        event: CorporateEvent,
        catalyst: Optional[CatalystScore] = None,
    ) -> MarketIntelligenceScore:
        """Score a corporate event across all intelligence dimensions.

        Args:
            event: CorporateEvent instance.
            catalyst: Optional pre-computed CatalystScore for direction-aware scoring.

        Returns:
            MarketIntelligenceScore with all 10 dimensions.
        """
        imp = _IMPORTANCE_SCORE[event.importance]
        sev = _SEVERITY_SCORE[event.severity]
        novelty = _TYPE_NOVELTY.get(event.event_type, 0.5)
        exp_vol = _TYPE_VOL_EXPECTATION.get(event.event_type, 0.5)
        inst_int = _inst_interest(event.event_type)
        conf = max(0.0, min(1.0, event.confidence))

        # Liquidity: higher vol → lower expected liquidity (wider spreads)
        exp_liq = round(max(0.0, 1.0 - exp_vol * 0.6), 4)

        # Direction-aware positive/negative split
        direction = catalyst.direction if catalyst else None
        from services.market_catalyst import CatalystDirection
        if direction == CatalystDirection.BULLISH:
            positive = round(imp * sev * conf, 6)
            negative = round(imp * sev * (1.0 - conf) * 0.4, 6)
        elif direction == CatalystDirection.BEARISH:
            negative = round(imp * sev * conf, 6)
            positive = round(imp * sev * (1.0 - conf) * 0.4, 6)
        else:
            positive = round(imp * sev * conf * 0.5, 6)
            negative = round(imp * sev * (1.0 - conf) * 0.5, 6)

        portfolio_relevance = round((imp * 0.4 + inst_int * 0.4 + novelty * 0.2), 6)

        overall = round(
            imp * 0.25
            + conf * 0.15
            + novelty * 0.15
            + inst_int * 0.20
            + sev * 0.15
            + portfolio_relevance * 0.10,
            6,
        )

        return MarketIntelligenceScore(
            event_id=event.id,
            positive_score=min(1.0, positive),
            negative_score=min(1.0, negative),
            confidence_score=round(conf, 6),
            importance_score=round(imp, 6),
            novelty_score=round(novelty, 6),
            expected_volatility=round(exp_vol, 6),
            expected_liquidity=round(exp_liq, 6),
            institutional_interest=round(inst_int, 6),
            portfolio_relevance=round(portfolio_relevance, 6),
            overall_score=min(1.0, overall),
        )

    def score_macro(self, event: MacroEvent) -> MarketIntelligenceScore:
        """Score a macro event."""
        imp = _IMPORTANCE_SCORE[event.importance]
        exp_vol = event.volatility_expectation if event.volatility_expectation is not None else 0.5
        conf = 0.85 if event.actual is not None else 0.50
        surprise_pct = abs(event.surprise_pct) if event.surprise_pct is not None else 0.0
        novelty = min(1.0, 0.5 + surprise_pct / 200.0)

        positive = round(imp * conf * (0.5 + max(0.0, (event.surprise_pct or 0) / 200.0)), 6)
        negative = round(imp * conf * (0.5 + max(0.0, -(event.surprise_pct or 0) / 200.0)), 6)
        positive = min(1.0, positive)
        negative = min(1.0, negative)

        inst_int = min(1.0, imp * 0.9 + 0.1)
        exp_liq = max(0.0, 1.0 - exp_vol * 0.5)
        portfolio_relevance = round(imp * 0.5 + inst_int * 0.5, 6)

        overall = round(
            imp * 0.30 + conf * 0.20 + novelty * 0.15 + inst_int * 0.20 + portfolio_relevance * 0.15,
            6,
        )

        return MarketIntelligenceScore(
            event_id=event.id,
            positive_score=positive,
            negative_score=negative,
            confidence_score=round(conf, 6),
            importance_score=round(imp, 6),
            novelty_score=round(novelty, 6),
            expected_volatility=round(exp_vol, 6),
            expected_liquidity=round(exp_liq, 6),
            institutional_interest=round(inst_int, 6),
            portfolio_relevance=round(portfolio_relevance, 6),
            overall_score=min(1.0, overall),
        )

    def score_batch(
        self,
        events: List[CorporateEvent],
        catalysts: Optional[List[CatalystScore]] = None,
    ) -> List[MarketIntelligenceScore]:
        """Score a list of corporate events."""
        cat_map: Dict[str, CatalystScore] = {}
        if catalysts:
            cat_map = {c.event_id: c for c in catalysts}
        return [self.score_corporate(ev, cat_map.get(ev.id)) for ev in events]
