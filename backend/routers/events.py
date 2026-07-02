"""M15 Phase 13 — Event Intelligence API Router.

25 endpoints under /events prefix.
Pure in-memory services, no DB, no network dependencies.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from schemas.events import (
    AddCorporateEventRequest,
    AddMacroEventRequest,
    CalendarRequest,
    CatalystRequest,
    ClusterRequest,
    EventFilterQuery,
    EventImpactRequest,
    EventSearchRequest,
    EventStudyRequest,
    IntelligenceRequest,
    ReportRequest,
    TimelineRequest,
)
from services.event_engine import (
    CorporateEventEngine,
    CorporateEventType,
    EventImportance,
    EventSeverity,
    get_corporate_event_engine,
)
from services.macro_event_engine import (
    MacroEventEngine,
    MacroEventType,
    get_macro_event_engine,
)
from services.event_study import EventStudy, EventWindow
from services.event_impact import EventImpactEngine
from services.market_catalyst import MarketCatalystEngine, CatalystDirection
from services.event_intelligence import EventIntelligenceEngine
from services.event_clustering import EventClusteringEngine
from services.market_intelligence_score import MarketIntelligenceScorer
from services.event_reports import EventReportGenerator, ReportType
from services.event_calendar import EventCalendar, TimelineGrouping as CalGrouping
from services.event_timeline import EventTimeline, TimelineFilter, TimelineView, TimelineGrouping
from services.event_search import EventSearchEngine, EventSearchQuery


router = APIRouter(prefix="/events", tags=["Event Intelligence"])

# ---------------------------------------------------------------------------
# Service singletons
# ---------------------------------------------------------------------------

_event_study = EventStudy()
_impact_engine = EventImpactEngine()
_catalyst_engine = MarketCatalystEngine()
_intelligence_engine = EventIntelligenceEngine()
_clustering_engine = EventClusteringEngine()
_scorer = MarketIntelligenceScorer()
_report_gen = EventReportGenerator()
_calendar = EventCalendar()
_timeline_engine = EventTimeline()
_search_engine = EventSearchEngine()


def _corp_engine() -> CorporateEventEngine:
    return get_corporate_event_engine()


def _macro_engine() -> MacroEventEngine:
    return get_macro_event_engine()


def _parse_corp_type(value: str) -> CorporateEventType:
    try:
        return CorporateEventType(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown corporate event type: {value!r}")


def _parse_macro_type(value: str) -> MacroEventType:
    try:
        return MacroEventType(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown macro event type: {value!r}")


def _parse_importance(value: Optional[str]) -> Optional[EventImportance]:
    if value is None:
        return None
    try:
        return EventImportance(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown importance: {value!r}")


def _parse_severity(value: Optional[str]) -> Optional[EventSeverity]:
    if value is None:
        return None
    try:
        return EventSeverity(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown severity: {value!r}")


def _parse_grouping(value: str) -> TimelineGrouping:
    try:
        return TimelineGrouping(value)
    except ValueError:
        return TimelineGrouping.DAY


def _parse_view(value: str) -> TimelineView:
    try:
        return TimelineView(value)
    except ValueError:
        return TimelineView.MARKET


# ---------------------------------------------------------------------------
# Corporate events
# ---------------------------------------------------------------------------

@router.get("/company")
def list_corporate_events(
    ticker: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    importance: Optional[str] = Query(None),
    since: Optional[float] = Query(None),
    until: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """List corporate events with optional filters."""
    eng = _corp_engine()
    et = _parse_corp_type(event_type) if event_type else None
    imp = _parse_importance(importance)
    events = eng.filter(
        ticker=ticker, sector=sector, country=country,
        event_type=et, importance=imp, since=since, until=until,
    )
    return [e.to_dict() for e in events[:limit]]


@router.post("/company")
def add_corporate_event(req: AddCorporateEventRequest) -> Dict[str, Any]:
    """Add a new corporate event."""
    eng = _corp_engine()
    et = _parse_corp_type(req.event_type)
    imp = _parse_importance(req.importance)
    sev = _parse_severity(req.severity)
    ev = eng.add_event(
        ticker=req.ticker,
        company=req.company,
        event_type=et,
        description=req.description,
        sector=req.sector,
        industry=req.industry,
        country=req.country,
        confidence=req.confidence,
        source=req.source,
        timestamp=req.timestamp,
        importance=imp,
        severity=sev,
        metadata=req.metadata,
        tags=req.tags,
    )
    return ev.to_dict()


@router.get("/company/{event_id}")
def get_corporate_event(event_id: str) -> Dict[str, Any]:
    """Get a specific corporate event by ID."""
    ev = _corp_engine().get_by_id(event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id!r} not found")
    return ev.to_dict()


# ---------------------------------------------------------------------------
# Macro events
# ---------------------------------------------------------------------------

@router.get("/macro")
def list_macro_events(
    event_type: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    importance: Optional[str] = Query(None),
    since: Optional[float] = Query(None),
    until: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """List macro events with optional filters."""
    eng = _macro_engine()
    et = _parse_macro_type(event_type) if event_type else None
    imp = _parse_importance(importance)
    events = eng.filter(event_type=et, country=country, importance=imp, since=since, until=until)
    return [e.to_dict() for e in events[:limit]]


@router.post("/macro")
def add_macro_event(req: AddMacroEventRequest) -> Dict[str, Any]:
    """Add a new macro event."""
    eng = _macro_engine()
    et = _parse_macro_type(req.event_type)
    imp = _parse_importance(req.importance)
    ev = eng.add_event(
        event_type=et,
        description=req.description,
        country=req.country,
        actual=req.actual,
        forecast=req.forecast,
        previous=req.previous,
        historical_values=req.historical_values,
        timestamp=req.timestamp,
        importance=imp,
        metadata=req.metadata,
    )
    return ev.to_dict()


@router.get("/macro/{event_id}")
def get_macro_event(event_id: str) -> Dict[str, Any]:
    """Get a specific macro event by ID."""
    ev = _macro_engine().get_by_id(event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Macro event {event_id!r} not found")
    return ev.to_dict()


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.get("/statistics")
def event_statistics() -> Dict[str, Any]:
    """Aggregate statistics across corporate and macro events."""
    corp_stats = _corp_engine().statistics()
    macro_stats = _macro_engine().statistics()
    return {
        "corporate": corp_stats,
        "macro": macro_stats,
        "total_events": corp_stats["total"] + macro_stats["total"],
    }


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

@router.post("/timeline")
def event_timeline(req: TimelineRequest) -> Dict[str, Any]:
    """Build grouped timeline view."""
    tl_filter = TimelineFilter(
        since=req.since,
        until=req.until,
        tickers=req.tickers,
        sectors=req.sectors,
        countries=req.countries,
        importance=req.importance,
        event_types=req.event_types,
        view=_parse_view(req.view),
        grouping=_parse_grouping(req.grouping),
    )
    corp_events = _corp_engine().all_events()
    macro_events = _macro_engine().all_events()
    groups = _timeline_engine.build(corp_events, macro_events, tl_filter)
    total = sum(g.total_count for g in groups)
    return {"groups": [g.to_dict() for g in groups], "total_events": total}


@router.get("/upcoming")
def upcoming_events(
    since: Optional[float] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    importance: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """Return upcoming events after a timestamp."""
    since_ts = since if since is not None else time.time()
    imp_filter = [importance] if importance else None
    return _calendar.upcoming(
        _corp_engine().all_events(),
        _macro_engine().all_events(),
        since=since_ts,
        limit=limit,
        importance=imp_filter,
    )


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

@router.post("/calendar")
def event_calendar_query(req: CalendarRequest) -> Dict[str, Any]:
    """Query the event calendar in a specific view."""
    corp_events = _corp_engine().all_events()
    macro_events = _macro_engine().all_events()

    if req.view == "agenda":
        entries = _calendar.agenda_view(
            corp_events, macro_events,
            since=req.since, until=req.until,
            importance=req.importance, limit=req.limit,
        )
        return {"view": "agenda", "entries": entries, "total": len(entries)}

    if req.view == "day":
        day_ts = req.since or time.time()
        return _calendar.day_view(corp_events, macro_events, day_ts)

    if req.view == "week":
        week_ts = req.since or time.time()
        days = _calendar.week_view(corp_events, macro_events, week_ts)
        return {"view": "week", "days": days}

    if req.view == "month":
        month_ts = req.since or time.time()
        weeks = _calendar.month_view(corp_events, macro_events, month_ts)
        return {"view": "month", "weeks": weeks}

    if req.view == "heatmap":
        grouping = _parse_grouping(req.grouping)
        cal_grouping = CalGrouping(grouping.value)
        data = _calendar.heatmap(corp_events, macro_events, cal_grouping)
        return {"view": "heatmap", "data": data}

    if req.view in ("upcoming", "past"):
        if req.view == "upcoming":
            entries = _calendar.upcoming(corp_events, macro_events, since=req.since or time.time(), limit=req.limit)
        else:
            entries = _calendar.past(corp_events, macro_events, until=req.until or time.time(), limit=req.limit)
        return {"view": req.view, "entries": entries}

    return _calendar.statistics(corp_events, macro_events)


@router.get("/heatmap")
def heatmap(
    grouping: str = Query("day"),
) -> List[Dict[str, Any]]:
    """Return event density heatmap data."""
    corp_events = _corp_engine().all_events()
    macro_events = _macro_engine().all_events()
    g = _parse_grouping(grouping)
    cal_grouping = CalGrouping(g.value)
    return _calendar.heatmap(corp_events, macro_events, cal_grouping)


# ---------------------------------------------------------------------------
# Event study
# ---------------------------------------------------------------------------

@router.post("/study")
def run_event_study(req: EventStudyRequest) -> Dict[str, Any]:
    """Run classical event study methodology."""
    windows = None
    if req.windows:
        windows = []
        for w in req.windows:
            try:
                windows.append(EventWindow(w))
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Unknown window: {w!r}")

    results = _event_study.run_multi_window(
        event_id=req.event_id,
        tickers=req.tickers,
        actual_returns_map=req.actual_returns,
        expected_returns_map=req.expected_returns,
        windows=windows,
    )
    return {
        "event_id": req.event_id,
        "results": {k: v.to_dict() for k, v in results.items()},
    }


# ---------------------------------------------------------------------------
# Event impact
# ---------------------------------------------------------------------------

@router.post("/impact")
def compute_event_impact(req: EventImpactRequest) -> Dict[str, Any]:
    """Compute event impact metrics for a security."""
    impact = _impact_engine.compute(
        event_id=req.event_id,
        ticker=req.ticker,
        pre_returns=req.pre_returns,
        post_returns=req.post_returns,
        market_returns=req.market_returns,
        pre_volumes=req.pre_volumes,
        post_volumes=req.post_volumes,
        gap_return=req.gap_return,
        expected_daily_return=req.expected_daily_return,
        metadata=req.metadata,
    )
    return impact.to_dict()


# ---------------------------------------------------------------------------
# Catalysts
# ---------------------------------------------------------------------------

@router.get("/catalysts")
def list_catalysts(
    direction: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Return top catalysts classified from all corporate events."""
    corp_events = _corp_engine().all_events()
    dir_filter = None
    if direction:
        try:
            dir_filter = CatalystDirection(direction)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown direction: {direction!r}")
    scores = _catalyst_engine.top_catalysts(corp_events, n=limit, direction=dir_filter)
    return [s.to_dict() for s in scores]


@router.post("/catalysts/score")
def score_event_catalyst(req: CatalystRequest) -> Dict[str, Any]:
    """Score a specific corporate event as a catalyst."""
    ev = _corp_engine().get_by_id(req.event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Event {req.event_id!r} not found")
    score = _catalyst_engine.classify(ev)
    return score.to_dict()


# ---------------------------------------------------------------------------
# AI intelligence
# ---------------------------------------------------------------------------

@router.post("/intelligence")
def event_intelligence(req: IntelligenceRequest) -> Dict[str, Any]:
    """Generate AI event intelligence for a corporate event."""
    ev = _corp_engine().get_by_id(req.event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Event {req.event_id!r} not found")
    intel = _intelligence_engine.analyse_corporate(ev)
    return intel.to_dict()


@router.post("/intelligence/macro")
def macro_event_intelligence(req: IntelligenceRequest) -> Dict[str, Any]:
    """Generate AI intelligence for a macro event."""
    ev = _macro_engine().get_by_id(req.event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Macro event {req.event_id!r} not found")
    intel = _intelligence_engine.analyse_macro(ev)
    return intel.to_dict()


# ---------------------------------------------------------------------------
# Market intelligence score
# ---------------------------------------------------------------------------

@router.get("/intelligence/score/{event_id}")
def intelligence_score(event_id: str) -> Dict[str, Any]:
    """Compute market intelligence score for a corporate event."""
    ev = _corp_engine().get_by_id(event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id!r} not found")
    cat = _catalyst_engine.classify(ev)
    score = _scorer.score_corporate(ev, cat)
    return score.to_dict()


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

@router.get("/clusters")
def event_clusters(
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    """Return event cluster distribution."""
    corp_events = _corp_engine().all_events()[:limit]
    dist = _clustering_engine.cluster_distribution(corp_events)
    groups = _clustering_engine.events_by_cluster(corp_events)
    return {"distribution": dist, "groups": groups}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.post("/search")
def search_events(req: EventSearchRequest) -> Dict[str, Any]:
    """Full-text search over corporate and macro events."""
    query = EventSearchQuery(
        query=req.query,
        tickers=req.tickers,
        sectors=req.sectors,
        countries=req.countries,
        event_types=req.event_types,
        importance=req.importance,
        since=req.since,
        until=req.until,
        kind=req.kind,
        limit=req.limit,
    )
    hits = _search_engine.search(query, _corp_engine().all_events(), _macro_engine().all_events())
    return {"hits": [h.to_dict() for h in hits], "total": len(hits)}


@router.get("/search/facets")
def search_facets() -> Dict[str, Any]:
    """Return search facets for the filtering UI."""
    return _search_engine.facets(_corp_engine().all_events(), _macro_engine().all_events())


@router.get("/search/autocomplete")
def search_autocomplete(q: str = Query(..., min_length=1)) -> List[str]:
    """Autocomplete ticker and company names."""
    return _search_engine.autocomplete(q, _corp_engine().all_events())


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@router.post("/report")
def generate_report(req: ReportRequest) -> Dict[str, Any]:
    """Generate an institutional event intelligence report."""
    corp_events = _corp_engine().all_events()
    macro_events = _macro_engine().all_events()

    # Apply time filter
    if req.since is not None:
        corp_events = [e for e in corp_events if e.timestamp >= req.since]
        macro_events = [e for e in macro_events if e.timestamp >= req.since]
    if req.until is not None:
        corp_events = [e for e in corp_events if e.timestamp <= req.until]
        macro_events = [e for e in macro_events if e.timestamp <= req.until]

    try:
        rt = ReportType(req.report_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown report type: {req.report_type!r}")

    if rt in (ReportType.DAILY, ReportType.WEEKLY, ReportType.MONTHLY):
        report = _report_gen.generate_daily(corp_events, macro_events)
    elif rt == ReportType.COMPANY:
        if not req.ticker:
            raise HTTPException(status_code=422, detail="ticker is required for company reports")
        catalysts = _catalyst_engine.classify_batch(corp_events)
        report = _report_gen.generate_company(req.ticker, corp_events, catalysts)
    elif rt == ReportType.SECTOR:
        if not req.sector:
            raise HTTPException(status_code=422, detail="sector is required for sector reports")
        report = _report_gen.generate_sector(req.sector, corp_events)
    elif rt == ReportType.MACRO:
        report = _report_gen.generate_macro(macro_events)
    elif rt == ReportType.CATALYST:
        catalysts = _catalyst_engine.classify_batch(corp_events)
        report = _report_gen.generate_catalyst(catalysts, corp_events)
    else:
        report = _report_gen.generate_daily(corp_events, macro_events)

    return report.to_dict()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.get("/export")
def export_events(
    kind: str = Query("corporate"),
    since: Optional[float] = Query(None),
    until: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """Export events as structured JSON."""
    if kind == "corporate":
        events = _corp_engine().filter(since=since, until=until)[:limit]
        return {"kind": "corporate", "count": len(events), "events": [e.to_dict() for e in events]}
    if kind == "macro":
        events = _macro_engine().filter(since=since, until=until)[:limit]
        return {"kind": "macro", "count": len(events), "events": [e.to_dict() for e in events]}
    raise HTTPException(status_code=422, detail="kind must be 'corporate' or 'macro'")
