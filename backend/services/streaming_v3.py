"""WebSocket v3 support layer (M10 Phase 5).

Adds to the v2 streaming foundation:
  - Real JWT validation via services.auth_service (not mock hashlib)
  - Role-based channel authorization (RBAC gating on subscribe)
  - Event replay buffer (last 50 events per channel, 5-min TTL)
  - Redis pub/sub fan-out bridge (publishes events across backend instances)

All v1/v2 endpoints remain unchanged.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from services.streaming_enhanced import (
    CHANNEL_REGISTRY,
    StreamEvent,
    connection_rate_limiter,
    resolve_channel,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Real JWT authentication
# ---------------------------------------------------------------------------

@dataclass
class V3AuthResult:
    valid: bool
    user_id: Optional[str] = None
    role: Optional[str] = None
    jti: Optional[str] = None
    anonymous: bool = False


def authenticate_token(token: Optional[str]) -> V3AuthResult:
    """Validate a JWT using the real auth service.

    Returns anonymous (valid, no identity) when token is absent.
    Returns invalid when token present but cannot be decoded.
    """
    if not token:
        return V3AuthResult(valid=True, anonymous=True)
    try:
        from services.auth_service import decode_token
        payload = decode_token(token)
    except Exception:
        return V3AuthResult(valid=False)

    if not payload:
        return V3AuthResult(valid=False)

    return V3AuthResult(
        valid=True,
        user_id=str(payload.get("sub", "")),
        role=payload.get("role", "VIEWER"),
        jti=payload.get("jti"),
        anonymous=False,
    )


# ---------------------------------------------------------------------------
# Role-based channel authorization
# ---------------------------------------------------------------------------

_ROLE_LEVELS: Dict[str, int] = {
    "VIEWER": 1,
    "ANALYST": 2,
    "TRADER": 3,
    "RISK_MANAGER": 4,
    "PORTFOLIO_MANAGER": 5,
    "COMPLIANCE": 6,
    "ADMIN": 10,
}

# Channels that require a minimum role level; absent = public (level 0)
_CHANNEL_MIN_ROLE: Dict[str, int] = {
    "system_metrics": _ROLE_LEVELS["ANALYST"],
    "provider_health": _ROLE_LEVELS["ANALYST"],
    "execution_updates": _ROLE_LEVELS["TRADER"],
    "task_queue": _ROLE_LEVELS["ANALYST"],
    "orders": _ROLE_LEVELS["VIEWER"],
    "executions": _ROLE_LEVELS["VIEWER"],
    "positions": _ROLE_LEVELS["VIEWER"],
}


def check_channel_access(channel: str, auth: V3AuthResult) -> bool:
    """Return True if ``auth`` permits subscribing to ``channel``."""
    key = resolve_channel(channel) or ""
    min_level = _CHANNEL_MIN_ROLE.get(key, 0)

    if min_level == 0:
        return True  # public channel

    if auth.anonymous or not auth.role:
        return False

    return _ROLE_LEVELS.get(auth.role, 0) >= min_level


# ---------------------------------------------------------------------------
# Event replay buffer (in-memory; Redis-backed when connected)
# ---------------------------------------------------------------------------

_REPLAY_MAX = 50
_replay: Dict[str, list] = {}
_replay_lock = threading.Lock()


def store_event(channel: str, event_dict: dict) -> None:
    """Append an event to the in-process replay buffer for this channel."""
    with _replay_lock:
        buf = _replay.setdefault(channel, [])
        buf.append(event_dict)
        if len(buf) > _REPLAY_MAX:
            _replay[channel] = buf[-_REPLAY_MAX:]
    # Mirror to Redis so other backend instances can serve replay
    _redis_store_event(channel, event_dict)


def get_replay(channel: str, since_seq: int = 0) -> List[dict]:
    """Return stored events with seq > since_seq.

    Tries Redis first (cross-instance), falls back to in-process buffer.
    """
    events = _redis_get_events(channel)
    if events is None:
        with _replay_lock:
            events = list(_replay.get(channel, []))
    return [e for e in events if e.get("seq", 0) > since_seq]


def _redis_store_event(channel: str, event_dict: dict) -> None:
    try:
        from services.cache import cache
        if not cache.is_redis_connected:
            return
        import redis as redis_lib
        key = f"ws:replay:{channel}"
        r = cache._redis  # type: ignore[attr-defined]
        pipe = r.pipeline()
        pipe.rpush(key, json.dumps(event_dict))
        pipe.ltrim(key, -_REPLAY_MAX, -1)
        pipe.expire(key, 300)
        pipe.execute()
    except Exception:
        pass


def _redis_get_events(channel: str) -> Optional[List[dict]]:
    try:
        from services.cache import cache
        if not cache.is_redis_connected:
            return None
        key = f"ws:replay:{channel}"
        r = cache._redis  # type: ignore[attr-defined]
        raw_list = r.lrange(key, 0, -1)
        return [json.loads(item) for item in raw_list]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Redis pub/sub fan-out bridge
# ---------------------------------------------------------------------------
# When Redis is connected, publish events so other instances fan out to their
# local WebSocket connections.  A background asyncio task in the router
# listens on the subscription and re-broadcasts locally.

_PUBSUB_PREFIX = "ws:pubsub:"


def redis_publish(channel: str, event_dict: dict) -> None:
    """Publish a WS event to Redis pub/sub (best-effort)."""
    try:
        from services.cache import cache
        cache.publish(_PUBSUB_PREFIX + channel, event_dict)
    except Exception:
        pass


async def redis_fanout_listener(channel: str, send_fn) -> None:  # type: ignore[type-arg]
    """Async task: listen to Redis pub/sub for ``channel`` and call send_fn(event_dict)."""
    try:
        from services.cache import cache
        if not cache.is_redis_connected:
            return
        pubsub = cache.get_pubsub()
        if pubsub is None:
            return
        pubsub.subscribe(_PUBSUB_PREFIX + channel)
        while True:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if msg and msg.get("type") == "message":
                try:
                    data = json.loads(msg["data"])
                    await send_fn(data)
                except Exception:
                    pass
            await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.debug("Redis fanout listener error on %s: %s", channel, exc)


# ---------------------------------------------------------------------------
# v3 status helper
# ---------------------------------------------------------------------------

def get_v3_status() -> dict:
    """Return v3 feature status dict."""
    from services.cache import cache
    from services.streaming import manager
    return {
        "version": "v3",
        "features": ["jwt_auth", "rbac", "event_replay", "redis_pubsub"],
        "redis_connected": cache.is_redis_connected,
        "active_connections": len(manager._connections),
        "replay_buffer_channels": len(_replay),
        "role_gated_channels": list(_CHANNEL_MIN_ROLE.keys()),
    }
