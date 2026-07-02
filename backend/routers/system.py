"""System health, metrics, and observability endpoints (M8)."""
from __future__ import annotations

import platform
import sys
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from services.cache import cache
from services.metrics import metrics
from services.rate_limiter import rate_limiter
from services.task_queue import task_queue
from middleware.rbac import require_role

router = APIRouter(prefix="/system", tags=["system"])

# Track start time for uptime calculation
_START_TIME = time.time()

# Simple in-process request counter (reset on restart)
_request_counts: Dict[str, int] = {}


def _increment_counter(key: str) -> None:
    _request_counts[key] = _request_counts.get(key, 0) + 1


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
def health_simple() -> Dict[str, Any]:
    """Lightweight liveness probe."""
    return {"status": "ok", "uptime_s": round(time.time() - _START_TIME, 1)}


@router.get("/health/detailed")
def health_detailed(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Deep health check for all components."""
    components: Dict[str, Dict] = {}

    # --- Database ---
    try:
        db.execute(text("SELECT 1"))
        components["database"] = {"status": "ok", "backend": "postgresql"}
    except Exception as exc:
        components["database"] = {"status": "error", "error": str(exc)}

    # --- Redis / Cache ---
    try:
        test_key = "__health_check__"
        cache.set(test_key, "ok", ttl=5)
        val = cache.get(test_key)
        cache.delete(test_key)
        components["cache"] = {
            "status": "ok" if val == "ok" else "degraded",
            "backend": cache.backend_name,
        }
    except Exception as exc:
        components["cache"] = {"status": "error", "error": str(exc)}

    # --- Task Queue ---
    try:
        stats = task_queue.stats()
        components["task_queue"] = {"status": "ok", **stats}
    except Exception as exc:
        components["task_queue"] = {"status": "error", "error": str(exc)}

    # --- Rate Limiter ---
    try:
        stats = rate_limiter.stats()
        components["rate_limiter"] = {"status": "ok", **stats}
    except Exception as exc:
        components["rate_limiter"] = {"status": "error", "error": str(exc)}

    overall = (
        "ok"
        if all(c.get("status") == "ok" for c in components.values())
        else "degraded"
    )

    return {
        "status": overall,
        "uptime_s": round(time.time() - _START_TIME, 1),
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "components": components,
    }


@router.get("/health/live")
def liveness() -> Dict[str, Any]:
    """Kubernetes liveness probe — always returns 200 if the process is up."""
    return {"alive": True}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Kubernetes readiness probe — checks DB connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Database not ready: {exc}")


# ---------------------------------------------------------------------------
# Prometheus-compatible metrics endpoint
# ---------------------------------------------------------------------------


@router.get("/metrics", response_class=None)
def prometheus_metrics(db: Session = Depends(get_db)):
    """Emit metrics in Prometheus text format (compatible with Prometheus scraper)."""
    from fastapi.responses import PlainTextResponse

    task_stats = task_queue.stats()
    rl_stats = rate_limiter.stats()

    # Task queue supplemental metrics
    extra_lines = [
        "# HELP apexquant_tasks_total Total background tasks in queue",
        "# TYPE apexquant_tasks_total gauge",
        f"apexquant_tasks_total {task_stats.get('total', 0)}",
        "",
        "# HELP apexquant_rate_limiter_buckets Active rate-limiter token buckets",
        "# TYPE apexquant_rate_limiter_buckets gauge",
        f"apexquant_rate_limiter_buckets {rl_stats.get('active_buckets', 0)}",
        "",
    ]
    for status_name, count in task_stats.get("by_status", {}).items():
        extra_lines.append(f'apexquant_tasks_by_status{{status="{status_name}"}} {count}')
    extra_lines.append("")

    body = metrics.to_prometheus() + "\n".join(extra_lines)
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")


@router.get("/metrics/json")
def metrics_json() -> Dict[str, Any]:
    """Metrics summary in JSON format (for dashboards)."""
    return {**metrics.to_dict(), "task_queue": task_queue.stats()}


# ---------------------------------------------------------------------------
# Task queue info
# ---------------------------------------------------------------------------


@router.get("/tasks")
def list_tasks(
    status: str = None,
    limit: int = 50,
) -> Dict[str, Any]:
    from services.task_queue import TaskStatus
    status_filter = TaskStatus(status) if status else None
    tasks = task_queue.list(status=status_filter, limit=limit)
    return {
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks),
        "stats": task_queue.stats(),
    }


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> Dict[str, Any]:
    task = task_queue.get(task_id)
    if task is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


# ---------------------------------------------------------------------------
# Rate limiter info
# ---------------------------------------------------------------------------


@router.get("/rate-limits")
def rate_limit_stats() -> Dict[str, Any]:
    return rate_limiter.stats()


# ---------------------------------------------------------------------------
# Build / version info
# ---------------------------------------------------------------------------


@router.get("/redis/health")
def redis_health() -> Dict[str, Any]:
    """Detailed Redis connectivity and stats."""
    info = cache.redis_info()
    if info is None:
        return {"connected": False, "reason": "no_redis_url_configured", "backend": cache.backend_name}
    return {**info, "backend": cache.backend_name}


@router.post("/cache/clear")
def clear_cache(
    prefix: Optional[str] = None,
    _payload: dict = Depends(require_role("ADMIN")),
) -> Dict[str, Any]:
    """Admin-only: clear all cached entries or entries matching a prefix."""
    if prefix:
        cache.clear_prefix(prefix)
        return {"cleared": True, "prefix": prefix}
    cache.ns_clear()
    return {"cleared": True, "scope": "all_namespaced_keys"}


@router.get("/info")
def system_info() -> Dict[str, Any]:
    return {
        "app": "ApexQuant Institutional Quantitative Research OS",
        "version": "8.0.0",
        "milestone": "M8",
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
        "uptime_s": round(time.time() - _START_TIME, 1),
    }
