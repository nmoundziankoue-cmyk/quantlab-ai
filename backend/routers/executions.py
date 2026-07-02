"""Executions router — EMS read layer + execution analytics + blotter.

Endpoints:
  GET  /executions                           List executions
  GET  /executions/{execution_id}            Single execution
  GET  /executions/order/{order_id}          Fills for an order
  GET  /executions/{order_id}/quality        Execution quality report
  GET  /executions/blotter                   Trade blotter
  GET  /executions/blotter/csv               CSV export
  GET  /executions/analytics                 Aggregate execution analytics
  GET  /executions/algorithms                List available execution algorithms
  POST /executions/algorithms/twap           Compute TWAP schedule
  POST /executions/algorithms/vwap           Compute VWAP schedule
  POST /executions/algorithms/pov            Compute POV schedule
  POST /executions/algorithms/iceberg        Compute Iceberg schedule
  POST /executions/algorithms/adaptive       Compute Adaptive schedule
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas.trading import (
    AlgoScheduleResponse,
    BlotterResponse,
    ExecutionAnalyticsSummary,
    ExecutionListResponse,
    ExecutionQualityReport,
    ExecutionResponse,
    IcebergRequest,
    POVRequest,
    TWAPRequest,
    VWAPRequest,
)
from services import ems as ems_service
from services.execution_algorithms import (
    compute_adaptive,
    compute_iceberg,
    compute_pov,
    compute_twap,
    compute_vwap,
    ALGO_FUNCTIONS,
)

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("", response_model=ExecutionListResponse)
def list_executions(
    order_id: Optional[uuid.UUID] = Query(default=None),
    ticker: Optional[str] = Query(default=None),
    venue: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ExecutionListResponse:
    execs, total = ems_service.list_executions(
        db, order_id=order_id, ticker=ticker, since=since, until=until, venue=venue, page=page, page_size=page_size
    )
    return ExecutionListResponse(
        executions=[ExecutionResponse.model_validate(e) for e in execs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/blotter", response_model=BlotterResponse)
def get_blotter(
    portfolio_id: Optional[uuid.UUID] = Query(default=None),
    paper_account_id: Optional[uuid.UUID] = Query(default=None),
    ticker: Optional[str] = Query(default=None),
    side: Optional[str] = Query(default=None),
    strategy_tag: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> BlotterResponse:
    rows, total, summary = ems_service.get_blotter(
        db,
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        ticker=ticker,
        since=since,
        until=until,
        side=side,
        strategy_tag=strategy_tag,
        page=page,
        page_size=page_size,
    )
    from schemas.trading import BlotterRow
    return BlotterResponse(
        rows=[BlotterRow(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        summary=summary,
    )


@router.get("/blotter/csv", response_class=PlainTextResponse)
def export_blotter_csv(
    portfolio_id: Optional[uuid.UUID] = Query(default=None),
    paper_account_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
) -> str:
    csv_content = ems_service.export_blotter_csv(db, portfolio_id=portfolio_id, paper_account_id=paper_account_id)
    return csv_content


@router.get("/analytics", response_model=Dict[str, Any])
def get_execution_analytics(
    portfolio_id: Optional[uuid.UUID] = Query(default=None),
    paper_account_id: Optional[uuid.UUID] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    result = ems_service.get_execution_analytics(
        db,
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        since=since,
        until=until,
    )
    # Coerce Decimal to str for JSON
    from decimal import Decimal
    def _coerce(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, dict):
            return {k: _coerce(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_coerce(i) for i in obj]
        return obj
    return _coerce(result)


@router.get("/algorithms", response_model=List[str])
def list_algorithms() -> List[str]:
    return list(ALGO_FUNCTIONS.keys())


@router.post("/algorithms/twap", response_model=AlgoScheduleResponse)
def schedule_twap(body: TWAPRequest) -> AlgoScheduleResponse:
    result = compute_twap(
        ticker=body.ticker,
        total_quantity=body.quantity,
        duration_minutes=body.duration_minutes,
        n_slices=body.n_slices,
        current_price=body.current_price,
    )
    return AlgoScheduleResponse(**result)


@router.post("/algorithms/vwap", response_model=AlgoScheduleResponse)
def schedule_vwap(body: VWAPRequest) -> AlgoScheduleResponse:
    try:
        result = compute_vwap(
            ticker=body.ticker,
            total_quantity=body.quantity,
            volume_profile=body.volume_profile,
            duration_minutes=body.duration_minutes,
            current_price=body.current_price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return AlgoScheduleResponse(**result)


@router.post("/algorithms/pov", response_model=AlgoScheduleResponse)
def schedule_pov(body: POVRequest) -> AlgoScheduleResponse:
    try:
        result = compute_pov(
            ticker=body.ticker,
            total_quantity=body.quantity,
            participation_rate=body.participation_rate,
            avg_volume_per_minute=body.avg_volume_per_minute,
            current_price=body.current_price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return AlgoScheduleResponse(**result)


@router.post("/algorithms/iceberg", response_model=AlgoScheduleResponse)
def schedule_iceberg(body: IcebergRequest) -> AlgoScheduleResponse:
    try:
        result = compute_iceberg(
            ticker=body.ticker,
            total_quantity=body.total_quantity,
            display_quantity=body.display_quantity,
            limit_price=body.limit_price,
            refill_delay_minutes=body.refill_delay_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return AlgoScheduleResponse(**result)


@router.post("/algorithms/adaptive", response_model=AlgoScheduleResponse)
def schedule_adaptive(
    ticker: str = Query(...),
    quantity: float = Query(...),
    duration_minutes: int = Query(default=60),
    urgency: float = Query(default=0.5),
    current_price: float = Query(default=100.0),
) -> AlgoScheduleResponse:
    from decimal import Decimal
    try:
        result = compute_adaptive(
            ticker=ticker,
            total_quantity=Decimal(str(quantity)),
            duration_minutes=duration_minutes,
            urgency=urgency,
            current_price=Decimal(str(current_price)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return AlgoScheduleResponse(**result)


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: uuid.UUID, db: Session = Depends(get_db)) -> ExecutionResponse:
    exc = ems_service.get_execution(db, execution_id)
    if exc is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    return ExecutionResponse.model_validate(exc)


@router.get("/order/{order_id}", response_model=List[ExecutionResponse])
def get_order_executions(order_id: uuid.UUID, db: Session = Depends(get_db)) -> List[ExecutionResponse]:
    execs = ems_service.list_executions_for_order(db, order_id)
    return [ExecutionResponse.model_validate(e) for e in execs]


@router.get("/order/{order_id}/quality", response_model=ExecutionQualityReport)
def get_execution_quality(order_id: uuid.UUID, db: Session = Depends(get_db)) -> ExecutionQualityReport:
    try:
        result = ems_service.compute_execution_quality(db, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ExecutionQualityReport(**result)
