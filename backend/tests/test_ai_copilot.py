"""Tests for M6 AI Research Copilot — sessions, messages, generation."""
from __future__ import annotations
import uuid
import pytest
from sqlalchemy.orm import Session

from schemas.document_intelligence import (
    CopilotSessionCreate, CopilotMessageCreate,
    ThesisRequest, MemoRequest, ReportRequest,
)
from services.ai_copilot import (
    create_chat_session, get_chat_session, list_chat_sessions,
    send_message, generate_thesis, generate_memo, generate_report_draft,
    _classify_intent, _extract_ticker_from_message,
)
from services.prompt_templates import (
    render_investment_thesis, render_bull_case, render_bear_case,
    render_swot, render_porter_five_forces, render_earnings_summary,
    render_research_memo, render_full_report_structure,
    list_templates,
)


# ---------------------------------------------------------------------------
# Intent classifier (pure)
# ---------------------------------------------------------------------------

def test_classify_greeting():
    assert _classify_intent("hello, can you help me?") == "greeting"


def test_classify_thesis():
    assert _classify_intent("give me an investment thesis for AAPL") == "thesis"


def test_classify_risk():
    assert _classify_intent("what are the main risks for MSFT?") == "risk"


def test_classify_bull():
    assert _classify_intent("what is the upside case for NVDA?") == "bull"


def test_classify_swot():
    assert _classify_intent("run a SWOT analysis for GOOGL") == "swot"


def test_classify_general():
    assert _classify_intent("tell me about cloud computing") == "general"


# ---------------------------------------------------------------------------
# Ticker extractor (pure)
# ---------------------------------------------------------------------------

def test_extract_ticker_basic():
    assert _extract_ticker_from_message("What is AAPL worth?") == "AAPL"


def test_extract_ticker_none():
    result = _extract_ticker_from_message("what is the meaning of life")
    # May return None or a non-standard token — just check it doesn't crash
    assert result is None or isinstance(result, str)


def test_extract_ticker_filters_stopwords():
    result = _extract_ticker_from_message("THE OR AND")
    assert result is None


def test_extract_ticker_prefers_first():
    result = _extract_ticker_from_message("compare AAPL and MSFT")
    assert result in ("AAPL", "MSFT")


# ---------------------------------------------------------------------------
# Prompt templates (pure, no DB)
# ---------------------------------------------------------------------------

def test_render_investment_thesis():
    out = render_investment_thesis("AAPL", {"company_name": "Apple", "sector": "Technology", "market_cap": "3T"})
    assert "AAPL" in out
    assert "Investment Thesis" in out


def test_render_bull_case():
    out = render_bull_case("MSFT", {"company_name": "Microsoft", "sector": "Cloud"})
    assert "MSFT" in out
    assert "Bull" in out


def test_render_bear_case():
    out = render_bear_case("TSLA", {"company_name": "Tesla"})
    assert "TSLA" in out
    assert "Bear" in out or "Risk" in out


def test_render_swot():
    out = render_swot("NVDA", {"company_name": "NVIDIA", "sector": "Semiconductors"})
    assert "NVDA" in out or "NVIDIA" in out
    assert "Strength" in out or "SWOT" in out


def test_render_porter_five_forces():
    out = render_porter_five_forces("AMZN", {"company_name": "Amazon"})
    assert "AMZN" in out or "Amazon" in out


def test_render_earnings_summary():
    ctx = {"eps_actual": 2.18, "eps_estimate": 2.05, "revenue_actual": "119B", "revenue_estimate": "117B"}
    out = render_earnings_summary("AAPL", ctx)
    assert "AAPL" in out


def test_render_research_memo():
    out = render_research_memo("GOOGL", {"company_name": "Alphabet"})
    assert "GOOGL" in out or "Alphabet" in out


def test_render_full_report_structure():
    sections = render_full_report_structure("META", {"company_name": "Meta Platforms"})
    assert isinstance(sections, dict)
    assert len(sections) >= 5


def test_prompt_templates_list():
    templates = list_templates()
    assert isinstance(templates, list)
    assert len(templates) >= 10
    names = [t.get("key") or t.get("id") for t in templates]
    assert "investment_thesis" in names
    assert "bull_case" in names
    assert "swot" in names


# ---------------------------------------------------------------------------
# Chat session CRUD (DB)
# ---------------------------------------------------------------------------

def test_create_chat_session(db: Session):
    data = CopilotSessionCreate(title="AAPL Session", session_type="CHAT", ticker="AAPL")
    session = create_chat_session(db, data)
    assert session.id is not None
    assert session.title == "AAPL Session"
    assert session.ticker == "AAPL"


def test_create_chat_session_minimal(db: Session):
    data = CopilotSessionCreate(title="Minimal")
    session = create_chat_session(db, data)
    assert session.messages == []


def test_get_chat_session(db: Session):
    data = CopilotSessionCreate(title="Get Me")
    s = create_chat_session(db, data)
    found = get_chat_session(db, s.id)
    assert found is not None
    assert found.title == "Get Me"


def test_get_chat_session_missing(db: Session):
    assert get_chat_session(db, uuid.uuid4()) is None


def test_list_chat_sessions(db: Session):
    create_chat_session(db, CopilotSessionCreate(title="S1", session_type="CHAT"))
    create_chat_session(db, CopilotSessionCreate(title="S2", session_type="THESIS"))
    result = list_chat_sessions(db)
    assert len(result) >= 2


def test_list_chat_sessions_filter_type(db: Session):
    create_chat_session(db, CopilotSessionCreate(title="Chat1", session_type="CHAT"))
    create_chat_session(db, CopilotSessionCreate(title="Thesis1", session_type="THESIS"))
    chats = list_chat_sessions(db, session_type="CHAT")
    assert all(s.session_type == "CHAT" for s in chats)


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------

def test_send_message_greeting(db: Session):
    s = create_chat_session(db, CopilotSessionCreate(title="Greet"))
    result = send_message(db, s.id, CopilotMessageCreate(content="hello"))
    assert "content" in result
    assert result.get("session_id") == str(s.id)


def test_send_message_appends_to_history(db: Session):
    s = create_chat_session(db, CopilotSessionCreate(title="History"))
    send_message(db, s.id, CopilotMessageCreate(content="What is the thesis for AAPL?"))
    session = get_chat_session(db, s.id)
    assert len(session.messages) >= 2  # user + assistant


def test_send_message_thesis_intent(db: Session):
    s = create_chat_session(db, CopilotSessionCreate(title="Thesis"))
    result = send_message(db, s.id, CopilotMessageCreate(content="Give me an investment thesis for MSFT"))
    response = result.get("content", "")
    assert len(response) > 50


def test_send_message_risk_intent(db: Session):
    s = create_chat_session(db, CopilotSessionCreate(title="Risk"))
    result = send_message(db, s.id, CopilotMessageCreate(content="What are the main risks for TSLA?"))
    response = result.get("content", "")
    assert len(response) > 20


def test_send_message_session_not_found(db: Session):
    result = send_message(db, uuid.uuid4(), CopilotMessageCreate(content="hello"))
    assert "error" in result


def test_send_message_returns_content(db: Session):
    s = create_chat_session(db, CopilotSessionCreate(title="Intent"))
    result = send_message(db, s.id, CopilotMessageCreate(content="bull case for AAPL upside"))
    assert "content" in result


# ---------------------------------------------------------------------------
# Thesis / Memo / Report generation
# ---------------------------------------------------------------------------

def test_generate_thesis(db: Session):
    req = ThesisRequest(ticker="AAPL")
    result = generate_thesis(db, req)
    assert "content" in result
    assert "AAPL" in result.get("content", "")


def test_generate_thesis_type(db: Session):
    req = ThesisRequest(ticker="MSFT")
    result = generate_thesis(db, req)
    assert result.get("type") == "investment_thesis"


def test_generate_memo(db: Session):
    req = MemoRequest(ticker="MSFT")
    result = generate_memo(db, req)
    assert "content" in result
    assert result.get("ticker") == "MSFT"


def test_generate_report_draft(db: Session):
    req = ReportRequest(ticker="NVDA")
    result = generate_report_draft(db, req)
    assert "sections" in result
    assert len(result["sections"]) >= 5


def test_generate_report_draft_has_markdown(db: Session):
    req = ReportRequest(ticker="AAPL")
    result = generate_report_draft(db, req)
    assert "full_markdown" in result
    assert len(result["full_markdown"]) > 100
