"""M15 Phase 11 — Event Calendar Engine.

Bloomberg-style event calendar with Agenda/Day/Week/Month/Heatmap/Timeline
views, upcoming/past filters, and full event query support.
Pure Python, in-memory, deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from services.event_engine import CorporateEvent, EventImportance
from services.macro_event_engine import MacroEvent
from services.event_timeline import (
    TimelineGrouping,
    _floor_to_period,
    _period_label,
    _period_end,
)


# ---------------------------------------------------------------------------
# Calendar view enum
# ---------------------------------------------------------------------------

class CalendarView(str, Enum):
    AGENDA = "agenda"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    HEATMAP = "heatmap"
    TIMELINE = "timeline"
    UPCOMING = "upcoming"
    PAST = "past"


# ---------------------------------------------------------------------------
# CalendarEntry dataclass
# ---------------------------------------------------------------------------

@dataclass
class CalendarEntry:
    """A single entry in the event calendar."""

    entry_id: str
    kind: str  # "corporate" or "macro"
    timestamp: float
    date_label: str
    time_label: str
    title: str
    ticker: Optional[str]
    importance: str
    event_type: str
    country: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind,
            "timestamp": self.timestamp,
            "date_label": self.date_label,
            "time_label": self.time_label,
            "title": self.title,
            "ticker": self.ticker,
            "importance": self.importance,
            "event_type": self.event_type,
            "country": self.country,
            "description": self.description,
            "metadata": self.metadata,
        }


def _from_corporate(ev: CorporateEvent) -> CalendarEntry:
    dt = datetime.fromtimestamp(ev.timestamp, tz=timezone.utc)
    return CalendarEntry(
        entry_id=ev.id,
        kind="corporate",
        timestamp=ev.timestamp,
        date_label=dt.strftime("%Y-%m-%d"),
        time_label=dt.strftime("%H:%M"),
        title=f"{ev.ticker} — {ev.event_type.value.replace('_', ' ').title()}",
        ticker=ev.ticker,
        importance=ev.importance.value,
        event_type=ev.event_type.value,
        country=ev.country,
        description=ev.description,
        metadata={
            "company": ev.company,
            "sector": ev.sector,
            "severity": ev.severity.value,
            "confidence": ev.confidence,
            "tags": ev.tags,
        },
    )


def _from_macro(ev: MacroEvent) -> CalendarEntry:
    dt = datetime.fromtimestamp(ev.timestamp, tz=timezone.utc)
    return CalendarEntry(
        entry_id=ev.id,
        kind="macro",
        timestamp=ev.timestamp,
        date_label=dt.strftime("%Y-%m-%d"),
        time_label=dt.strftime("%H:%M"),
        title=f"{ev.event_type.value.upper()} ({ev.country})",
        ticker=None,
        importance=ev.importance.value,
        event_type=ev.event_type.value,
        country=ev.country,
        description=ev.description,
        metadata={
            "actual": ev.actual,
            "forecast": ev.forecast,
            "surprise_pct": ev.surprise_pct,
            "volatility_expectation": ev.volatility_expectation,
        },
    )


# ---------------------------------------------------------------------------
# EventCalendar
# ---------------------------------------------------------------------------

class EventCalendar:
    """Institutional Bloomberg-style event calendar."""

    def _all_entries(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
    ) -> List[CalendarEntry]:
        entries = [_from_corporate(e) for e in corporate_events]
        entries += [_from_macro(e) for e in macro_events]
        return sorted(entries, key=lambda e: e.timestamp)

    def _apply_filters(
        self,
        entries: List[CalendarEntry],
        since: Optional[float] = None,
        until: Optional[float] = None,
        importance: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
        tickers: Optional[List[str]] = None,
        countries: Optional[List[str]] = None,
        kind: Optional[str] = None,
    ) -> List[CalendarEntry]:
        result = entries
        if since is not None:
            result = [e for e in result if e.timestamp >= since]
        if until is not None:
            result = [e for e in result if e.timestamp <= until]
        if importance:
            imp_set = set(importance)
            result = [e for e in result if e.importance in imp_set]
        if event_types:
            et_set = set(event_types)
            result = [e for e in result if e.event_type in et_set]
        if tickers:
            t_set = {t.upper() for t in tickers}
            result = [e for e in result if e.ticker and e.ticker.upper() in t_set]
        if countries:
            c_set = {c.upper() for c in countries}
            result = [e for e in result if e.country.upper() in c_set]
        if kind:
            result = [e for e in result if e.kind == kind]
        return result

    def agenda_view(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        since: Optional[float] = None,
        until: Optional[float] = None,
        importance: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Ordered agenda list of entries."""
        entries = self._all_entries(corporate_events, macro_events)
        entries = self._apply_filters(entries, since=since, until=until, importance=importance)
        return [e.to_dict() for e in entries[:limit]]

    def day_view(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        day_ts: float,
    ) -> Dict[str, Any]:
        """All events on a specific day."""
        start = _floor_to_period(day_ts, TimelineGrouping.DAY)
        end = start + 86400
        entries = self._all_entries(corporate_events, macro_events)
        day_entries = self._apply_filters(entries, since=start, until=end)
        dt = datetime.fromtimestamp(start, tz=timezone.utc)
        return {
            "date": dt.strftime("%Y-%m-%d"),
            "total_count": len(day_entries),
            "corporate_count": sum(1 for e in day_entries if e.kind == "corporate"),
            "macro_count": sum(1 for e in day_entries if e.kind == "macro"),
            "entries": [e.to_dict() for e in day_entries],
        }

    def week_view(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        week_ts: float,
    ) -> List[Dict[str, Any]]:
        """Per-day buckets for a calendar week."""
        week_start = _floor_to_period(week_ts, TimelineGrouping.WEEK)
        result = []
        for i in range(7):
            day_start = week_start + i * 86400
            result.append(self.day_view(corporate_events, macro_events, day_start))
        return result

    def month_view(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        month_ts: float,
    ) -> List[Dict[str, Any]]:
        """Per-week buckets for a calendar month."""
        month_start = _floor_to_period(month_ts, TimelineGrouping.MONTH)
        month_end = _period_end(month_start, TimelineGrouping.MONTH)
        result = []
        current = month_start
        while current < month_end:
            week_end = min(current + 7 * 86400, month_end)
            entries = self._all_entries(corporate_events, macro_events)
            week_entries = self._apply_filters(entries, since=current, until=week_end)
            dt_start = datetime.fromtimestamp(current, tz=timezone.utc)
            dt_end = datetime.fromtimestamp(week_end, tz=timezone.utc)
            result.append({
                "week_label": f"{dt_start.strftime('%Y-%m-%d')} to {dt_end.strftime('%Y-%m-%d')}",
                "start": current,
                "end": week_end,
                "total_count": len(week_entries),
                "entries": [e.to_dict() for e in week_entries],
            })
            current += 7 * 86400
        return result

    def heatmap(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        grouping: TimelineGrouping = TimelineGrouping.DAY,
    ) -> List[Dict[str, Any]]:
        """Density heatmap data per period."""
        all_entries = self._all_entries(corporate_events, macro_events)
        grouped: Dict[float, Dict[str, Any]] = {}
        for entry in all_entries:
            ps = _floor_to_period(entry.timestamp, grouping)
            if ps not in grouped:
                grouped[ps] = {
                    "label": _period_label(ps, grouping),
                    "period_start": ps,
                    "count": 0,
                    "corporate": 0,
                    "macro": 0,
                    "importance_critical": 0,
                    "importance_high": 0,
                }
            grouped[ps]["count"] += 1
            if entry.kind == "corporate":
                grouped[ps]["corporate"] += 1
            else:
                grouped[ps]["macro"] += 1
            if entry.importance == "critical":
                grouped[ps]["importance_critical"] += 1
            elif entry.importance == "high":
                grouped[ps]["importance_high"] += 1
        return sorted(grouped.values(), key=lambda x: x["period_start"])

    def upcoming(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        since: float,
        limit: int = 20,
        importance: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Next events after a timestamp."""
        entries = self._all_entries(corporate_events, macro_events)
        entries = self._apply_filters(entries, since=since, importance=importance)
        return [e.to_dict() for e in entries[:limit]]

    def past(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        until: float,
        limit: int = 20,
        importance: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Most recent events before a timestamp."""
        entries = self._all_entries(corporate_events, macro_events)
        entries = self._apply_filters(entries, until=until, importance=importance)
        return [e.to_dict() for e in sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]]

    def statistics(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
    ) -> Dict[str, Any]:
        """Summary statistics for the calendar."""
        all_entries = self._all_entries(corporate_events, macro_events)
        imp_dist: Dict[str, int] = {}
        type_dist: Dict[str, int] = {}
        country_dist: Dict[str, int] = {}
        for e in all_entries:
            imp_dist[e.importance] = imp_dist.get(e.importance, 0) + 1
            type_dist[e.event_type] = type_dist.get(e.event_type, 0) + 1
            country_dist[e.country] = country_dist.get(e.country, 0) + 1
        return {
            "total_entries": len(all_entries),
            "corporate_count": sum(1 for e in all_entries if e.kind == "corporate"),
            "macro_count": sum(1 for e in all_entries if e.kind == "macro"),
            "by_importance": imp_dist,
            "by_event_type": type_dist,
            "by_country": dict(sorted(country_dist.items(), key=lambda x: x[1], reverse=True)[:10]),
        }
