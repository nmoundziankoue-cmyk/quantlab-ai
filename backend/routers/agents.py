from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import services.agents as svc

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    agent_id: str
    ticker: str = ""
    context: Optional[Dict[str, Any]] = None


class MultiAgentRequest(BaseModel):
    tickers: List[str] = Field(min_length=1, max_length=10)
    agent_ids: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


@router.get("")
def list_agents():
    return svc.list_agents()


@router.get("/{agent_id}/capabilities")
def get_capabilities(agent_id: str):
    caps = svc.get_agent_capabilities(agent_id)
    if not caps:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return caps


@router.post("/run")
def run_agent(req: AgentRunRequest):
    return svc.run_agent(req.agent_id, ticker=req.ticker, context=req.context)


@router.post("/workflow")
def run_workflow(req: MultiAgentRequest):
    return svc.run_multi_agent_workflow(req.tickers, agent_ids=req.agent_ids, context=req.context)
