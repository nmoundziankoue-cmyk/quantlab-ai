"""Request body size limit middleware (M10 Phase 9).

Rejects requests with Content-Length exceeding the configured maximum.
Default: 10 MB.  Exempt: WebSocket upgrades (no body).
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


_DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
            except ValueError:
                size = 0
            if size > self._max_bytes:
                return JSONResponse(
                    {"detail": f"Request body too large. Maximum allowed: {self._max_bytes // (1024 * 1024)} MB"},
                    status_code=413,
                )
        return await call_next(request)
