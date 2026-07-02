"""Alert service.

Handles CRUD for alert definitions and evaluating trigger conditions.

Trigger condition schema (JSON blob stored in Alert.trigger_condition):
  {"metric": "drawdown_pct", "threshold": 10.0, "operator": "gt"}
  {"metric": "pnl_usd", "threshold": -5000.0, "operator": "lt"}
  {"metric": "order_status", "value": "REJECTED"}
  {"metric": "cash_pct", "threshold": 20.0, "operator": "lt"}
  {"metric": "position_pct", "ticker": "AAPL", "threshold": 30.0, "operator": "gt"}

Operators: "gt" (>), "gte" (>=), "lt" (<), "lte" (<=), "eq" (==)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.trading import Alert, AlertTypeEnum


# ---------------------------------------------------------------------------
# Operator evaluation
# ---------------------------------------------------------------------------


def _evaluate(actual: float, threshold: float, operator: str) -> bool:
    ops = {
        "gt": actual > threshold,
        "gte": actual >= threshold,
        "lt": actual < threshold,
        "lte": actual <= threshold,
        "eq": actual == threshold,
    }
    return ops.get(operator, False)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_alert(db: Session, name: str, alert_type: str, trigger_condition: Dict[str, Any],
                 message_template: str, portfolio_id: Optional[uuid.UUID] = None,
                 paper_account_id: Optional[uuid.UUID] = None, ticker: Optional[str] = None) -> Alert:
    alert = Alert(
        name=name,
        alert_type=AlertTypeEnum(alert_type),
        portfolio_id=portfolio_id,
        paper_account_id=paper_account_id,
        ticker=ticker.upper() if ticker else None,
        trigger_condition=trigger_condition,
        message_template=message_template,
        is_active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alert(db: Session, alert_id: uuid.UUID) -> Optional[Alert]:
    return db.query(Alert).filter(Alert.id == alert_id).first()


def list_alerts(
    db: Session,
    portfolio_id: Optional[uuid.UUID] = None,
    paper_account_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
) -> List[Alert]:
    q = db.query(Alert)
    if portfolio_id:
        q = q.filter(Alert.portfolio_id == portfolio_id)
    if paper_account_id:
        q = q.filter(Alert.paper_account_id == paper_account_id)
    if active_only:
        q = q.filter(Alert.is_active == True)  # noqa: E712
    return q.order_by(Alert.created_at.desc()).all()


def update_alert(db: Session, alert_id: uuid.UUID, **kwargs) -> Alert:
    alert = get_alert(db, alert_id)
    if alert is None:
        raise ValueError(f"Alert {alert_id} not found")
    for key, val in kwargs.items():
        if hasattr(alert, key) and val is not None:
            setattr(alert, key, val)
    db.commit()
    db.refresh(alert)
    return alert


def delete_alert(db: Session, alert_id: uuid.UUID) -> None:
    alert = get_alert(db, alert_id)
    if alert is None:
        raise ValueError(f"Alert {alert_id} not found")
    db.delete(alert)
    db.commit()


# ---------------------------------------------------------------------------
# Trigger evaluation
# ---------------------------------------------------------------------------


def evaluate_alert(alert: Alert, context: Dict[str, Any]) -> Tuple[bool, str]:
    """Evaluate whether an alert should fire given a context dict.

    Returns (triggered, rendered_message).
    Context keys map to metric names (e.g. "drawdown_pct", "pnl_usd", etc.)
    """
    condition = alert.trigger_condition
    metric = condition.get("metric")
    operator = condition.get("operator")
    threshold = condition.get("threshold")
    value_match = condition.get("value")

    if metric not in context:
        return False, ""

    actual = context[metric]

    triggered = False
    if value_match is not None:
        triggered = str(actual) == str(value_match)
    elif threshold is not None and operator:
        try:
            triggered = _evaluate(float(actual), float(threshold), operator)
        except (TypeError, ValueError):
            triggered = False

    if not triggered:
        return False, ""

    # Render message template (simple {key} substitution)
    try:
        message = alert.message_template.format(**context)
    except (KeyError, ValueError):
        message = alert.message_template

    return True, message


def evaluate_all_alerts(db: Session, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Evaluate all active alerts against a given context.  Persist trigger state."""
    active = db.query(Alert).filter(Alert.is_active == True).all()  # noqa: E712
    fired: List[Dict[str, Any]] = []
    for alert in active:
        triggered, message = evaluate_alert(alert, context)
        if triggered:
            alert.is_triggered = True
            alert.trigger_count += 1
            alert.last_triggered_at = datetime.now(timezone.utc)
            fired.append({
                "alert_id": alert.id,
                "name": alert.name,
                "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else alert.alert_type,
                "message": message,
                "triggered_at": alert.last_triggered_at,
            })
    if fired:
        db.commit()
    return fired
