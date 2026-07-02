"""M15 Phase 3 — Event Timeline Engine.

Institutional timeline with Company/Sector/Country/Market/Portfolio views,
multi-dimension filtering, and Day/Week/Month/Quarter/Year grouping.
Pure Python, in-memory, fully deterministic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from services.event_engine import CorporateEvent, CorporateEventType, EventImportance
from services.macro_event_engine import MacroEvent, MacroEventType


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TimelineView(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    COUNTRY = "country"
    MARKET = "market"
    PORTFOLIO = "portfolio"


class TimelineGrouping(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


# ---------------------------------------------------------------------------
# AnyEvent union type
# ---------------------------------------------------------------------------

AnyEvent = Union[CorporateEvent, MacroEvent]


# ---------------------------------------------------------------------------
# TimelineFilter dataclass
# ---------------------------------------------------------------------------

@dataclass
class TimelineFilter:
    """Filter specification for timeline queries."""

    since: Optional[float] = None
    until: Optional[float] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    importance: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    view: TimelineView = TimelineView.MARKET
    grouping: TimelineGrouping = TimelineGrouping.DAY


# ---------------------------------------------------------------------------
# TimelineGroup dataclass
# ---------------------------------------------------------------------------

@dataclass
class TimelineGroup:
    """A temporal bucket of events."""

    label: str
    period_start: float
    period_end: float
    events: List[Dict[str, Any]] = field(default_factory=list)
    corporate_count: int = 0
    macro_count: int = 0
    total_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "events": self.events,
            "corporate_count": self.corporate_count,
            "macro_count": self.macro_count,
            "total_count": self.total_count,
        }


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

def _floor_to_period(ts: float, grouping: TimelineGrouping) -> float:
    """Return the start of the period containing ts."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    if grouping == TimelineGrouping.DAY:
        floored = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif grouping == TimelineGrouping.WEEK:
        floored = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif grouping == TimelineGrouping.MONTH:
        floored = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif grouping == TimelineGrouping.QUARTER:
        q_month = ((dt.month - 1) // 3) * 3 + 1
        floored = dt.replace(month=q_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # YEAR
        floored = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return floored.timestamp()


def _period_label(ts: float, grouping: TimelineGrouping) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    if grouping == TimelineGrouping.DAY:
        return dt.strftime("%Y-%m-%d")
    if grouping == TimelineGrouping.WEEK:
        return f"W{dt.isocalendar()[1]:02d}-{dt.year}"
    if grouping == TimelineGrouping.MONTH:
        return dt.strftime("%Y-%m")
    if grouping == TimelineGrouping.QUARTER:
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{q}"
    return str(dt.year)


def _period_end(period_start: float, grouping: TimelineGrouping) -> float:
    dt = datetime.fromtimestamp(period_start, tz=timezone.utc)
    if grouping == TimelineGrouping.DAY:
        end = dt + timedelta(days=1)
    elif grouping == TimelineGrouping.WEEK:
        end = dt + timedelta(weeks=1)
    elif grouping == TimelineGrouping.MONTH:
        if dt.month == 12:
            end = dt.replace(year=dt.year + 1, month=1)
        else:
            end = dt.replace(month=dt.month + 1)
    elif grouping == TimelineGrouping.QUARTER:
        months_ahead = 3
        new_month = dt.month + months_ahead
        new_year = dt.year + (new_month - 1) // 12
        new_month = (new_month - 1) % 12 + 1
        end = dt.replace(year=new_year, month=new_month)
    else:
        end = dt.replace(year=dt.year + 1)
    return end.timestamp()


# ---------------------------------------------------------------------------
# EventTimeline
# ---------------------------------------------------------------------------

class EventTimeline:
    """Build grouped timeline views from corporate and macro events."""

    def _matches_corporate(
        self, ev: CorporateEvent, f: TimelineFilter
    ) -> bool:
        if f.since is not None and ev.timestamp < f.since:
            return False
        if f.until is not None and ev.timestamp > f.until:
            return False
        if f.tickers and ev.ticker.upper() not in {t.upper() for t in f.tickers}:
            return False
        if f.sectors and ev.sector.lower() not in {s.lower() for s in f.sectors}:
            return False
        if f.countries and ev.country.upper() not in {c.upper() for c in f.countries}:
            return False
        if f.importance and ev.importance.value not in f.importance:
            return False
        if f.event_types and ev.event_type.value not in f.event_types:
            return False
        return True

    def _matches_macro(self, ev: MacroEvent, f: TimelineFilter) -> bool:
        if f.since is not None and ev.timestamp < f.since:
            return False
        if f.until is not None and ev.timestamp > f.until:
            return False
        if f.countries and ev.country.upper() not in {c.upper() for c in f.countries}:
            return False
        if f.importance and ev.importance.value not in f.importance:
            return False
        if f.event_types and ev.event_type.value not in f.event_types:
            return False
        return True

    def build(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        timeline_filter: TimelineFilter,
    ) -> List[TimelineGroup]:
        """Build grouped timeline from event lists.

        Args:
            corporate_events: List of corporate events.
            macro_events: List of macro events.
            timeline_filter: Filter and grouping specification.

        Returns:
            List of TimelineGroup sorted by period_start ascending.
        """
        grouped: Dict[float, TimelineGroup] = {}

        def _ensure_group(ts: float) -> TimelineGroup:
            period_start = _floor_to_period(ts, timeline_filter.grouping)
            if period_start not in grouped:
                grouped[period_start] = TimelineGroup(
                    label=_period_label(period_start, timeline_filter.grouping),
                    period_start=period_start,
                    period_end=_period_end(period_start, timeline_filter.grouping),
                )
            return grouped[period_start]

        for ev in corporate_events:
            if self._matches_corporate(ev, timeline_filter):
                grp = _ensure_group(ev.timestamp)
                grp.events.append({"kind": "corporate", **ev.to_dict()})
                grp.corporate_count += 1
                grp.total_count += 1

        for ev in macro_events:
            if self._matches_macro(ev, timeline_filter):
                grp = _ensure_group(ev.timestamp)
                grp.events.append({"kind": "macro", **ev.to_dict()})
                grp.macro_count += 1
                grp.total_count += 1

        return sorted(grouped.values(), key=lambda g: g.period_start)

    def heatmap_data(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        grouping: TimelineGrouping = TimelineGrouping.DAY,
    ) -> List[Dict[str, Any]]:
        """Return counts per period for heatmap visualization."""
        f = TimelineFilter(grouping=grouping)
        groups = self.build(corporate_events, macro_events, f)
        return [
            {
                "label": g.label,
                "period_start": g.period_start,
                "count": g.total_count,
                "corporate": g.corporate_count,
                "macro": g.macro_count,
            }
            for g in groups
        ]

    def upcoming(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        since: float,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return next `limit` events after `since`, sorted by timestamp."""
        all_evs: List[Dict[str, Any]] = []
        for ev in corporate_events:
            if ev.timestamp >= since:
                all_evs.append({"kind": "corporate", **ev.to_dict()})
        for ev in macro_events:
            if ev.timestamp >= since:
                all_evs.append({"kind": "macro", **ev.to_dict()})
        all_evs.sort(key=lambda e: e["timestamp"])
        return all_evs[:limit]
