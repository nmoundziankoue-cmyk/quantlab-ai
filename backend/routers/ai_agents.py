"""M9 Phase 7 — AI Research Copilot API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.ai_agents import get_orchestrator, list_agents, AGENT_TYPES

router = APIRouter(prefix="/agents/research", tags=["ai_agents"])


class SessionCreate(BaseModel):
    topic: str
    context: dict = {}
    tickers: List[str] = []


class AgentQuery(BaseModel):
    agent_type: str
    query: str


class MultiAgentQuery(BaseModel):
    query: str
    agents: Optional[List[str]] = None  # None = all agents


@router.get("/agents")
def get_agents():
    return {"agents": list_agents()}


@router.post("/sessions")
def create_session(body: SessionCreate):
    ctx = {**body.context, "tickers": body.tickers}
    s = get_orchestrator().create_session(body.topic, ctx)
    return {"id": s.id, "topic": s.topic, "created_at": s.created_at}


@router.get("/sessions")
def list_sessions():
    return {"sessions": get_orchestrator().list_sessions()}


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    s = get_orchestrator().get_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return {
        "id": s.id,
        "topic": s.topic,
        "messages": s.messages,
        "response_count": len(s.agent_responses),
        "created_at": s.created_at,
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    ok = get_orchestrator().delete_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"deleted": session_id}


@router.post("/sessions/{session_id}/query")
def single_agent_query(session_id: str, body: AgentQuery):
    if body.agent_type not in AGENT_TYPES:
        raise HTTPException(400, f"Unknown agent type. Valid: {AGENT_TYPES}")
    resp = get_orchestrator().run_agent(session_id, body.agent_type, body.query)
    if resp is None:
        raise HTTPException(404, "Session not found")
    return {
        "agent_type": resp.agent_type,
        "content": resp.content,
        "confidence": resp.confidence,
        "citations": [c.__dict__ for c in resp.citations],
        "tools_used": resp.tools_used,
        "timestamp": resp.timestamp,
    }


@router.post("/sessions/{session_id}/query/all")
def multi_agent_query(session_id: str, body: MultiAgentQuery):
    if body.agents:
        responses = []
        for agent_type in body.agents:
            r = get_orchestrator().run_agent(session_id, agent_type, body.query)
            if r:
                responses.append(r)
    else:
        responses = get_orchestrator().run_all_agents(session_id, body.query)
    return {
        "responses": [
            {"agent_type": r.agent_type, "content": r.content, "confidence": r.confidence}
            for r in responses
        ]
    }


@router.get("/sessions/{session_id}/synthesis")
def synthesize(session_id: str):
    s = get_orchestrator().get_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return get_orchestrator().synthesize(session_id)
