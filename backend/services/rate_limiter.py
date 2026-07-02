"""In-memory token-bucket rate limiter with optional Redis backend.

Usage::

    from services.rate_limiter import rate_limiter

    # Returns True if the request is allowed, False if rate-limited
    allowed = rate_limiter.check("user:uuid-abc", rate=10, capacity=20)

    # Convenience for IP-based limiting
    allowed = rate_limiter.check_ip("192.168.1.1", rate=30, capacity=60)
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class _Bucket:
    """Single token-bucket entry (not thread-safe on its own)."""

    __slots__ = ("tokens", "last_refill")

    def __init__(self, capacity: float) -> None:
        self.tokens: float = capacity
        self.last_refill: float = time.monotonic()


class RateLimiter:
    """Thread-safe token-bucket rate limiter.

    Each ``key`` gets its own bucket. Tokens refill at ``rate`` per second up
    to ``capacity``. Stale buckets (no activity for >``cleanup_after_s``
    seconds) are evicted periodically.
    """

    def __init__(self, cleanup_after_s: float = 3600) -> None:
        self._buckets: Dict[str, _Bucket] = {}
        self._lock = threading.Lock()
        self._cleanup_after_s = cleanup_after_s
        self._last_cleanup: float = time.monotonic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(
        self,
        key: str,
        *,
        rate: float = 10.0,
        capacity: int = 20,
        tokens: int = 1,
    ) -> bool:
        """Return True if the request may proceed, False if rate-limited."""
        with self._lock:
            self._maybe_cleanup()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(capacity)
                self._buckets[key] = bucket

            now = time.monotonic()
            elapsed = now - bucket.last_refill
            bucket.tokens = min(float(capacity), bucket.tokens + elapsed * rate)
            bucket.last_refill = now

            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                return True
            return False

    def check_ip(self, ip: str, *, rate: float = 30.0, capacity: int = 60) -> bool:
        return self.check(f"ip:{ip}", rate=rate, capacity=capacity)

    def check_user(self, user_id: str, *, rate: float = 60.0, capacity: int = 120) -> bool:
        return self.check(f"user:{user_id}", rate=rate, capacity=capacity)

    def check_endpoint(
        self, key: str, endpoint: str, *, rate: float = 5.0, capacity: int = 10
    ) -> bool:
        return self.check(f"ep:{endpoint}:{key}", rate=rate, capacity=capacity)

    def reset(self, key: str) -> None:
        """Remove a specific bucket (e.g. after successful auth)."""
        with self._lock:
            self._buckets.pop(key, None)

    def remaining(self, key: str, capacity: int, rate: float) -> Tuple[float, float]:
        """Return (tokens_remaining, reset_in_seconds) without consuming a token."""
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return float(capacity), 0.0
            now = time.monotonic()
            elapsed = now - bucket.last_refill
            tokens = min(float(capacity), bucket.tokens + elapsed * rate)
            deficit = float(capacity) - tokens
            reset_in = deficit / rate if (rate > 0 and deficit > 0) else 0.0
            return tokens, reset_in

    def stats(self) -> dict:
        with self._lock:
            return {
                "active_buckets": len(self._buckets),
                "cleanup_interval_s": self._cleanup_after_s,
            }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _maybe_cleanup(self) -> None:
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_after_s:
            return
        cutoff = now - self._cleanup_after_s
        stale = [k for k, b in self._buckets.items() if b.last_refill < cutoff]
        for k in stale:
            del self._buckets[k]
        self._last_cleanup = now


# Module-level singleton
rate_limiter = RateLimiter()

# ------------------------------------------------------------------
# Convenience decorators / helpers for FastAPI
# ------------------------------------------------------------------

from functools import wraps
from fastapi import HTTPException, Request, status


def limit(key_fn=None, *, rate: float = 10.0, capacity: int = 20):
    """Raise 429 when rate-limited. ``key_fn`` receives the FastAPI ``Request``."""

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            key_src = key_fn(request) if key_fn else (request.client.host if request.client else "global")
            if not rate_limiter.check(key_src, rate=rate, capacity=capacity):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please slow down.",
                    headers={"Retry-After": "1"},
                )
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def check_rate_limit(request: Request, rate: float = 30.0, capacity: int = 60) -> None:
    """Call inside a FastAPI endpoint to enforce IP-based rate limiting."""
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check_ip(ip, rate=rate, capacity=capacity):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded.",
            headers={"Retry-After": "1"},
        )
