"""Tests for the Agent Orchestration Engine (M7)."""
from __future__ import annotations

import uuid
import pytest

import services.agent_orchestrator as svc
from models.orchestrator import AgentWorkflow, WorkflowTask


# ---------------------------------------------------------------------------
# Workflow CRUD
# ---------------------------------------------------------------------------

class TestWorkflowCRUD:
    def test_create_workflow_minimal(self, db):
        wf = svc.create_workflow(db, name="Test Workflow")
        assert wf.id is not None
        assert wf.name == "Test Workflow"
        assert wf.status == "PENDING"

    def test_create_workflow_with_dag(self, db):
        dag = {"tasks": [
            {"task_name": "task_a", "agent_id": "market_analyst", "depends_on": []},
            {"task_name": "task_b", "agent_id": "risk_analyst", "depends_on": ["task_a"]},
        ]}
        wf = svc.create_workflow(db, name="DAG Workflow", dag_definition=dag)
        assert len(wf.tasks) == 2

    def test_create_workflow_with_priority(self, db):
        wf = svc.create_workflow(db, name="High Priority", priority=9)
        assert wf.priority == 9

    def test_get_workflow_exists(self, db):
        wf = svc.create_workflow(db, name="Get Test")
        fetched = svc.get_workflow(db, wf.id)
        assert fetched is not None
        assert fetched.id == wf.id

    def test_get_workflow_not_found(self, db):
        result = svc.get_workflow(db, uuid.uuid4())
        assert result is None

    def test_list_workflows_empty(self, db):
        result = svc.list_workflows(db, limit=100)
        assert isinstance(result, list)

    def test_list_workflows_returns_created(self, db):
        svc.create_workflow(db, name="List Test Workflow")
        result = svc.list_workflows(db, limit=100)
        names = [w.name for w in result]
        assert "List Test Workflow" in names

    def test_list_workflows_filter_by_status(self, db):
        svc.create_workflow(db, name="Pending WF")
        pending = svc.list_workflows(db, status="PENDING", limit=100)
        assert all(w.status == "PENDING" for w in pending)

    def test_delete_workflow(self, db):
        wf = svc.create_workflow(db, name="Delete Me")
        ok = svc.delete_workflow(db, wf.id)
        assert ok is True
        assert svc.get_workflow(db, wf.id) is None

    def test_delete_workflow_not_found(self, db):
        ok = svc.delete_workflow(db, uuid.uuid4())
        assert ok is False


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_no_deps(self):
        tasks = [
            {"task_name": "a", "depends_on": []},
            {"task_name": "b", "depends_on": []},
        ]
        waves = svc._topological_sort(tasks)
        assert len(waves) >= 1
        flat = [t for wave in waves for t in wave]
        assert "a" in flat
        assert "b" in flat

    def test_sequential_deps(self):
        tasks = [
            {"task_name": "a", "depends_on": []},
            {"task_name": "b", "depends_on": ["a"]},
            {"task_name": "c", "depends_on": ["b"]},
        ]
        waves = svc._topological_sort(tasks)
        # a must come before b, b before c
        flat = [t for wave in waves for t in wave]
        assert flat.index("a") < flat.index("b")
        assert flat.index("b") < flat.index("c")

    def test_parallel_deps(self):
        tasks = [
            {"task_name": "root", "depends_on": []},
            {"task_name": "branch_a", "depends_on": ["root"]},
            {"task_name": "branch_b", "depends_on": ["root"]},
        ]
        waves = svc._topological_sort(tasks)
        flat = [t for wave in waves for t in wave]
        assert flat.index("root") < flat.index("branch_a")
        assert flat.index("root") < flat.index("branch_b")

    def test_single_task(self):
        tasks = [{"task_name": "solo", "depends_on": []}]
        waves = svc._topological_sort(tasks)
        assert any("solo" in wave for wave in waves)

    def test_empty_tasks(self):
        waves = svc._topological_sort([])
        assert waves == []


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------

class TestWorkflowExecution:
    def test_execute_empty_workflow(self, db):
        wf = svc.create_workflow(db, name="Empty WF")
        result = svc.execute_workflow(db, wf.id, global_input={"ticker": "AAPL"})
        assert result["status"] == "COMPLETED"

    def test_execute_single_task_workflow(self, db):
        dag = {"tasks": [
            {"task_name": "market_task", "agent_id": "market_analyst", "input_data": {"ticker": "AAPL"}},
        ]}
        wf = svc.create_workflow(db, name="Single Task", dag_definition=dag)
        result = svc.execute_workflow(db, wf.id, global_input={"ticker": "AAPL"})
        assert result["status"] in ("COMPLETED", "FAILED")
        assert len(result["tasks"]) == 1

    def test_execute_workflow_not_found(self, db):
        result = svc.execute_workflow(db, uuid.uuid4())
        assert "error" in result

    def test_execute_already_running_returns_error(self, db):
        wf = svc.create_workflow(db, name="Running WF")
        wf.status = "RUNNING"
        db.flush()
        result = svc.execute_workflow(db, wf.id)
        assert "error" in result

    def test_execute_already_completed_returns_error(self, db):
        wf = svc.create_workflow(db, name="Completed WF")
        wf.status = "COMPLETED"
        db.flush()
        result = svc.execute_workflow(db, wf.id)
        assert "error" in result

    def test_execute_updates_workflow_status(self, db):
        wf = svc.create_workflow(db, name="Status Update WF")
        svc.execute_workflow(db, wf.id, global_input={"ticker": "MSFT"})
        db.refresh(wf)
        assert wf.status in ("COMPLETED", "FAILED")

    def test_execute_sets_completed_at(self, db):
        wf = svc.create_workflow(db, name="Timestamp WF")
        svc.execute_workflow(db, wf.id)
        db.refresh(wf)
        assert wf.completed_at is not None

    def test_result_contains_summary(self, db):
        wf = svc.create_workflow(db, name="Summary WF")
        result = svc.execute_workflow(db, wf.id)
        assert "summary" in result

    def test_multi_task_execution(self, db):
        dag = {"tasks": [
            {"task_name": "task_1", "agent_id": "market_analyst"},
            {"task_name": "task_2", "agent_id": "fundamental_analyst", "depends_on": ["task_1"]},
        ]}
        wf = svc.create_workflow(db, name="Multi Task", dag_definition=dag)
        result = svc.execute_workflow(db, wf.id, global_input={"ticker": "AAPL"})
        assert len(result["tasks"]) == 2


# ---------------------------------------------------------------------------
# Workflow timeline
# ---------------------------------------------------------------------------

class TestWorkflowTimeline:
    def test_get_timeline_not_found(self, db):
        result = svc.get_workflow_timeline(db, uuid.uuid4())
        assert "error" in result

    def test_get_timeline_after_execution(self, db):
        dag = {"tasks": [{"task_name": "t1", "agent_id": "market_analyst"}]}
        wf = svc.create_workflow(db, name="Timeline WF", dag_definition=dag)
        svc.execute_workflow(db, wf.id, global_input={"ticker": "AAPL"})
        timeline = svc.get_workflow_timeline(db, wf.id)
        assert "tasks" in timeline
        assert timeline["workflow_id"] == str(wf.id)

    def test_timeline_includes_task_details(self, db):
        dag = {"tasks": [{"task_name": "timeline_task", "agent_id": "risk_analyst"}]}
        wf = svc.create_workflow(db, name="Detail Timeline WF", dag_definition=dag)
        svc.execute_workflow(db, wf.id, global_input={"ticker": "AAPL"})
        timeline = svc.get_workflow_timeline(db, wf.id)
        assert len(timeline["tasks"]) == 1
        assert timeline["tasks"][0]["task_name"] == "timeline_task"


# ---------------------------------------------------------------------------
# Cancel & health
# ---------------------------------------------------------------------------

class TestCancelAndHealth:
    def test_cancel_pending_workflow(self, db):
        wf = svc.create_workflow(db, name="Cancel Me")
        result = svc.cancel_workflow(db, wf.id)
        assert result["status"] == "CANCELLED"

    def test_cancel_completed_workflow_returns_error(self, db):
        wf = svc.create_workflow(db, name="Already Done")
        wf.status = "COMPLETED"
        db.flush()
        result = svc.cancel_workflow(db, wf.id)
        assert "error" in result

    def test_cancel_not_found(self, db):
        result = svc.cancel_workflow(db, uuid.uuid4())
        assert "error" in result

    def test_get_health_returns_counts(self, db):
        svc.create_workflow(db, name="Health WF 1")
        svc.create_workflow(db, name="Health WF 2")
        health = svc.get_workflow_health(db)
        assert "total_workflows" in health
        assert "by_status" in health
        assert health["total_workflows"] >= 2
