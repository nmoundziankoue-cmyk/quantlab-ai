"""Research memory — maintains per-session context for the AI copilot."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.document_intelligence import CopilotSession
from schemas.document_intelligence import CopilotSessionCreate, CopilotMessage


def create_session(db: Session, data: CopilotSessionCreate) -> CopilotSession:
    session = CopilotSession(
        title=data.title,
        session_type=data.session_type,
        ticker=data.ticker,
        messages=[],
        context_docs=[],
        metadata_={},
    )
    db.add(session)
    db.flush()
    return session


def get_session(db: Session, session_id: uuid.UUID) -> Optional[CopilotSession]:
    return db.query(CopilotSession).filter(CopilotSession.id == session_id).first()


def list_sessions(db: Session, session_type: Optional[str] = None, limit: int = 50) -> List[CopilotSession]:
    q = db.query(CopilotSession)
    if session_type:
        q = q.filter(CopilotSession.session_type == session_type)
    return q.order_by(CopilotSession.updated_at.desc()).limit(limit).all()


def append_message(db: Session, session: CopilotSession, role: str, content: str, citations: Optional[List[Dict]] = None) -> CopilotSession:
    messages: List[Dict] = list(session.messages or [])
    messages.append({
        "role": role,
        "content": content,
        "citations": citations or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    session.messages = messages
    db.flush()
    return session


def get_context_window(session: CopilotSession, max_messages: int = 10) -> List[Dict[str, Any]]:
    messages: List[Dict] = list(session.messages or [])
    return messages[-max_messages:]


def update_context_docs(db: Session, session: CopilotSession, doc_ids: List[str]) -> CopilotSession:
    existing = list(session.context_docs or [])
    combined = list({*existing, *doc_ids})[:20]
    session.context_docs = combined
    db.flush()
    return session
