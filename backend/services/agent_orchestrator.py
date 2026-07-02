"""Agent Orchestration Engine — DAG execution, task queue, parallel dispatch (M7).

Implements deterministic DAG workflow execution over the existing 12-agent system.
No background threads: all execution is synchronous and transactional.
"""
from __future__ import annotations

import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.orchestrator import AgentWorkflow, WorkflowTask
import services.agents as agents_svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _topological_sort(tasks: List[Dict[str, Any]]) -> List[List[str]]:
    """Return task names grouped into execution waves (topological levels)."""
    name_to_deps: Dict[str, List[str]] = {}
    for t in tasks:
        deps = t.get("depends_on") or []
        name_to_deps[t["task_name"]] = deps if isinstance(deps, list) else []

    # Kahn's algorithm
    in_degree: Dict[str, int] = {n: 0 for n in name_to_deps}
    for deps in name_to_deps.values():
        for d in deps:
            in_degree[d] = in_degree.get(d, 0)
    for name, deps in name_to_deps.items():
        for _ in deps:
            in_degree[name] = in_degree.get(name, 0) + 1

    queue: deque = deque([n for n, deg in in_degree.items() if deg == 0])
    waves: List[List[str]] = []
    while queue:
        wave = list(queue)
        queue.clear()
        waves.append(wave)
        for name in wave:
            for other, deps in name_to_deps.items():
                if name in deps:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)
    return waves


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_workflow(
    db: Session,
    name: str,
    description: Optional[str] = None,
    dag_definition: Optional[Dict[str, Any]] = None,
    priority: int = 5,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentWorkflow:
    workflow = AgentWorkflow(
        name=name,
        description=description,
        dag_definition=dag_definition,
        priority=priority,
        metadata_=metadata,
        status="PENDING",
    )
    db.add(workflow)
    db.flush()

    # Pre-create task rows from dag_definition
    tasks_def = (dag_definition or {}).get("tasks", [])
    for task_def in tasks_def:
        task = WorkflowTask(
            workflow_id=workflow.id,
            agent_id=task_def.get("agent_id", "market_analyst"),
            task_name=task_def.get("task_name", f"task_{uuid.uuid4().hex[:8]}"),
            depends_on=task_def.get("depends_on"),
            input_data=task_def.get("input_data"),
            status="PENDING",
        )
        db.add(task)
    db.flush()
    return workflow


def get_workflow(db: Session, workflow_id: uuid.UUID) -> Optional[AgentWorkflow]:
    return db.get(AgentWorkflow, workflow_id)


def list_workflows(
    db: Session,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[AgentWorkflow]:
    from sqlalchemy import select
    stmt = select(AgentWorkflow).order_by(AgentWorkflow.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(AgentWorkflow.status == status)
    return list(db.execute(stmt).scalars())


def delete_workflow(db: Session, workflow_id: uuid.UUID) -> bool:
    wf = db.get(AgentWorkflow, workflow_id)
    if not wf:
        return False
    db.delete(wf)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------

def execute_workflow(
    db: Session,
    workflow_id: uuid.UUID,
    global_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a workflow DAG synchronously. Updates task/workflow status in-place."""
    wf = db.get(AgentWorkflow, workflow_id)
    if not wf:
        return {"error": f"Workflow {workflow_id} not found"}

    if wf.status in ("RUNNING", "COMPLETED"):
        return {"error": f"Workflow is already {wf.status}"}

    # Mark workflow as running
    wf.status = "RUNNING"
    wf.started_at = _now()
    db.flush()

    from sqlalchemy import select
    tasks = list(
        db.execute(select(WorkflowTask).where(WorkflowTask.workflow_id == wf.id)).scalars()
    )
    task_map = {t.task_name: t for t in tasks}

    if not tasks:
        wf.status = "COMPLETED"
        wf.completed_at = _now()
        wf.result_summary = {"message": "No tasks to execute", "tasks_completed": 0}
        db.flush()
        return {"workflow_id": str(workflow_id), "status": "COMPLETED", "tasks": [], "summary": wf.result_summary}

    # Build execution waves
    task_defs = [
        {"task_name": t.task_name, "depends_on": t.depends_on or []}
        for t in tasks
    ]
    waves = _topological_sort(task_defs)

    results: List[Dict[str, Any]] = []
    task_outputs: Dict[str, Any] = {}
    all_success = True

    for wave in waves:
        for task_name in wave:
            task = task_map.get(task_name)
            if task is None:
                continue

            task.status = "RUNNING"
            task.started_at = _now()
            db.flush()

            # Merge global input + task-specific input + upstream outputs
            input_data = {**(global_input or {}), **(task.input_data or {})}
            for dep in (task.depends_on or []):
                if dep in task_outputs:
                    input_data[f"upstream_{dep}"] = task_outputs[dep]

            ticker = input_data.get("ticker", "AAPL")
            try:
                output = agents_svc.run_agent(task.agent_id, ticker)
                task.status = "COMPLETED"
                task.output_data = output
                task_outputs[task_name] = output
                t_end = _now()
                task.completed_at = t_end
                if task.started_at:
                    task.duration_ms = int((t_end - task.started_at).total_seconds() * 1000)
            except Exception as exc:
                task.status = "FAILED"
                task.error_message = str(exc)
                all_success = False
                task.completed_at = _now()

            db.flush()
            results.append({
                "task_name": task_name,
                "agent_id": task.agent_id,
                "status": task.status,
                "output": task.output_data,
                "error": task.error_message,
            })

    wf.status = "COMPLETED" if all_success else "FAILED"
    wf.completed_at = _now()
    wf.result_summary = {
        "tasks_total": len(tasks),
        "tasks_completed": sum(1 for r in results if r["status"] == "COMPLETED"),
        "tasks_failed": sum(1 for r in results if r["status"] == "FAILED"),
    }
    db.flush()

    return {
        "workflow_id": str(workflow_id),
        "status": wf.status,
        "tasks": results,
        "summary": wf.result_summary,
    }


def get_workflow_timeline(
    db: Session, workflow_id: uuid.UUID
) -> Dict[str, Any]:
    """Return execution timeline for a workflow."""
    wf = db.get(AgentWorkflow, workflow_id)
    if not wf:
        return {"error": "Workflow not found"}

    from sqlalchemy import select
    tasks = list(
        db.execute(
            select(WorkflowTask)
            .where(WorkflowTask.workflow_id == wf.id)
            .order_by(WorkflowTask.created_at)
        ).scalars()
    )

    return {
        "workflow_id": str(workflow_id),
        "name": wf.name,
        "status": wf.status,
        "started_at": wf.started_at.isoformat() if wf.started_at else None,
        "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
        "tasks": [
            {
                "task_name": t.task_name,
                "agent_id": t.agent_id,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ],
    }


def cancel_workflow(db: Session, workflow_id: uuid.UUID) -> Dict[str, Any]:
    wf = db.get(AgentWorkflow, workflow_id)
    if not wf:
        return {"error": "Workflow not found"}
    if wf.status == "COMPLETED":
        return {"error": "Cannot cancel a completed workflow"}
    wf.status = "CANCELLED"
    wf.completed_at = _now()
    db.flush()
    return {"workflow_id": str(workflow_id), "status": "CANCELLED"}


def get_workflow_health(db: Session) -> Dict[str, Any]:
    """Return aggregate health metrics for all workflows."""
    from sqlalchemy import select, func
    from sqlalchemy import case as sa_case

    wfs = list(db.execute(select(AgentWorkflow)).scalars())
    status_counts: Dict[str, int] = defaultdict(int)
    for wf in wfs:
        status_counts[wf.status] += 1

    return {
        "total_workflows": len(wfs),
        "by_status": dict(status_counts),
        "active_workflows": status_counts.get("RUNNING", 0),
        "success_rate": round(
            status_counts.get("COMPLETED", 0) / max(len(wfs), 1) * 100, 1
        ),
    }
