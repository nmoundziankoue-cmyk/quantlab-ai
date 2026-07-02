"""AI Research Copilot — deterministic analytical engine.

Runs entirely without external LLM API keys using:
- Structured template rendering (prompt_templates.py)
- RAG retrieval from ingested documents (rag_engine.py)
- Session memory (research_memory.py)
- Available market data context

When API keys are available in the future, swap _generate_response()
for an LLM call while keeping the same interface.
"""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.document_intelligence import CopilotSession
from schemas.document_intelligence import (
    CopilotSessionCreate, CopilotMessageCreate,
    ThesisRequest, MemoRequest, ReportRequest, CitedAnswer,
    AskDocumentRequest,
)
import services.research_memory as memory_svc
import services.prompt_templates as templates
from services.rag_engine import ask_document, search_documents
from schemas.document_intelligence import DocumentSearchRequest


# ---------------------------------------------------------------------------
# Response generator (deterministic)
# ---------------------------------------------------------------------------

_GREETING_TRIGGERS = {"hello", "hi", "hey", "help", "start"}
_THESIS_TRIGGERS = {"thesis", "invest", "recommendation", "rate", "target"}
_RISK_TRIGGERS = {"risk", "downside", "bear", "worry", "concern"}
_BULL_TRIGGERS = {"upside", "bull", "catalyst", "opportunity", "growth"}
_SWOT_TRIGGERS = {"swot", "strength", "weakness", "opportunity", "threat"}


def _classify_intent(message: str) -> str:
    lower = message.lower()
    if any(t in lower for t in _GREETING_TRIGGERS):
        return "greeting"
    if any(t in lower for t in _SWOT_TRIGGERS):
        return "swot"
    if any(t in lower for t in _THESIS_TRIGGERS):
        return "thesis"
    if any(t in lower for t in _RISK_TRIGGERS):
        return "risk"
    if any(t in lower for t in _BULL_TRIGGERS):
        return "bull"
    return "general"


def _extract_ticker_from_message(message: str) -> Optional[str]:
    import re
    tickers = re.findall(r"\b([A-Z]{1,5})\b", message)
    common = {"I", "A", "THE", "AN", "IS", "IN", "AT", "TO", "OR", "AND", "FOR", "BE", "DO"}
    found = [t for t in tickers if t not in common and len(t) >= 2]
    return found[0] if found else None


def _generate_response(message: str, session: CopilotSession, context: str = "") -> str:
    intent = _classify_intent(message)
    ticker = _extract_ticker_from_message(message) or session.ticker or "the company"

    if intent == "greeting":
        return (
            f"Welcome to the AI Research Copilot. I can help you with:\n\n"
            f"- **Investment thesis** generation for any ticker\n"
            f"- **Bull/bear case** analysis\n"
            f"- **SWOT and Porter Five Forces** frameworks\n"
            f"- **Earnings summaries** and research memos\n"
            f"- **Document Q&A** from your ingested research library\n\n"
            f"Try asking: *'Generate a bull case for AAPL'* or *'What are the risks for MSFT?'*"
        )
    elif intent == "swot":
        return templates.render_swot(ticker, {"company_name": ticker, "sector": "Technology"})
    elif intent == "thesis":
        return templates.render_investment_thesis(ticker, {"sector": "N/A", "price": "N/A"})
    elif intent == "risk":
        return templates.render_bear_case(ticker, {"current_price": "N/A", "risks": ["Execution risk", "Competitive pressure", "Macro headwinds", "Valuation risk"]})
    elif intent == "bull":
        return templates.render_bull_case(ticker, {"current_price": "N/A", "catalysts": ["Earnings acceleration", "Market share gains", "Product expansion", "Multiple re-rating"]})
    else:
        if context:
            return f"Based on the available research context:\n\n{context[:800]}\n\n---\n*Answer derived from ingested documents. Ingest more documents for richer responses.*"
        return (
            f"I understand you're asking about: *{message}*\n\n"
            f"To provide a more precise answer, please:\n"
            f"1. Specify the ticker symbol (e.g., AAPL, MSFT)\n"
            f"2. Use a specific template: thesis, bull case, bear case, SWOT\n"
            f"3. Ingest relevant documents for document Q&A\n\n"
            f"*Type 'help' to see available capabilities.*"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_chat_session(db: Session, data: CopilotSessionCreate) -> CopilotSession:
    return memory_svc.create_session(db, data)


def get_chat_session(db: Session, session_id: uuid.UUID) -> Optional[CopilotSession]:
    return memory_svc.get_session(db, session_id)


def list_chat_sessions(db: Session, session_type: Optional[str] = None) -> List[CopilotSession]:
    return memory_svc.list_sessions(db, session_type)


def send_message(db: Session, session_id: uuid.UUID, data: CopilotMessageCreate) -> Dict[str, Any]:
    session = memory_svc.get_session(db, session_id)
    if not session:
        return {"error": "Session not found"}

    memory_svc.append_message(db, session, "user", data.content)

    rag_context = ""
    citations = []
    if data.document_ids:
        memory_svc.update_context_docs(db, session, [str(d) for d in data.document_ids])
        rag_req = AskDocumentRequest(question=data.content, document_ids=data.document_ids, top_k=5)
        cited = ask_document(db, rag_req)
        rag_context = cited.answer
        citations = [c.model_dump() for c in cited.citations]
    elif session.context_docs:
        doc_ids = [uuid.UUID(d) for d in session.context_docs[:5]]
        rag_req = AskDocumentRequest(question=data.content, document_ids=doc_ids, top_k=3)
        cited = ask_document(db, rag_req)
        rag_context = cited.answer if cited.confidence > 0.1 else ""
        citations = [c.model_dump() for c in cited.citations] if rag_context else []

    assistant_content = _generate_response(data.content, session, rag_context)
    memory_svc.append_message(db, session, "assistant", assistant_content, citations)

    return {
        "session_id": str(session_id),
        "role": "assistant",
        "content": assistant_content,
        "citations": citations,
    }


def generate_thesis(db: Session, req: ThesisRequest) -> Dict[str, Any]:
    context: Dict[str, Any] = {"sector": "N/A", "price": "N/A"}
    if req.additional_context:
        context["additional_context"] = req.additional_context
    content = templates.render_investment_thesis(req.ticker, context)
    if req.document_ids:
        rag_req = AskDocumentRequest(question=f"Investment thesis for {req.ticker}", document_ids=req.document_ids, top_k=5)
        cited = ask_document(db, rag_req)
        if cited.confidence > 0.1:
            content += f"\n\n### Research Context\n{cited.answer}"
    return {"ticker": req.ticker, "type": "investment_thesis", "content": content}


def generate_memo(db: Session, req: MemoRequest) -> Dict[str, Any]:
    context = {"recommendation": "NEUTRAL", "target_price": "N/A", "key_points": req.key_points or []}
    content = templates.render_research_memo(req.ticker, context)
    return {"ticker": req.ticker, "memo_type": req.memo_type, "content": content}


def generate_report_draft(db: Session, req: ReportRequest) -> Dict[str, Any]:
    context = {"company_name": req.ticker, "sector": "N/A", "recommendation": "NEUTRAL", "target_price": "N/A"}
    sections = templates.render_full_report_structure(req.ticker, context)
    full_md = "\n\n".join(sections.values())
    return {
        "ticker": req.ticker,
        "sections": sections,
        "full_markdown": full_md,
        "section_count": len(sections),
    }
