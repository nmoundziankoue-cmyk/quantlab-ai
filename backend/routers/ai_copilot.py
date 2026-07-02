from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.document_intelligence import (
    CopilotSessionCreate, CopilotSessionResponse, CopilotMessageCreate,
    ThesisRequest, MemoRequest, ReportRequest,
)
import services.ai_copilot as copilot_svc
import services.prompt_templates as templates

router = APIRouter(prefix="/copilot", tags=["ai-copilot"])


@router.post("/sessions", response_model=CopilotSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(data: CopilotSessionCreate, db: Session = Depends(get_db)):
    session = copilot_svc.create_chat_session(db, data)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=List[CopilotSessionResponse])
def list_sessions(session_type: Optional[str] = None, db: Session = Depends(get_db)):
    return copilot_svc.list_chat_sessions(db, session_type=session_type)


@router.get("/sessions/{session_id}", response_model=CopilotSessionResponse)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    s = copilot_svc.get_chat_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@router.post("/sessions/{session_id}/messages")
def send_message(session_id: uuid.UUID, data: CopilotMessageCreate, db: Session = Depends(get_db)):
    result = copilot_svc.send_message(db, session_id, data)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    db.commit()
    return result


@router.post("/generate/thesis")
def generate_thesis(req: ThesisRequest, db: Session = Depends(get_db)):
    return copilot_svc.generate_thesis(db, req)


@router.post("/generate/memo")
def generate_memo(req: MemoRequest, db: Session = Depends(get_db)):
    return copilot_svc.generate_memo(db, req)


@router.post("/generate/report")
def generate_report(req: ReportRequest, db: Session = Depends(get_db)):
    return copilot_svc.generate_report_draft(db, req)


@router.get("/templates")
def list_templates():
    return templates.list_templates()
