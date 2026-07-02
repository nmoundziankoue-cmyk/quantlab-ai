"""Tests for M9 Phase 9 — structured logging, request IDs, tracing."""
import json
import logging
import threading
import pytest
from services.structured_logging import (
    JsonFormatter, get_structured_logger, RequestContext, generate_request_id,
    SlowQueryTracker, ErrorAggregator, Tracer, Span, slow_query_tracker, error_aggregator,
)


# ---------------------------------------------------------------------------
# Request context
# ---------------------------------------------------------------------------

class TestRequestContext:
    def setup_method(self):
        RequestContext.clear()

    def test_set_and_get(self):
        RequestContext.set(request_id="abc123", path="/test")
        ctx = RequestContext.get_context()
        assert ctx["request_id"] == "abc123"
        assert ctx["path"] == "/test"

    def test_clear(self):
        RequestContext.set(request_id="xyz")
        RequestContext.clear()
        assert RequestContext.get_context() == {}

    def test_request_id_empty_by_default(self):
        RequestContext.clear()
        assert RequestContext.request_id() == ""

    def test_update(self):
        RequestContext.set(request_id="r1")
        RequestContext.update(user_id="u1")
        ctx = RequestContext.get_context()
        assert ctx["request_id"] == "r1"
        assert ctx["user_id"] == "u1"

    def test_thread_isolation(self):
        results = {}
        RequestContext.set(request_id="main-thread")
        def worker():
            RequestContext.set(request_id="worker-thread")
            results["worker"] = RequestContext.request_id()
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert results["worker"] == "worker-thread"
        assert RequestContext.request_id() == "main-thread"


# ---------------------------------------------------------------------------
# generate_request_id
# ---------------------------------------------------------------------------

class TestGenerateRequestId:
    def test_unique(self):
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100

    def test_format(self):
        rid = generate_request_id()
        parts = rid.split("-")
        assert len(parts) == 5  # UUID4 format


# ---------------------------------------------------------------------------
# JsonFormatter
# ---------------------------------------------------------------------------

class TestJsonFormatter:
    def test_format_produces_json(self):
        fmt = JsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "hello world", (), None)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["message"] == "hello world"
        assert data["level"] == "INFO"
        assert "timestamp" in data

    def test_includes_request_id_when_set(self):
        RequestContext.set(request_id="test-req-123")
        fmt = JsonFormatter()
        record = logging.LogRecord("test", logging.WARNING, "", 0, "warn", (), None)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["request_id"] == "test-req-123"
        RequestContext.clear()


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------

class TestStructuredLogger:
    def test_returns_logger(self):
        logger = get_structured_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_has_json_handler(self):
        logger = get_structured_logger("test.json_handler")
        assert any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers)

    def test_singleton_per_name(self):
        l1 = get_structured_logger("same.name")
        l2 = get_structured_logger("same.name")
        assert l1 is l2


# ---------------------------------------------------------------------------
# SlowQueryTracker
# ---------------------------------------------------------------------------

class TestSlowQueryTracker:
    def test_records_slow_op(self):
        t = SlowQueryTracker(threshold_ms=50.0)
        assert t.record("db_query", 100.0)

    def test_ignores_fast_op(self):
        t = SlowQueryTracker(threshold_ms=200.0)
        assert not t.record("fast_op", 10.0)

    def test_get_slow_ops(self):
        t = SlowQueryTracker(threshold_ms=10.0)
        t.record("op1", 50.0)
        t.record("op2", 30.0)
        ops = t.get_slow_ops()
        assert len(ops) >= 2

    def test_limit(self):
        t = SlowQueryTracker(threshold_ms=1.0)
        for i in range(20):
            t.record(f"op_{i}", 50.0)
        ops = t.get_slow_ops(limit=5)
        assert len(ops) == 5

    def test_stats(self):
        t = SlowQueryTracker(threshold_ms=10.0)
        t.record("x", 50.0)
        s = t.stats()
        assert s["total_recorded"] >= 1
        assert "threshold_ms" in s

    def test_max_history(self):
        t = SlowQueryTracker(threshold_ms=1.0, max_history=5)
        for i in range(10):
            t.record(f"op{i}", 50.0)
        ops = t.get_slow_ops(limit=100)
        assert len(ops) <= 5


# ---------------------------------------------------------------------------
# ErrorAggregator
# ---------------------------------------------------------------------------

class TestErrorAggregator:
    def test_record_and_summary(self):
        agg = ErrorAggregator()
        agg.record("ValueError", "invalid input")
        agg.record("ValueError", "another error")
        agg.record("KeyError", "missing key")
        s = agg.summary()
        assert s["by_type"]["ValueError"] == 2
        assert s["by_type"]["KeyError"] == 1

    def test_get_recent(self):
        agg = ErrorAggregator()
        agg.record("DBError", "connection refused")
        recent = agg.get_recent("DBError")
        assert len(recent) == 1
        assert "connection refused" in recent[0]["message"]

    def test_get_recent_limit(self):
        agg = ErrorAggregator(max_per_type=3)
        for i in range(10):
            agg.record("TestError", f"error {i}")
        recent = agg.get_recent("TestError")
        assert len(recent) <= 3

    def test_nonexistent_type(self):
        agg = ErrorAggregator()
        assert agg.get_recent("NonExistent") == []


# ---------------------------------------------------------------------------
# Tracer and Span
# ---------------------------------------------------------------------------

class TestTracer:
    def test_start_span(self):
        t = Tracer()
        span = t.start_span("test_operation")
        assert span.name == "test_operation"
        assert span.trace_id

    def test_end_span_records(self):
        t = Tracer()
        span = t.start_span("op")
        t.end_span(span)
        spans = t.recent_spans()
        assert any(s["name"] == "op" for s in spans)

    def test_parent_span_shares_trace_id(self):
        t = Tracer()
        parent = t.start_span("parent")
        child = t.start_span("child", parent=parent)
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id

    def test_duration_computed(self):
        import time
        t = Tracer()
        span = t.start_span("timed")
        time.sleep(0.01)
        span.end()
        assert span.duration_ms > 5

    def test_recent_spans_limit(self):
        t = Tracer()
        for i in range(10):
            s = t.start_span(f"op_{i}")
            t.end_span(s)
        spans = t.recent_spans(limit=5)
        assert len(spans) == 5
