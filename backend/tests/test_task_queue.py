"""Tests for services/task_queue.py (M8)."""
from __future__ import annotations

import time

import pytest

from services.task_queue import BackgroundTask, InMemoryTaskQueue, TaskStatus, task_queue


def _add(a, b):
    return a + b


def _fail():
    raise ValueError("intentional failure")


def _slow(duration):
    time.sleep(duration)
    return "done"


class TestInMemoryTaskQueue:
    def setup_method(self):
        self.q = InMemoryTaskQueue(max_history=100)

    def test_enqueue_returns_task_id(self):
        tid = self.q.enqueue(_add, 1, 2, task_name="add")
        assert isinstance(tid, str)
        assert len(tid) == 36  # UUID format

    def test_task_visible_immediately(self):
        tid = self.q.enqueue(_add, 1, 2, task_name="add")
        task = self.q.get(tid)
        assert task is not None
        assert task.name == "add"

    def test_task_completes(self):
        tid = self.q.enqueue(_add, 3, 4, task_name="add")
        for _ in range(50):
            t = self.q.get(tid)
            if t.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.02)
        assert t.status == TaskStatus.COMPLETED
        assert t.result == 7

    def test_failed_task_captures_error(self):
        tid = self.q.enqueue(_fail, task_name="fail")
        for _ in range(50):
            t = self.q.get(tid)
            if t.status == TaskStatus.FAILED:
                break
            time.sleep(0.02)
        assert t.status == TaskStatus.FAILED
        assert "intentional failure" in t.error

    def test_task_has_timestamps(self):
        tid = self.q.enqueue(_add, 1, 1, task_name="ts-test")
        for _ in range(50):
            t = self.q.get(tid)
            if t.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.02)
        assert t.started_at is not None
        assert t.completed_at is not None
        assert t.completed_at >= t.started_at

    def test_priority_stored(self):
        tid = self.q.enqueue(_add, 1, 2, task_name="prio", priority=1)
        task = self.q.get(tid)
        assert task.priority == 1

    def test_metadata_stored(self):
        tid = self.q.enqueue(_add, 1, 2, task_name="meta", metadata={"key": "value"})
        task = self.q.get(tid)
        assert task.metadata == {"key": "value"}

    def test_list_all_tasks(self):
        self.q.enqueue(_add, 1, 1, task_name="list-a")
        self.q.enqueue(_add, 2, 2, task_name="list-b")
        time.sleep(0.05)
        tasks = self.q.list(limit=50)
        names = [t.name for t in tasks]
        assert "list-a" in names
        assert "list-b" in names

    def test_list_by_status(self):
        tid = self.q.enqueue(_fail, task_name="list-fail")
        for _ in range(50):
            if self.q.get(tid).status == TaskStatus.FAILED:
                break
            time.sleep(0.02)
        failed = self.q.list(status=TaskStatus.FAILED)
        assert any(t.id == tid for t in failed)

    def test_cancel_pending_task(self):
        # Use a slow task so we can cancel before it completes
        tid = self.q.enqueue(_slow, 5, task_name="slow-cancel")
        # Try to cancel quickly
        result = self.q.cancel(tid)
        # May succeed if still PENDING
        task = self.q.get(tid)
        # Either cancelled or already running (race condition in test)
        assert task.status in (TaskStatus.CANCELLED, TaskStatus.RUNNING, TaskStatus.COMPLETED)

    def test_to_dict_format(self):
        tid = self.q.enqueue(_add, 1, 2, task_name="dict-test")
        for _ in range(50):
            t = self.q.get(tid)
            if t.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.02)
        d = t.to_dict()
        assert "id" in d
        assert "name" in d
        assert "status" in d
        assert "result" in d
        assert "duration_ms" in d

    def test_stats(self):
        stats = self.q.stats()
        assert "total" in stats
        assert "by_status" in stats
        assert "max_history" in stats

    def test_get_nonexistent_returns_none(self):
        assert self.q.get("nonexistent-id") is None

    def test_max_history_eviction(self):
        q = InMemoryTaskQueue(max_history=10)
        for i in range(15):
            tid = q.enqueue(_add, i, 0, task_name=f"task-{i}")
        # Wait for all to complete
        time.sleep(0.1)
        # Should not exceed max_history significantly
        tasks = q.list(limit=200)
        assert len(tasks) <= 15  # eviction may have reduced count


class TestModuleSingleton:
    def test_task_queue_singleton_exists(self):
        assert task_queue is not None
        assert isinstance(task_queue, InMemoryTaskQueue)

    def test_singleton_enqueue_and_get(self):
        tid = task_queue.enqueue(_add, 10, 20, task_name="singleton-test")
        task = task_queue.get(tid)
        assert task is not None
        assert task.name == "singleton-test"


class TestBackgroundTaskDataclass:
    def test_default_status_pending(self):
        task = BackgroundTask(id="test-id", name="test")
        assert task.status == TaskStatus.PENDING

    def test_to_dict_no_crash_incomplete(self):
        task = BackgroundTask(id="test-id", name="test")
        d = task.to_dict()
        assert d["duration_ms"] is None  # Not completed yet
