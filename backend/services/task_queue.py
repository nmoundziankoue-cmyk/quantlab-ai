"""In-process background task queue with Celery-compatible interface.

When Celery is installed and configured, swap the ``enqueue_task`` call with a
proper Celery task. Until then, this module runs tasks in daemon threads so the
API never blocks.

Usage::

    from services.task_queue import task_queue

    task_id = task_queue.enqueue(my_function, arg1, arg2, task_name="my-task")
    task = task_queue.get(task_id)
    print(task.status, task.result)
"""
from __future__ import annotations

import logging
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class BackgroundTask:
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round((self.completed_at - self.started_at) * 1000, 1)
            if self.completed_at and self.started_at
            else None,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class InMemoryTaskQueue:
    """Thread-safe in-process task queue.

    Tasks run in daemon threads so they don't block the event loop. Completed
    tasks are kept in memory for up to ``max_history`` entries.
    """

    def __init__(self, max_history: int = 500) -> None:
        self._tasks: Dict[str, BackgroundTask] = {}
        self._lock = threading.RLock()
        self._max_history = max_history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(
        self,
        func: Callable,
        *args: Any,
        task_name: str = "task",
        priority: int = 5,
        metadata: Optional[Dict] = None,
        **kwargs: Any,
    ) -> str:
        task_id = str(uuid.uuid4())
        task = BackgroundTask(
            id=task_id,
            name=task_name,
            priority=priority,
            metadata=metadata or {},
        )
        with self._lock:
            self._evict_if_needed()
            self._tasks[task_id] = task

        thread = threading.Thread(
            target=self._run,
            args=(task, func, args, kwargs),
            daemon=True,
            name=f"task-{task_name}-{task_id[:8]}",
        )
        thread.start()
        logger.info("Enqueued task %s (id=%s, priority=%d)", task_name, task_id, priority)
        return task_id

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def list(
        self,
        *,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        name_prefix: Optional[str] = None,
    ) -> List[BackgroundTask]:
        with self._lock:
            tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if name_prefix:
            tasks = [t for t in tasks if t.name.startswith(name_prefix)]

        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def cancel(self, task_id: str) -> bool:
        """Mark a PENDING task as cancelled (running tasks cannot be stopped)."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False

    def stats(self) -> dict:
        with self._lock:
            counts: Dict[str, int] = {}
            for t in self._tasks.values():
                counts[t.status.value] = counts.get(t.status.value, 0) + 1
        return {
            "total": sum(counts.values()),
            "by_status": counts,
            "max_history": self._max_history,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(self, task: BackgroundTask, func: Callable, args: tuple, kwargs: dict) -> None:
        with self._lock:
            if task.status == TaskStatus.CANCELLED:
                return
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

        try:
            result = func(*args, **kwargs)
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = time.time()
            logger.info("Task %s completed (id=%s)", task.name, task.id)
        except Exception as exc:
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                task.completed_at = time.time()
            logger.error("Task %s failed (id=%s): %s", task.name, task.id, exc)
            logger.debug(traceback.format_exc())

    def _evict_if_needed(self) -> None:
        """Remove oldest completed/failed tasks when at capacity."""
        if len(self._tasks) < self._max_history:
            return
        terminal = [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        terminal.sort(key=lambda t: t.created_at)
        to_remove = max(1, len(terminal) // 4)
        for t in terminal[:to_remove]:
            del self._tasks[t.id]


# Module-level singleton
task_queue = InMemoryTaskQueue()
