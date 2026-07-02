"""Enterprise notification delivery service (M8).

Supported channels: EMAIL, WEBHOOK, SLACK, CONSOLE (fallback).
Persists delivery attempts and logs to the notification_logs table.
"""
from __future__ import annotations

import json
import logging
import smtplib
import time
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from sqlalchemy.orm import Session

from models.notifications import NotificationLog, NotificationTemplate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel constants
# ---------------------------------------------------------------------------

CHANNEL_EMAIL = "EMAIL"
CHANNEL_SLACK = "SLACK"
CHANNEL_WEBHOOK = "WEBHOOK"
CHANNEL_DISCORD = "DISCORD"
CHANNEL_CONSOLE = "CONSOLE"

VALID_CHANNELS = {CHANNEL_EMAIL, CHANNEL_SLACK, CHANNEL_WEBHOOK, CHANNEL_DISCORD, CHANNEL_CONSOLE}
VALID_STATUSES = {"PENDING", "DELIVERED", "FAILED", "RETRYING"}

# ---------------------------------------------------------------------------
# Delivery functions
# ---------------------------------------------------------------------------


def _send_email(
    recipient: str,
    subject: str,
    body: str,
    *,
    smtp_host: str = "localhost",
    smtp_port: int = 587,
    smtp_user: Optional[str] = None,
    smtp_pass: Optional[str] = None,
    use_tls: bool = True,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user or "noreply@apexquant.io"
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(f"<pre>{body}</pre>", "html"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        if use_tls:
            server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.sendmail(msg["From"], recipient, msg.as_string())


def _send_webhook(url: str, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=10) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"Webhook returned HTTP {resp.status}")


def _send_slack(webhook_url: str, text: str, subject: Optional[str] = None) -> None:
    payload = {"text": f"*{subject}*\n{text}" if subject else text}
    _send_webhook(webhook_url, payload)


def _send_discord(webhook_url: str, text: str, subject: Optional[str] = None) -> None:
    payload = {"content": f"**{subject}**\n{text}" if subject else text}
    _send_webhook(webhook_url, payload)


def _send_console(recipient: str, subject: Optional[str], body: str) -> None:
    logger.info(
        "[NOTIFICATION] channel=CONSOLE recipient=%s subject=%s\n%s",
        recipient,
        subject,
        body,
    )


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------


def send_notification(
    db: Session,
    *,
    channel: str,
    recipient: str,
    subject: Optional[str] = None,
    body: str,
    user_id: Optional[uuid.UUID] = None,
    priority: int = 5,
    metadata: Optional[Dict] = None,
    smtp_config: Optional[Dict] = None,
) -> dict:
    """Deliver a notification and persist the log record.

    ``smtp_config`` keys: host, port, user, password, use_tls.
    For SLACK/DISCORD/WEBHOOK, ``recipient`` is the webhook URL.
    """
    if channel not in VALID_CHANNELS:
        raise ValueError(f"Unknown channel: {channel}. Valid: {VALID_CHANNELS}")

    log = NotificationLog(
        user_id=user_id,
        channel=channel,
        recipient=recipient,
        subject=subject,
        body=body,
        status="PENDING",
        priority=priority,
        metadata_=metadata or {},
    )
    db.add(log)
    db.flush()

    error_msg: Optional[str] = None
    try:
        if channel == CHANNEL_EMAIL:
            cfg = smtp_config or {}
            _send_email(
                recipient,
                subject or "ApexQuant Notification",
                body,
                smtp_host=cfg.get("host", "localhost"),
                smtp_port=cfg.get("port", 587),
                smtp_user=cfg.get("user"),
                smtp_pass=cfg.get("password"),
                use_tls=cfg.get("use_tls", True),
            )
        elif channel == CHANNEL_SLACK:
            _send_slack(recipient, body, subject)
        elif channel == CHANNEL_DISCORD:
            _send_discord(recipient, body, subject)
        elif channel == CHANNEL_WEBHOOK:
            _send_webhook(recipient, {"subject": subject, "body": body, "metadata": metadata})
        elif channel == CHANNEL_CONSOLE:
            _send_console(recipient, subject, body)

        log.status = "DELIVERED"
        log.delivered_at = datetime.now(timezone.utc)
    except (URLError, smtplib.SMTPException, OSError, RuntimeError) as exc:
        error_msg = str(exc)
        log.status = "FAILED"
        log.error_message = error_msg
        logger.warning("Notification delivery failed (%s): %s", channel, exc)
    finally:
        log.attempts += 1
        db.flush()

    return _log_to_dict(log)


def send_from_template(
    db: Session,
    template_name: str,
    recipient: str,
    *,
    variables: Optional[Dict[str, str]] = None,
    user_id: Optional[uuid.UUID] = None,
    **kwargs: Any,
) -> dict:
    template = (
        db.query(NotificationTemplate)
        .filter(
            NotificationTemplate.name == template_name,
            NotificationTemplate.is_active.is_(True),
        )
        .first()
    )
    if template is None:
        raise ValueError(f"Template '{template_name}' not found or inactive")

    vars_ = variables or {}
    body = Template(template.body_template).safe_substitute(vars_)
    subject = (
        Template(template.subject_template).safe_substitute(vars_)
        if template.subject_template
        else None
    )

    return send_notification(
        db,
        channel=template.channel,
        recipient=recipient,
        subject=subject,
        body=body,
        user_id=user_id,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Template CRUD
# ---------------------------------------------------------------------------


def create_template(
    db: Session,
    *,
    name: str,
    channel: str,
    body_template: str,
    subject_template: Optional[str] = None,
    variables: Optional[Dict] = None,
) -> dict:
    if channel not in VALID_CHANNELS:
        raise ValueError(f"Unknown channel: {channel}")
    existing = db.query(NotificationTemplate).filter(NotificationTemplate.name == name).first()
    if existing:
        raise ValueError(f"Template '{name}' already exists")
    tpl = NotificationTemplate(
        name=name,
        channel=channel,
        body_template=body_template,
        subject_template=subject_template,
        variables=variables or {},
    )
    db.add(tpl)
    db.flush()
    return _template_to_dict(tpl)


def get_template(db: Session, template_id: uuid.UUID) -> Optional[dict]:
    tpl = db.get(NotificationTemplate, template_id)
    return _template_to_dict(tpl) if tpl else None


def list_templates(db: Session, channel: Optional[str] = None, active_only: bool = True) -> List[dict]:
    q = db.query(NotificationTemplate)
    if active_only:
        q = q.filter(NotificationTemplate.is_active.is_(True))
    if channel:
        q = q.filter(NotificationTemplate.channel == channel)
    return [_template_to_dict(t) for t in q.order_by(NotificationTemplate.name).all()]


def update_template(db: Session, template_id: uuid.UUID, **fields: Any) -> Optional[dict]:
    tpl = db.get(NotificationTemplate, template_id)
    if tpl is None:
        return None
    allowed = {"body_template", "subject_template", "variables", "is_active", "channel"}
    for k, v in fields.items():
        if k in allowed:
            setattr(tpl, k, v)
    db.flush()
    return _template_to_dict(tpl)


def delete_template(db: Session, template_id: uuid.UUID) -> bool:
    tpl = db.get(NotificationTemplate, template_id)
    if tpl is None:
        return False
    db.delete(tpl)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Log queries
# ---------------------------------------------------------------------------


def list_logs(
    db: Session,
    *,
    user_id: Optional[uuid.UUID] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[dict]:
    q = db.query(NotificationLog)
    if user_id:
        q = q.filter(NotificationLog.user_id == user_id)
    if channel:
        q = q.filter(NotificationLog.channel == channel)
    if status:
        q = q.filter(NotificationLog.status == status)
    rows = q.order_by(NotificationLog.created_at.desc()).offset(offset).limit(limit).all()
    return [_log_to_dict(r) for r in rows]


def get_log(db: Session, log_id: uuid.UUID) -> Optional[dict]:
    log = db.get(NotificationLog, log_id)
    return _log_to_dict(log) if log else None


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _template_to_dict(t: NotificationTemplate) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "channel": t.channel,
        "subject_template": t.subject_template,
        "body_template": t.body_template,
        "variables": t.variables,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _log_to_dict(l: NotificationLog) -> dict:
    return {
        "id": str(l.id),
        "user_id": str(l.user_id) if l.user_id else None,
        "channel": l.channel,
        "recipient": l.recipient,
        "subject": l.subject,
        "body": l.body[:200] + "..." if len(l.body) > 200 else l.body,
        "status": l.status,
        "error_message": l.error_message,
        "attempts": l.attempts,
        "priority": l.priority,
        "created_at": l.created_at.isoformat() if l.created_at else None,
        "delivered_at": l.delivered_at.isoformat() if l.delivered_at else None,
    }
