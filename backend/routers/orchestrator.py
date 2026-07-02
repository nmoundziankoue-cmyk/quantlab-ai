"""Agent Orchestration Engine router (M7) — DAG workflows, task queue, execution."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import services.agent_orchestrator as svc
from schemas.orchestrator import (
    CreateWorkflowRequest,
    ExecuteWorkflowRequest,
    WorkflowSchema,
)

router = APIRouter(prefix="/orchestrator", tags=["Agent Orchestrator"])


@router.post("/workflows", response_model=Dict[str, Any])
def create_workflow(req: CreateWorkflowRequest, db: Session = Depends(get_db)):
    """Create a new workflow DAG."""
    dag_dict = req.dag_definition.model_dump() if req.dag_definition else None
    wf = svc.create_workflow(
        db=db,
        name=req.name,
        description=req.description,
        dag_definition=dag_dict,
        priority=req.priority,
        metadata=req.metadata,
    )
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "status": wf.status,
        "priority": wf.priority,
        "created_at": wf.created_at.isoformat(),
    }


@router.get("/workflows", response_model=List[Dict[str, Any]])
def list_workflows(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all workflows, optionally filtered by status."""
    workflows = svc.list_workflows(db, status=status, limit=limit)
    return [
        {
            "id": str(wf.id),
            "name": wf.name,
            "status": wf.status,
            "priority": wf.priority,
            "started_at": wf.started_at.isoformat() if wf.started_at else None,
            "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
            "result_summary": wf.result_summary,
            "created_at": wf.created_at.isoformat(),
        }
        for wf in workflows
    ]


@router.get("/workflows/{workflow_id}", response_model=Dict[str, Any])
def get_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get workflow details including tasks."""
    wf = svc.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    tasks = [
        {
            "id": str(t.id),
            "task_name": t.task_name,
            "agent_id": t.agent_id,
            "status": t.status,
            "duration_ms": t.duration_ms,
            "error_message": t.error_message,
        }
        for t in (wf.tasks or [])
    ]
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "status": wf.status,
        "priority": wf.priority,
        "dag_definition": wf.dag_definition,
        "result_summary": wf.result_summary,
        "tasks": tasks,
        "started_at": wf.started_at.isoformat() if wf.started_at else None,
        "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
        "created_at": wf.created_at.isoformat(),
    }


@router.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
def execute_workflow(
    workflow_id: uuid.UUID,
    req: ExecuteWorkflowRequest,
    db: Session = Depends(get_db),
):
    """Execute a workflow DAG synchronously."""
    global_input = req.global_input or {}
    if req.ticker:
        global_input["ticker"] = req.ticker
    result = svc.execute_workflow(db, workflow_id, global_input=global_input or None)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/workflows/{workflow_id}/timeline", response_model=Dict[str, Any])
def get_workflow_timeline(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return execution timeline for a workflow."""
    result = svc.get_workflow_timeline(db, workflow_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/workflows/{workflow_id}/cancel", response_model=Dict[str, Any])
def cancel_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    """Cancel a pending or running workflow."""
    result = svc.cancel_workflow(db, workflow_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/workflows/{workflow_id}", response_model=Dict[str, Any])
def delete_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a workflow and all its tasks."""
    ok = svc.delete_workflow(db, workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"deleted": str(workflow_id)}


@router.get("/health", response_model=Dict[str, Any])
def get_orchestrator_health(db: Session = Depends(get_db)):
    """Return aggregate health metrics for the orchestration engine."""
    return svc.get_workflow_health(db)


@router.post("/quick-run", response_model=Dict[str, Any])
def quick_run_workflow(
    ticker: str = "AAPL",
    agent_ids: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create and immediately execute a simple sequential workflow."""
    agents = (agent_ids or "market_analyst,fundamental_analyst,risk_analyst").split(",")
    tasks = [
        {"task_name": f"task_{a}", "agent_id": a.strip(), "input_data": {"ticker": ticker}}
        for a in agents
    ]
    wf = svc.create_workflow(
        db=db,
        name=f"Quick Run — {ticker}",
        description=f"Auto-generated workflow for {ticker}",
        dag_definition={"tasks": tasks},
        priority=8,
    )
    result = svc.execute_workflow(db, wf.id, global_input={"ticker": ticker})
    return result
