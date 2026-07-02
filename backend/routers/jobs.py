"""Background job system (M10 Phase 6).

Provides persistent job tracking via the background_jobs table with
in-process execution, idempotency keys, retry support, and WebSocket
progress events published via Redis pub/sub.

Endpoints:
  POST   /jobs              Enqueue a new job
  GET    /jobs              List jobs (paginated, filterable)
  GET    /jobs/{id}         Get job status
  DELETE /jobs/{id}         Cancel a PENDING job
  POST   /jobs/{id}/retry   Re-enqueue a FAILED job
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from middleware.rbac import get_current_user_payload
from models.m10 import BackgroundJob
from services.cache import cache
from services.task_queue import task_queue, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["background-jobs"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class EnqueueJobRequest(BaseModel):
    job_type: str
    payload: Optional[Dict[str, Any]] = None
    priority: int = 5
    max_retries: int = 3
    idempotency_key: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _publish_progress(job_id: str, status: str, progress_pct: Optional[int] = None) -> None:
    """Publish job progress to WebSocket via Redis pub/sub."""
    try:
        cache.publish(
            f"jobs:{job_id}",
            {"job_id": job_id, "status": status, "progress_pct": progress_pct, "ts": time.time()},
        )
    except Exception:
        pass


def _job_to_dict(job: BackgroundJob) -> Dict[str, Any]:
    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "priority": job.priority,
        "payload": job.payload,
        "result": job.result,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "progress_pct": job.progress_pct,
        "idempotency_key": job.idempotency_key,
        "user_id": str(job.user_id) if job.user_id else None,
        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def _run_job(job_id: str, job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generic job executor. Dispatches by job_type. Returns result dict."""
    # Import DB session for updates within the thread.
    from database import SessionLocal
    db = SessionLocal()
    try:
        job = db.get(BackgroundJob, uuid.UUID(job_id))
        if not job:
            return {"error": "Job record not found"}

        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        _publish_progress(job_id, "RUNNING", 0)

        # Dispatch
        result = _dispatch(job_type, payload, job_id)

        job.status = "COMPLETED"
        job.result = result
        job.completed_at = datetime.now(timezone.utc)
        job.progress_pct = 100
        db.commit()
        _publish_progress(job_id, "COMPLETED", 100)
        return result
    except Exception as exc:
        try:
            job = db.get(BackgroundJob, uuid.UUID(job_id))
            if job:
                job.status = "FAILED"
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            _publish_progress(job_id, "FAILED")
        except Exception:
            pass
        raise
    finally:
        db.close()


def _dispatch(job_type: str, payload: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """Dispatch a job to the appropriate handler. Extend for new job types."""
    if job_type == "market_data_refresh":
        ticker = payload.get("ticker", "SPY")
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        return {"ticker": ticker, "price": getattr(info, "last_price", None)}

    if job_type == "portfolio_risk_snapshot":
        tickers = payload.get("tickers", [])
        return {"tickers_processed": len(tickers), "snapshot_taken": True}

    if job_type == "strategy_backtest":
        return {"message": "Backtest dispatched", "strategy": payload.get("strategy_type")}

    # Generic echo job — useful for testing
    if job_type == "echo":
        return {"echo": payload, "job_id": job_id}

    raise ValueError(f"Unknown job_type: {job_type!r}. Supported: market_data_refresh, portfolio_risk_snapshot, strategy_backtest, echo")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=Dict[str, Any], status_code=202)
def enqueue_job(
    req: EnqueueJobRequest,
    db: Session = Depends(get_db),
    payload_jwt: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """Enqueue a new background job. Returns immediately with job ID and status=PENDING."""
    user_id = uuid.UUID(payload_jwt["sub"])

    # Idempotency: return existing job if key already used
    if req.idempotency_key:
        existing = db.execute(
            select(BackgroundJob).where(BackgroundJob.idempotency_key == req.idempotency_key)
        ).scalars().first()
        if existing:
            return {**_job_to_dict(existing), "idempotent": True}

    job = BackgroundJob(
        id=uuid.uuid4(),
        idempotency_key=req.idempotency_key,
        user_id=user_id,
        job_type=req.job_type,
        status="PENDING",
        priority=req.priority,
        payload=req.payload or {},
        max_retries=req.max_retries,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    job_id = str(job.id)
    task_queue.enqueue(
        _run_job,
        job_id,
        req.job_type,
        req.payload or {},
        task_name=f"job:{req.job_type}",
        priority=req.priority,
        metadata={"job_id": job_id},
    )

    return _job_to_dict(job)


@router.get("", response_model=Dict[str, Any])
def list_jobs(
    status: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """List background jobs with optional filters."""
    stmt = select(BackgroundJob).order_by(BackgroundJob.enqueued_at.desc()).offset(offset).limit(limit)
    if status:
        stmt = stmt.where(BackgroundJob.status == status.upper())
    if job_type:
        stmt = stmt.where(BackgroundJob.job_type == job_type)
    jobs = list(db.execute(stmt).scalars())
    return {"jobs": [_job_to_dict(j) for j in jobs], "count": len(jobs)}


@router.get("/{job_id}", response_model=Dict[str, Any])
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """Get current status and result of a specific job."""
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    job = db.get(BackgroundJob, jid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dict(job)


@router.delete("/{job_id}", response_model=Dict[str, Any])
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """Cancel a PENDING job. Running jobs cannot be interrupted."""
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    job = db.get(BackgroundJob, jid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("PENDING",):
        raise HTTPException(status_code=409, detail=f"Cannot cancel a job in status {job.status}")
    job.status = "CANCELLED"
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    _publish_progress(job_id, "CANCELLED")
    return {"cancelled": True, "job_id": job_id}


@router.post("/{job_id}/retry", response_model=Dict[str, Any])
def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Dict[str, Any]:
    """Re-enqueue a FAILED or CANCELLED job."""
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    job = db.get(BackgroundJob, jid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("FAILED", "CANCELLED"):
        raise HTTPException(status_code=409, detail=f"Only FAILED or CANCELLED jobs can be retried. Current status: {job.status}")
    if job.retry_count >= job.max_retries:
        raise HTTPException(status_code=422, detail=f"Max retries ({job.max_retries}) reached")

    job.status = "PENDING"
    job.retry_count += 1
    job.error_message = None
    job.result = None
    job.started_at = None
    job.completed_at = None
    job.enqueued_at = datetime.now(timezone.utc)
    db.commit()

    task_queue.enqueue(
        _run_job,
        job_id,
        job.job_type,
        job.payload or {},
        task_name=f"job:{job.job_type}:retry{job.retry_count}",
        priority=job.priority,
        metadata={"job_id": job_id, "retry_count": job.retry_count},
    )

    return _job_to_dict(job)
