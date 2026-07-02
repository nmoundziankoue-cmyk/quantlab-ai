"""Security headers middleware (M8).

Adds OWASP-recommended HTTP security headers to every response.
Register via ``app.add_middleware(SecurityHeadersMiddleware)``.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add CSP, HSTS, and other security headers to all responses."""

    _HEADERS = {
        # Prevent framing (clickjacking)
        "X-Frame-Options": "DENY",
        # Block MIME sniffing
        "X-Content-Type-Options": "nosniff",
        # XSS filter (legacy browsers)
        "X-XSS-Protection": "1; mode=block",
        # Don't leak referer cross-origin
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # HSTS — 1 year, include sub-domains
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        # Content Security Policy
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        ),
        # Permissions policy
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        # Cache control for API responses
        "Cache-Control": "no-store",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in self._HEADERS.items():
            response.headers.setdefault(name, value)
        return response
