"""M9 Phase 9 — Structured logging, request IDs, distributed tracing skeleton.

Provides:
- ``get_structured_logger`` — JSON-formatted logger
- ``RequestContext`` — thread-local request context (request_id, user_id, etc.)
- ``slow_query_tracker`` — records slow operations
- ``error_aggregator`` — aggregates errors by type
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = _request_context.get_context()
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if ctx:
            log_obj.update(ctx)
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def get_structured_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


# ---------------------------------------------------------------------------
# Request context (thread-local)
# ---------------------------------------------------------------------------

class _RequestContextStore(threading.local):
    def __init__(self):
        self._ctx: Dict[str, Any] = {}

    def set(self, **kwargs) -> None:
        self._ctx = kwargs

    def update(self, **kwargs) -> None:
        self._ctx.update(kwargs)

    def get_context(self) -> Dict[str, Any]:
        return dict(self._ctx)

    def clear(self) -> None:
        self._ctx = {}

    def request_id(self) -> str:
        return self._ctx.get("request_id", "")


_request_context = _RequestContextStore()

RequestContext = _request_context  # public alias


def generate_request_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Slow query tracker
# ---------------------------------------------------------------------------

@dataclass
class SlowOperation:
    operation: str
    duration_ms: float
    request_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)


class SlowQueryTracker:
    def __init__(self, threshold_ms: float = 200.0, max_history: int = 100) -> None:
        self._threshold = threshold_ms
        self._history: Deque[SlowOperation] = deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._total_recorded = 0

    def record(self, operation: str, duration_ms: float, **metadata) -> bool:
        if duration_ms < self._threshold:
            return False
        op = SlowOperation(
            operation=operation,
            duration_ms=round(duration_ms, 2),
            request_id=_request_context.request_id(),
            metadata=metadata,
        )
        with self._lock:
            self._history.append(op)
            self._total_recorded += 1
        return True

    def get_slow_ops(self, limit: int = 20) -> List[dict]:
        with self._lock:
            ops = list(self._history)[-limit:]
        return [op.__dict__ for op in reversed(ops)]

    def stats(self) -> dict:
        with self._lock:
            return {
                "threshold_ms": self._threshold,
                "total_recorded": self._total_recorded,
                "history_size": len(self._history),
            }


slow_query_tracker = SlowQueryTracker()


# ---------------------------------------------------------------------------
# Error aggregator
# ---------------------------------------------------------------------------

class ErrorAggregator:
    def __init__(self, max_per_type: int = 20) -> None:
        self._counts: Dict[str, int] = defaultdict(int)
        self._recent: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=max_per_type))
        self._lock = threading.Lock()

    def record(self, error_type: str, message: str, **context) -> None:
        entry = {
            "message": message,
            "request_id": _request_context.request_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **context,
        }
        with self._lock:
            self._counts[error_type] += 1
            self._recent[error_type].append(entry)

    def summary(self) -> dict:
        with self._lock:
            return {
                "total_types": len(self._counts),
                "by_type": dict(self._counts),
            }

    def get_recent(self, error_type: str, limit: int = 10) -> List[dict]:
        with self._lock:
            items = list(self._recent.get(error_type, []))
        return items[-limit:]


error_aggregator = ErrorAggregator()


# ---------------------------------------------------------------------------
# Simple span / trace context (OpenTelemetry-compatible shape)
# ---------------------------------------------------------------------------

@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None
    attributes: dict = field(default_factory=dict)

    def end(self) -> None:
        self.end_time = time.monotonic()

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.monotonic() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": round(self.duration_ms, 3),
            "attributes": self.attributes,
        }


class Tracer:
    def __init__(self, service_name: str = "apexquant") -> None:
        self.service_name = service_name
        self._spans: Deque[Span] = deque(maxlen=500)
        self._lock = threading.Lock()

    def start_span(self, name: str, parent: Optional[Span] = None) -> Span:
        trace_id = parent.trace_id if parent else uuid.uuid4().hex
        span = Span(name=name, trace_id=trace_id, parent_span_id=parent.span_id if parent else None)
        return span

    def end_span(self, span: Span) -> None:
        span.end()
        with self._lock:
            self._spans.append(span)

    def recent_spans(self, limit: int = 50) -> List[dict]:
        with self._lock:
            return [s.to_dict() for s in list(self._spans)[-limit:]]


tracer = Tracer()
