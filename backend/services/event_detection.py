"""M14 Phase 6 — Alternative-data event detection engine.

Rule-based classifiers that scan document/headline text and emit normalized
`AltEvent` objects. Deterministic keyword + regex matching — no ML model,
no network call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AltEventType(Enum):
    EARNINGS = "earnings"
    GUIDANCE_CHANGE = "guidance_change"
    CEO_CHANGE = "ceo_change"
    CFO_CHANGE = "cfo_change"
    MNA = "mna"
    BANKRUPTCY = "bankruptcy"
    BUYBACK = "buyback"
    SECONDARY_OFFERING = "secondary_offering"
    DIVIDEND = "dividend"
    CREDIT_DOWNGRADE = "credit_downgrade"
    REGULATORY_ACTION = "regulatory_action"
    PATENT_APPROVAL = "patent_approval"
    SUPPLY_CHAIN_DISRUPTION = "supply_chain_disruption"
    WEATHER_IMPACT = "weather_impact"
    GEOPOLITICAL = "geopolitical"


class EventSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AltEvent:
    event_type: AltEventType
    symbol: str
    confidence: float
    severity: EventSeverity
    snippet: str
    source_doc_id: Optional[str] = None
    matched_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "event_type": self.event_type.value,
            "symbol": self.symbol,
            "confidence": self.confidence,
            "severity": self.severity.value,
            "snippet": self.snippet,
            "source_doc_id": self.source_doc_id,
            "matched_patterns": self.matched_patterns,
        }


# ---------------------------------------------------------------------------
# Pattern catalog: (event_type, [regex patterns], base_severity)
# ---------------------------------------------------------------------------

_PATTERNS: List[Dict[str, object]] = [
    {
        "type": AltEventType.EARNINGS,
        "patterns": [r"reported\s+(?:quarterly\s+)?earnings", r"earnings\s+per\s+share", r"q[1-4]\s+results"],
        "severity": EventSeverity.MEDIUM,
    },
    {
        "type": AltEventType.GUIDANCE_CHANGE,
        "patterns": [r"(?:raised|lowered|cut|reaffirmed)\s+(?:its\s+)?(?:full.year\s+)?guidance", r"updated\s+outlook"],
        "severity": EventSeverity.HIGH,
    },
    {
        "type": AltEventType.CEO_CHANGE,
        "patterns": [r"(?:names?|appoints?|announc\w+)\s+new\s+(?:chief executive officer|ceo)",
                     r"ceo\s+(?:to\s+)?(?:resign|step down|retire|depart)"],
        "severity": EventSeverity.HIGH,
    },
    {
        "type": AltEventType.CFO_CHANGE,
        "patterns": [r"(?:names?|appoints?|announc\w+)\s+new\s+(?:chief financial officer|cfo)",
                     r"cfo\s+(?:to\s+)?(?:resign|step down|retire|depart)"],
        "severity": EventSeverity.MEDIUM,
    },
    {
        "type": AltEventType.MNA,
        "patterns": [r"agrees?\s+to\s+acquire", r"merger\s+agreement", r"to\s+be\s+acquired\s+by", r"definitive\s+agreement\s+to\s+merge"],
        "severity": EventSeverity.HIGH,
    },
    {
        "type": AltEventType.BANKRUPTCY,
        "patterns": [r"files?\s+for\s+chapter\s+11", r"bankruptcy\s+protection", r"going\s+concern"],
        "severity": EventSeverity.HIGH,
    },
    {
        "type": AltEventType.BUYBACK,
        "patterns": [r"share\s+repurchase\s+program", r"authoriz\w+\s+(?:a\s+)?(?:stock\s+)?buyback", r"repurchase\s+of\s+up\s+to"],
        "severity": EventSeverity.MEDIUM,
    },
    {
        "type": AltEventType.SECONDARY_OFFERING,
        "patterns": [r"secondary\s+offering", r"public\s+offering\s+of\s+(?:common\s+)?(?:stock|shares)", r"proposed\s+offering\s+of"],
        "severity": EventSeverity.MEDIUM,
    },
    {
        "type": AltEventType.DIVIDEND,
        "patterns": [r"declares?\s+(?:a\s+)?(?:quarterly\s+)?dividend", r"dividend\s+of\s+\$"],
        "severity": EventSeverity.LOW,
    },
    {
        "type": AltEventType.CREDIT_DOWNGRADE,
        "patterns": [r"downgrad\w+\s+(?:credit\s+)?rating", r"moody.?s\s+downgrades?", r"s&p\s+downgrades?"],
        "severity": EventSeverity.HIGH,
    },
    {
        "type": AltEventType.REGULATORY_ACTION,
        "patterns": [r"sec\s+(?:investigation|charges|enforcement)", r"regulatory\s+(?:action|scrutiny)", r"consent\s+decree"],
        "severity": EventSeverity.HIGH,
    },
    {
        "type": AltEventType.PATENT_APPROVAL,
        "patterns": [r"patent\s+(?:granted|approved|issued)", r"awarded\s+a\s+patent"],
        "severity": EventSeverity.LOW,
    },
    {
        "type": AltEventType.SUPPLY_CHAIN_DISRUPTION,
        "patterns": [r"supply\s+chain\s+(?:disruption|delay|shortage)", r"chip\s+shortage", r"production\s+halt"],
        "severity": EventSeverity.MEDIUM,
    },
    {
        "type": AltEventType.WEATHER_IMPACT,
        "patterns": [r"hurricane\s+(?:disrupts?|damages?|impacts?)", r"flood\w*\s+(?:damage|disruption)", r"winter\s+storm\s+impact"],
        "severity": EventSeverity.MEDIUM,
    },
    {
        "type": AltEventType.GEOPOLITICAL,
        "patterns": [r"sanctions?\s+(?:imposed|against)", r"trade\s+war", r"export\s+(?:ban|restriction)", r"tariffs?\s+on"],
        "severity": EventSeverity.MEDIUM,
    },
]

_COMPILED = [
    {"type": p["type"], "regexes": [re.compile(pat, re.IGNORECASE) for pat in p["patterns"]], "severity": p["severity"]}
    for p in _PATTERNS
]

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def detect_events(text: str, symbol: str = "UNKNOWN", source_doc_id: Optional[str] = None) -> List[AltEvent]:
    """Scan text for all recognised event patterns; returns one AltEvent per match group."""
    sentences = [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()] or [text.strip()]
    events: List[AltEvent] = []

    for entry in _COMPILED:
        matched_in_doc: List[str] = []
        best_sentence = ""
        for sentence in sentences:
            for rx in entry["regexes"]:
                if rx.search(sentence):
                    matched_in_doc.append(rx.pattern)
                    if not best_sentence:
                        best_sentence = sentence
        if not matched_in_doc:
            continue
        confidence = min(1.0, 0.5 + 0.15 * len(set(matched_in_doc)))
        events.append(AltEvent(
            event_type=entry["type"],
            symbol=symbol.upper(),
            confidence=round(confidence, 4),
            severity=entry["severity"],
            snippet=best_sentence[:280],
            source_doc_id=source_doc_id,
            matched_patterns=sorted(set(matched_in_doc)),
        ))
    return events


def detect_events_batch(documents: List[Dict[str, str]]) -> Dict[str, List[AltEvent]]:
    """documents: list of {"doc_id":..., "symbol":..., "text":...}. Returns symbol -> events."""
    results: Dict[str, List[AltEvent]] = {}
    for doc in documents:
        symbol = doc.get("symbol", "UNKNOWN").upper()
        events = detect_events(doc.get("text", ""), symbol=symbol, source_doc_id=doc.get("doc_id"))
        results.setdefault(symbol, []).extend(events)
    return results


def event_density(events: List[AltEvent], window_doc_count: int) -> float:
    """Events per document, normalised to [0, 1] assuming <=5 events/doc is saturating."""
    if window_doc_count <= 0:
        return 0.0
    rate = len(events) / window_doc_count
    return round(min(1.0, rate / 5.0), 4)
