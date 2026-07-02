"""M15 Phase 12 — Event Search Engine.

Full-text search over corporate and macro events with metadata filters,
relevance scoring, and faceted results.
Pure Python, in-memory, deterministic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from services.event_engine import CorporateEvent, CorporateEventType, EventImportance
from services.macro_event_engine import MacroEvent, MacroEventType


# ---------------------------------------------------------------------------
# Query dataclass
# ---------------------------------------------------------------------------

@dataclass
class EventSearchQuery:
    """Parameters for an event search."""

    query: Optional[str] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    importance: Optional[List[str]] = None
    since: Optional[float] = None
    until: Optional[float] = None
    kind: Optional[str] = None  # "corporate" | "macro" | None (both)
    limit: int = 20


# ---------------------------------------------------------------------------
# SearchHit dataclass
# ---------------------------------------------------------------------------

@dataclass
class EventSearchHit:
    """A single search result with relevance score."""

    event_id: str
    kind: str
    score: float
    event_data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "score": self.score,
            "event_data": self.event_data,
        }


# ---------------------------------------------------------------------------
# Relevance scorer
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _tf_score(query_tokens: List[str], document_text: str) -> float:
    """Term frequency score for query tokens in document text."""
    if not query_tokens:
        return 0.0
    doc_tokens = _tokenize(document_text)
    if not doc_tokens:
        return 0.0
    freq: Dict[str, int] = {}
    for t in doc_tokens:
        freq[t] = freq.get(t, 0) + 1
    score = 0.0
    for qt in query_tokens:
        score += freq.get(qt, 0) / len(doc_tokens)
    return score / len(query_tokens)


def _importance_boost(importance: str) -> float:
    return {"critical": 0.4, "high": 0.25, "medium": 0.1, "low": 0.0}.get(importance, 0.0)


# ---------------------------------------------------------------------------
# EventSearchEngine
# ---------------------------------------------------------------------------

class EventSearchEngine:
    """Relevance-ranked search engine for corporate and macro events."""

    def _corp_text(self, ev: CorporateEvent) -> str:
        return " ".join([
            ev.ticker, ev.company, ev.sector, ev.industry,
            ev.event_type.value, ev.description,
            " ".join(ev.tags),
        ])

    def _macro_text(self, ev: MacroEvent) -> str:
        return " ".join([
            ev.event_type.value, ev.country, ev.description,
        ])

    def _matches_corporate(self, ev: CorporateEvent, q: EventSearchQuery) -> bool:
        if q.tickers and ev.ticker.upper() not in {t.upper() for t in q.tickers}:
            return False
        if q.sectors and ev.sector.lower() not in {s.lower() for s in q.sectors}:
            return False
        if q.countries and ev.country.upper() not in {c.upper() for c in q.countries}:
            return False
        if q.event_types and ev.event_type.value not in q.event_types:
            return False
        if q.importance and ev.importance.value not in q.importance:
            return False
        if q.since is not None and ev.timestamp < q.since:
            return False
        if q.until is not None and ev.timestamp > q.until:
            return False
        return True

    def _matches_macro(self, ev: MacroEvent, q: EventSearchQuery) -> bool:
        if q.countries and ev.country.upper() not in {c.upper() for c in q.countries}:
            return False
        if q.event_types and ev.event_type.value not in q.event_types:
            return False
        if q.importance and ev.importance.value not in q.importance:
            return False
        if q.since is not None and ev.timestamp < q.since:
            return False
        if q.until is not None and ev.timestamp > q.until:
            return False
        return True

    def search(
        self,
        query: EventSearchQuery,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
    ) -> List[EventSearchHit]:
        """Execute a search and return relevance-ranked hits.

        Args:
            query: EventSearchQuery with filters and optional text.
            corporate_events: Pool of corporate events to search.
            macro_events: Pool of macro events to search.

        Returns:
            List of EventSearchHit sorted by score descending.
        """
        q_tokens = _tokenize(query.query or "")
        hits: List[EventSearchHit] = []

        if query.kind in (None, "corporate"):
            for ev in corporate_events:
                if not self._matches_corporate(ev, query):
                    continue
                text = self._corp_text(ev)
                tf = _tf_score(q_tokens, text) if q_tokens else 0.5
                boost = _importance_boost(ev.importance.value)
                score = round(tf * 0.7 + boost + ev.confidence * 0.1, 6)
                hits.append(EventSearchHit(
                    event_id=ev.id,
                    kind="corporate",
                    score=score,
                    event_data=ev.to_dict(),
                ))

        if query.kind in (None, "macro"):
            for ev in macro_events:
                if not self._matches_macro(ev, query):
                    continue
                text = self._macro_text(ev)
                tf = _tf_score(q_tokens, text) if q_tokens else 0.5
                boost = _importance_boost(ev.importance.value)
                score = round(tf * 0.7 + boost + 0.1, 6)
                hits.append(EventSearchHit(
                    event_id=ev.id,
                    kind="macro",
                    score=score,
                    event_data=ev.to_dict(),
                ))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:query.limit]

    def facets(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
    ) -> Dict[str, Any]:
        """Return facet counts for filtering UI."""
        sectors: Dict[str, int] = {}
        countries: Dict[str, int] = {}
        event_types: Dict[str, int] = {}
        importances: Dict[str, int] = {}

        for ev in corporate_events:
            sectors[ev.sector] = sectors.get(ev.sector, 0) + 1
            countries[ev.country] = countries.get(ev.country, 0) + 1
            event_types[ev.event_type.value] = event_types.get(ev.event_type.value, 0) + 1
            importances[ev.importance.value] = importances.get(ev.importance.value, 0) + 1

        for ev in macro_events:
            countries[ev.country] = countries.get(ev.country, 0) + 1
            event_types[ev.event_type.value] = event_types.get(ev.event_type.value, 0) + 1
            importances[ev.importance.value] = importances.get(ev.importance.value, 0) + 1

        return {
            "sectors": dict(sorted(sectors.items(), key=lambda x: x[1], reverse=True)),
            "countries": dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)),
            "event_types": dict(sorted(event_types.items(), key=lambda x: x[1], reverse=True)),
            "importance": dict(sorted(importances.items(), key=lambda x: x[1], reverse=True)),
        }

    def autocomplete(
        self,
        prefix: str,
        corporate_events: List[CorporateEvent],
    ) -> List[str]:
        """Return ticker/company suggestions matching a prefix."""
        prefix_lower = prefix.lower()
        suggestions: List[str] = []
        seen: set = set()
        for ev in corporate_events:
            for candidate in (ev.ticker, ev.company):
                if candidate.lower().startswith(prefix_lower) and candidate not in seen:
                    suggestions.append(candidate)
                    seen.add(candidate)
        return sorted(suggestions)[:10]
