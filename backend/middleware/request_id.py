"""M9 Phase 9 — Request ID middleware.

Injects X-Request-ID into every request and response.
Stores request context (request_id, path, method) for structured logging.
"""
from __future__ import annotations
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from services.structured_logging import RequestContext, slow_query_tracker
from services.metrics import metrics


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        RequestContext.set(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        t0 = time.monotonic()
        response: Response = await call_next(request)
        duration_s = time.monotonic() - t0
        duration_ms = duration_s * 1000

        slow_query_tracker.record(
            operation=f"{request.method} {request.url.path}",
            duration_ms=duration_ms,
            status_code=response.status_code,
        )

        # Record metrics
        metrics.inc_request(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_s=duration_s,
        )
        if response.status_code >= 400:
            metrics.inc_error(path=request.url.path, status=response.status_code)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        RequestContext.clear()
        return response
