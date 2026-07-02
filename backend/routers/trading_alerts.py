"""Trading Alerts router.

Endpoints:
  POST   /trading-alerts                    Create alert
  GET    /trading-alerts                    List alerts
  GET    /trading-alerts/{alert_id}         Get alert
  PATCH  /trading-alerts/{alert_id}         Update alert
  DELETE /trading-alerts/{alert_id}         Delete alert
  GET    /trading-alerts/types              List alert types
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.trading import AlertTypeEnum
from schemas.trading import AlertCreate, AlertResponse, AlertUpdate
from services import alerts as alert_service

router = APIRouter(prefix="/trading-alerts", tags=["alerts"])


@router.get("/types", response_model=List[str])
def list_alert_types() -> List[str]:
    return [t.value for t in AlertTypeEnum]


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(body: AlertCreate, db: Session = Depends(get_db)) -> AlertResponse:
    alert = alert_service.create_alert(
        db,
        name=body.name,
        alert_type=body.alert_type,
        trigger_condition=body.trigger_condition,
        message_template=body.message_template,
        portfolio_id=body.portfolio_id,
        paper_account_id=body.paper_account_id,
        ticker=body.ticker,
    )
    return AlertResponse.model_validate(alert)


@router.get("", response_model=List[AlertResponse])
def list_alerts(
    portfolio_id: Optional[uuid.UUID] = Query(default=None),
    paper_account_id: Optional[uuid.UUID] = Query(default=None),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> List[AlertResponse]:
    alerts = alert_service.list_alerts(
        db,
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        active_only=active_only,
    )
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: uuid.UUID, db: Session = Depends(get_db)) -> AlertResponse:
    alert = alert_service.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: uuid.UUID,
    body: AlertUpdate,
    db: Session = Depends(get_db),
) -> AlertResponse:
    try:
        alert = alert_service.update_alert(db, alert_id, **body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AlertResponse.model_validate(alert)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    try:
        alert_service.delete_alert(db, alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
