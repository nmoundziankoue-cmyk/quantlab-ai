"""Notification management router (M8)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.rbac import get_current_user_payload
import services.notifications as notif_svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SendRequest(BaseModel):
    channel: str
    recipient: str
    subject: Optional[str] = None
    body: str
    priority: int = 5
    metadata: Optional[Dict] = None
    smtp_config: Optional[Dict] = None


class SendFromTemplateRequest(BaseModel):
    template_name: str
    recipient: str
    variables: Optional[Dict[str, str]] = None
    priority: int = 5


class CreateTemplateRequest(BaseModel):
    name: str
    channel: str
    body_template: str
    subject_template: Optional[str] = None
    variables: Optional[Dict] = None


class UpdateTemplateRequest(BaseModel):
    body_template: Optional[str] = None
    subject_template: Optional[str] = None
    variables: Optional[Dict] = None
    is_active: Optional[bool] = None
    channel: Optional[str] = None


# ---------------------------------------------------------------------------
# Send notifications
# ---------------------------------------------------------------------------


@router.post("/send")
def send_notification(
    body: SendRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Send a notification immediately."""
    user_id_str = payload.get("sub")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None
    try:
        result = notif_svc.send_notification(
            db,
            channel=body.channel,
            recipient=body.recipient,
            subject=body.subject,
            body=body.body,
            user_id=user_uuid,
            priority=body.priority,
            metadata=body.metadata,
            smtp_config=body.smtp_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/send-template")
def send_from_template(
    body: SendFromTemplateRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user_id_str = payload.get("sub")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None
    try:
        result = notif_svc.send_from_template(
            db,
            body.template_name,
            body.recipient,
            variables=body.variables,
            user_id=user_uuid,
            priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.post("/templates")
def create_template(
    body: CreateTemplateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        return notif_svc.create_template(
            db,
            name=body.name,
            channel=body.channel,
            body_template=body.body_template,
            subject_template=body.subject_template,
            variables=body.variables,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/templates")
def list_templates(
    channel: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    templates = notif_svc.list_templates(db, channel=channel, active_only=active_only)
    return {"templates": templates, "count": len(templates)}


@router.get("/templates/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    tid = uuid.UUID(template_id)
    result = notif_svc.get_template(db, tid)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.put("/templates/{template_id}")
def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tid = uuid.UUID(template_id)
    result = notif_svc.update_template(db, tid, **body.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.delete("/templates/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    tid = uuid.UUID(template_id)
    ok = notif_svc.delete_template(db, tid)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True, "id": template_id}


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


@router.get("/logs")
def list_logs(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user_id_str = payload.get("sub")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None
    logs = notif_svc.list_logs(
        db, user_id=user_uuid, channel=channel, status=status, limit=limit, offset=offset
    )
    return {"logs": logs, "count": len(logs)}


@router.get("/logs/{log_id}")
def get_log(log_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    lid = uuid.UUID(log_id)
    result = notif_svc.get_log(db, lid)
    if result is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return result


@router.get("/channels")
def list_channels() -> Dict[str, Any]:
    return {
        "channels": list(notif_svc.VALID_CHANNELS),
        "descriptions": {
            "EMAIL": "SMTP email delivery",
            "SLACK": "Slack incoming webhook",
            "DISCORD": "Discord webhook",
            "WEBHOOK": "Generic HTTP POST webhook",
            "CONSOLE": "Log to console (dev/debug only)",
        },
    }
