"""M9 Phase 2 — WebSocket streaming enhancements.

Extends services/streaming.py with:
  - Typed StreamEvent envelopes with monotonic sequence numbers
  - Per-connection token-bucket rate limiting
  - Channel registry with metadata and wildcard support
  - zlib payload compression for large messages
  - Authentication hook (JWT-shape token validation)
  - Publisher helpers for all M9 channels

The existing `services.streaming.manager` singleton is reused for
all transport — this module adds the envelope/auth/rate layers on top.
"""
from __future__ import annotations

import base64
import hashlib
import json
import threading
import time
import uuid
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.streaming import manager, publish_event  # re-export for convenience

__all__ = [
    "StreamEvent",
    "SequenceCounter",
    "RateLimiter",
    "ConnectionRateLimiter",
    "ChannelRegistry",
    "CHANNEL_REGISTRY",
    "AuthValidator",
    "compress_payload",
    "decompress_payload",
    "publish_market_data",
    "publish_agent_progress",
    "publish_alert",
    "publish_task_event",
    "publish_system_metrics",
    "publish_provider_health",
    "publish_execution_update",
    "get_enhanced_status",
]

# ---------------------------------------------------------------------------
# Sequence counter — global monotonic per-channel seq
# ---------------------------------------------------------------------------

class SequenceCounter:
    """Thread-safe monotonic counter per channel."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._lock = threading.Lock()

    def next(self, channel: str) -> int:
        with self._lock:
            self._counters[channel] = self._counters.get(channel, 0) + 1
            return self._counters[channel]

    def current(self, channel: str) -> int:
        with self._lock:
            return self._counters.get(channel, 0)

    def reset(self, channel: str) -> None:
        with self._lock:
            self._counters[channel] = 0


_seq = SequenceCounter()


# ---------------------------------------------------------------------------
# Typed event envelope
# ---------------------------------------------------------------------------

@dataclass
class StreamEvent:
    """Typed WebSocket event envelope.

    Fields:
        event_type  — one of: data | heartbeat | connected | subscribed |
                               pong | error | system | agent_progress |
                               task_update | market_data | alert |
                               provider_health | execution_update
        channel     — channel name (e.g. "market_data:AAPL")
        payload     — application payload dict
        event_id    — UUID4 for dedup
        seq         — monotonic per-channel sequence number
        timestamp   — ISO-8601 UTC
        compressed  — True if payload is zlib-compressed in to_json()
        version     — envelope schema version
    """
    event_type: str
    channel: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    seq: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    compressed: bool = False
    version: str = "2"

    def to_dict(self) -> dict:
        return {
            "v": self.version,
            "event_type": self.event_type,
            "channel": self.channel,
            "payload": self.payload,
            "event_id": self.event_id,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "compressed": self.compressed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def data(cls, channel: str, payload: Dict[str, Any]) -> "StreamEvent":
        return cls(
            event_type="data",
            channel=channel,
            payload=payload,
            seq=_seq.next(channel),
        )

    @classmethod
    def error(cls, channel: str, message: str, code: str = "ERROR") -> "StreamEvent":
        return cls(
            event_type="error",
            channel=channel,
            payload={"message": message, "code": code},
        )

    @classmethod
    def system(cls, message: str, payload: Optional[Dict] = None) -> "StreamEvent":
        return cls(
            event_type="system",
            channel="system",
            payload={"message": message, **(payload or {})},
        )


# ---------------------------------------------------------------------------
# Compression helpers
# ---------------------------------------------------------------------------

COMPRESS_THRESHOLD_BYTES = 1024  # compress JSON strings larger than this


def compress_payload(data: str) -> str:
    """zlib-compress a JSON string and base64url-encode it."""
    compressed = zlib.compress(data.encode("utf-8"), level=6)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def decompress_payload(data: str) -> str:
    """Reverse of compress_payload."""
    raw = base64.urlsafe_b64decode(data.encode("ascii"))
    return zlib.decompress(raw).decode("utf-8")


def maybe_compress(event: StreamEvent) -> str:
    """Serialize event; compress payload if it exceeds threshold."""
    raw_json = event.to_json()
    if len(raw_json) > COMPRESS_THRESHOLD_BYTES:
        compressed_payload = compress_payload(json.dumps(event.payload))
        compressed_event = StreamEvent(
            event_type=event.event_type,
            channel=event.channel,
            payload={"_compressed": compressed_payload},
            event_id=event.event_id,
            seq=event.seq,
            timestamp=event.timestamp,
            compressed=True,
            version=event.version,
        )
        return compressed_event.to_json()
    return raw_json


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------

@dataclass
class RateLimiter:
    """Token-bucket rate limiter for a single connection.

    Args:
        capacity       — max burst tokens
        refill_rate    — tokens added per second
    """
    capacity: float = 20.0
    refill_rate: float = 10.0  # tokens/second

    def __post_init__(self) -> None:
        self._tokens: float = self.capacity
        self._last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def allow(self, cost: float = 1.0) -> bool:
        """Return True and consume cost tokens if allowed; False if rate-limited."""
        with self._lock:
            self._refill()
            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False

    @property
    def tokens_available(self) -> float:
        with self._lock:
            self._refill()
            return round(self._tokens, 3)


class ConnectionRateLimiter:
    """Per-connection rate limiter registry."""

    def __init__(self, capacity: float = 20.0, refill_rate: float = 10.0) -> None:
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.Lock()
        self._capacity = capacity
        self._refill_rate = refill_rate

    def get(self, conn_id: str) -> RateLimiter:
        with self._lock:
            if conn_id not in self._limiters:
                self._limiters[conn_id] = RateLimiter(self._capacity, self._refill_rate)
            return self._limiters[conn_id]

    def remove(self, conn_id: str) -> None:
        with self._lock:
            self._limiters.pop(conn_id, None)

    def allow(self, conn_id: str, cost: float = 1.0) -> bool:
        return self.get(conn_id).allow(cost)


connection_rate_limiter = ConnectionRateLimiter()


# ---------------------------------------------------------------------------
# Channel registry
# ---------------------------------------------------------------------------

@dataclass
class ChannelInfo:
    name: str
    pattern: str  # exact or with {PARAM} placeholder
    description: str
    category: str
    requires_auth: bool = False
    rate_limit_cost: float = 1.0


CHANNEL_REGISTRY: Dict[str, ChannelInfo] = {
    # legacy channels (unchanged)
    "orders": ChannelInfo("orders", "orders", "Order lifecycle events", "trading"),
    "executions": ChannelInfo("executions", "executions", "Trade execution fills", "trading"),
    "positions": ChannelInfo("positions", "positions", "Position changes", "trading"),
    "alerts": ChannelInfo("alerts", "alerts", "Trading alerts and signals", "trading"),
    # market data (extends legacy prices:{TICKER})
    "market_data": ChannelInfo("market_data", "market_data:{TICKER}", "Live market quotes and OHLCV", "market"),
    "prices": ChannelInfo("prices", "prices:{TICKER}", "Legacy live price feed (alias)", "market"),
    # M9 new channels
    "agent_progress": ChannelInfo(
        "agent_progress", "agent_progress:{SESSION_ID}",
        "AI research agent progress and partial results", "ai"
    ),
    "task_queue": ChannelInfo(
        "task_queue", "task_queue",
        "Background task lifecycle (queued/running/done/failed)", "system"
    ),
    "system_metrics": ChannelInfo(
        "system_metrics", "system_metrics",
        "Periodic CPU/memory/latency system health snapshot", "system"
    ),
    "provider_health": ChannelInfo(
        "provider_health", "provider_health",
        "Data provider health score and quota updates", "system"
    ),
    "execution_updates": ChannelInfo(
        "execution_updates", "execution_updates",
        "Enhanced execution engine order updates", "trading"
    ),
    "job_progress": ChannelInfo(
        "job_progress", "job_progress:{JOB_ID}",
        "Background job progress updates (M10 jobs system)", "system",
        requires_auth=True,
    ),
    "news_feed": ChannelInfo(
        "news_feed", "news_feed",
        "Live news headlines and sentiment scores", "market"
    ),
}


def resolve_channel(raw: str) -> Optional[str]:
    """Resolve a raw channel string to a registry key.

    E.g. "market_data:AAPL" → "market_data",  "orders" → "orders"
    Returns None for completely unknown channels.
    """
    if raw in CHANNEL_REGISTRY:
        return raw
    prefix = raw.split(":")[0]
    return prefix if prefix in CHANNEL_REGISTRY else None


def is_valid_channel(channel: str) -> bool:
    return resolve_channel(channel) is not None


# ---------------------------------------------------------------------------
# Authentication hook
# ---------------------------------------------------------------------------

class AuthValidator:
    """Lightweight token validator for WebSocket connections.

    In production: validate JWT signature against secret key.
    In dev/test: accept any non-empty string; extract mock user_id.
    """

    def __init__(self, secret: str = "dev-secret-not-for-production") -> None:
        self._secret = secret

    def validate(self, token: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Return (is_valid, user_id_or_None)."""
        if not token:
            # Anonymous — allowed for public channels
            return True, None
        if len(token) < 8:
            return False, None
        # Mock: derive user_id deterministically from token hash
        h = hashlib.sha256(f"{self._secret}:{token}".encode()).hexdigest()[:16]
        user_id = f"user_{h}"
        return True, user_id

    def validate_channel_access(
        self, channel: str, user_id: Optional[str]
    ) -> bool:
        """Check if a user_id may subscribe to a channel."""
        info = CHANNEL_REGISTRY.get(resolve_channel(channel) or "")
        if info and info.requires_auth and user_id is None:
            return False
        return True


_auth_validator = AuthValidator()


def validate_token(token: Optional[str]) -> Tuple[bool, Optional[str]]:
    return _auth_validator.validate(token)


# ---------------------------------------------------------------------------
# Publisher helpers for all M9 channels
# ---------------------------------------------------------------------------

def publish_market_data(ticker: str, data: Dict[str, Any]) -> None:
    """Publish live market quote on market_data:{ticker} channel."""
    event = StreamEvent.data(f"market_data:{ticker}", {
        "ticker": ticker,
        "event_subtype": "quote",
        **data,
    })
    publish_event(f"market_data:{ticker}", event.to_dict())
    # Also publish on legacy prices:{ticker} for backwards compatibility
    publish_event(f"prices:{ticker}", {
        "ticker": ticker,
        "price": data.get("price"),
        "timestamp": event.timestamp,
    })


def publish_agent_progress(session_id: str, agent_type: str, progress: Dict[str, Any]) -> None:
    """Publish agent research progress for a session."""
    event = StreamEvent.data(f"agent_progress:{session_id}", {
        "session_id": session_id,
        "agent_type": agent_type,
        "event_subtype": "progress",
        **progress,
    })
    publish_event(f"agent_progress:{session_id}", event.to_dict())


def publish_alert(alert_data: Dict[str, Any]) -> None:
    """Publish a trading alert."""
    event = StreamEvent.data("alerts", {
        "event_subtype": "alert",
        **alert_data,
    })
    publish_event("alerts", event.to_dict())


def publish_task_event(task_id: str, status: str, detail: Optional[Dict] = None) -> None:
    """Publish a task queue lifecycle event."""
    event = StreamEvent.data("task_queue", {
        "task_id": task_id,
        "status": status,  # queued | running | done | failed | cancelled
        "event_subtype": "task_lifecycle",
        **(detail or {}),
    })
    publish_event("task_queue", event.to_dict())


def publish_system_metrics(metrics: Dict[str, Any]) -> None:
    """Publish periodic system health snapshot."""
    event = StreamEvent.data("system_metrics", {
        "event_subtype": "metrics_snapshot",
        **metrics,
    })
    publish_event("system_metrics", event.to_dict())


def publish_provider_health(provider_name: str, health_data: Dict[str, Any]) -> None:
    """Publish provider health update."""
    event = StreamEvent.data("provider_health", {
        "provider": provider_name,
        "event_subtype": "health_update",
        **health_data,
    })
    publish_event("provider_health", event.to_dict())


def publish_execution_update(order_data: Dict[str, Any]) -> None:
    """Publish execution engine order update."""
    event = StreamEvent.data("execution_updates", {
        "event_subtype": "order_update",
        **order_data,
    })
    publish_event("execution_updates", event.to_dict())


# ---------------------------------------------------------------------------
# Enhanced status snapshot
# ---------------------------------------------------------------------------

def get_enhanced_status() -> dict:
    """Return a rich status dict for the /ws/v2/status endpoint."""
    channels_info = []
    for key, info in CHANNEL_REGISTRY.items():
        channels_info.append({
            "key": key,
            "pattern": info.pattern,
            "description": info.description,
            "category": info.category,
            "requires_auth": info.requires_auth,
        })
    return {
        "active_connections": manager.active_connections,
        "channel_count": len(CHANNEL_REGISTRY),
        "channels": channels_info,
        "features": {
            "authentication": True,
            "rate_limiting": True,
            "compression": True,
            "sequence_numbers": True,
            "heartbeat": True,
            "reconnect_support": True,
        },
        "rate_limit": {
            "capacity": connection_rate_limiter._capacity,
            "refill_rate_per_sec": connection_rate_limiter._refill_rate,
        },
        "compression_threshold_bytes": COMPRESS_THRESHOLD_BYTES,
        "envelope_version": "2",
    }
