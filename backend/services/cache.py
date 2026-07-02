"""Unified cache with Redis backend and in-memory TTL fallback.

Usage::

    from services.cache import cache

    cache.set("quote:AAPL", data, ttl=30)
    data = cache.get("quote:AAPL")       # None on miss / expiry
    cache.delete("quote:AAPL")
    cache.clear_prefix("quote:")          # invalidate all quote keys

    # Token blacklist (requires Redis for cross-process consistency)
    cache.revoke_token(jti, ttl_seconds)
    cache.is_token_revoked(jti)           # True if revoked

    # Pub/Sub (Redis only — no-op in memory mode)
    cache.publish("channel:name", {"event": "update"})
    pubsub = cache.get_pubsub()           # None in memory mode

Redis is used when ``settings.redis_url`` is non-empty and the server is
reachable.  Any connection failure causes a silent fallback to the in-memory
store — no exception is raised to the caller.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Namespace prefix for all Redis keys to avoid collisions in shared instances.
_NAMESPACE = "quant:"
_BLACKLIST_PREFIX = f"{_NAMESPACE}blacklist:"


class _MemoryStore:
    """Thread-safe-enough TTL dict for single-process use."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._data[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def clear_prefix(self, prefix: str) -> None:
        for k in list(self._data.keys()):
            if k.startswith(prefix):
                del self._data[k]

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def key_count(self) -> int:
        now = time.monotonic()
        return sum(1 for _, exp in self._data.values() if now <= exp)


class CacheBackend:
    """Unified cache interface with Redis backend and in-memory fallback.

    Attributes:
        backend_name: ``"redis"`` or ``"memory"`` — tells callers which is active.
    """

    def __init__(self) -> None:
        self._redis = None
        self._mem = _MemoryStore()

    def connect(self, redis_url: str) -> None:
        """Attempt to connect to Redis.  Fails silently on error."""
        if not redis_url:
            return
        try:
            import redis as _redis_lib

            client = _redis_lib.from_url(
                redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            client.ping()
            self._redis = client
            logger.info("Cache: Redis connected at %s", redis_url)
        except Exception as exc:
            logger.warning("Cache: Redis unavailable (%s) — using in-memory fallback", exc)

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis else "memory"

    @property
    def is_redis_connected(self) -> bool:
        return self._redis is not None

    # ── Core get/set/delete ───────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value or ``None`` on miss / expiry."""
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                return json.loads(raw) if raw is not None else None
            except Exception:
                pass  # degrade to memory on Redis error
        return self._mem.get(key)

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store *value* under *key* for *ttl* seconds."""
        if self._redis is not None:
            try:
                self._redis.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception:
                pass
        self._mem.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """Remove a single key."""
        if self._redis is not None:
            try:
                self._redis.delete(key)
                return
            except Exception:
                pass
        self._mem.delete(key)

    def clear_prefix(self, prefix: str) -> None:
        """Invalidate all keys starting with *prefix*."""
        if self._redis is not None:
            try:
                for key in self._redis.scan_iter(f"{prefix}*"):
                    self._redis.delete(key)
                return
            except Exception:
                pass
        self._mem.clear_prefix(prefix)

    # ── Namespaced helpers ────────────────────────────────────────────────────

    def ns_get(self, key: str) -> Optional[Any]:
        """Get with automatic namespace prefix."""
        return self.get(f"{_NAMESPACE}{key}")

    def ns_set(self, key: str, value: Any, ttl: int) -> None:
        """Set with automatic namespace prefix."""
        self.set(f"{_NAMESPACE}{key}", value, ttl)

    def ns_delete(self, key: str) -> None:
        """Delete with automatic namespace prefix."""
        self.delete(f"{_NAMESPACE}{key}")

    def ns_clear(self) -> None:
        """Clear all namespaced keys."""
        self.clear_prefix(_NAMESPACE)

    # ── Token blacklist ───────────────────────────────────────────────────────

    def revoke_token(self, jti: str, ttl_seconds: int) -> None:
        """Add a JWT ID to the revocation list for *ttl_seconds*."""
        key = f"{_BLACKLIST_PREFIX}{jti}"
        if self._redis is not None:
            try:
                self._redis.setex(key, ttl_seconds, "1")
                return
            except Exception:
                pass
        self._mem.set(key, "1", ttl_seconds)

    def is_token_revoked(self, jti: str) -> bool:
        """Return True if this JWT ID has been revoked."""
        key = f"{_BLACKLIST_PREFIX}{jti}"
        if self._redis is not None:
            try:
                return bool(self._redis.exists(key))
            except Exception:
                pass
        return self._mem.exists(key)

    def clear_blacklist(self) -> int:
        """Remove all blacklisted token entries. Returns count cleared."""
        if self._redis is not None:
            try:
                keys = list(self._redis.scan_iter(f"{_BLACKLIST_PREFIX}*"))
                if keys:
                    self._redis.delete(*keys)
                return len(keys)
            except Exception:
                pass
        before = self._mem.key_count()
        self._mem.clear_prefix(_BLACKLIST_PREFIX)
        return before - self._mem.key_count()

    # ── Pub/Sub (Redis only) ──────────────────────────────────────────────────

    def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a Redis channel. Returns subscriber count (0 if unavailable)."""
        if self._redis is not None:
            try:
                return self._redis.publish(channel, json.dumps(message, default=str))
            except Exception as exc:
                logger.warning("Cache pubsub publish error: %s", exc)
        return 0

    def get_pubsub(self):
        """Return a Redis PubSub object or None in memory mode."""
        if self._redis is not None:
            try:
                return self._redis.pubsub(ignore_subscribe_messages=True)
            except Exception:
                pass
        return None

    # ── Health / diagnostics ──────────────────────────────────────────────────

    def redis_info(self) -> Optional[dict]:
        """Return Redis INFO dict or None if not connected."""
        if self._redis is not None:
            try:
                info = self._redis.info()
                return {
                    "connected": True,
                    "version": info.get("redis_version"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
            except Exception as exc:
                return {"connected": False, "error": str(exc)}
        return {"connected": False, "reason": "no_redis_url_configured"}


# Module-level singleton — import and use directly
cache = CacheBackend()
