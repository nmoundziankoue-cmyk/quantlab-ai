"""M9 Phase 1 — Provider health & stats API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from services.provider_health import get_health_router

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/health")
def provider_health():
    return get_health_router().health_summary()


@router.get("/stats")
def provider_stats():
    return {"providers": get_health_router().get_all_stats()}


@router.get("/stats/{name}")
def provider_stats_single(name: str):
    stats = get_health_router().get_provider_stats(name)
    if stats is None:
        raise HTTPException(404, f"Provider '{name}' not found")
    return stats


@router.get("/ranking")
def provider_ranking():
    all_stats = get_health_router().get_all_stats()
    ranked = sorted(all_stats, key=lambda s: (-s["health_score"], s["priority"]))
    return {"ranked": ranked}


@router.delete("/cache")
def invalidate_cache(ticker: str = Query(None, description="Ticker to invalidate, or all if omitted")):
    get_health_router().invalidate_cache(ticker)
    return {"invalidated": ticker or "all"}
