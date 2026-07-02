"""M9 Phase 9 — Observability: structured logs, traces, slow queries, error aggregation."""
from fastapi import APIRouter, Query
from services.structured_logging import slow_query_tracker, error_aggregator, tracer

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/slow-queries")
def slow_queries(limit: int = Query(20, le=100)):
    return {"slow_queries": slow_query_tracker.get_slow_ops(limit), "stats": slow_query_tracker.stats()}


@router.get("/errors")
def error_summary():
    return error_aggregator.summary()


@router.get("/errors/{error_type}")
def error_detail(error_type: str, limit: int = Query(10, le=50)):
    return {"error_type": error_type, "recent": error_aggregator.get_recent(error_type, limit)}


@router.get("/traces")
def recent_traces(limit: int = Query(50, le=200)):
    return {"spans": tracer.recent_spans(limit)}
