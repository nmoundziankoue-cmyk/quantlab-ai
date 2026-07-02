"""M9 Phase 2 — Enhanced WebSocket streaming router (v2).

New endpoints (do NOT modify existing /ws or /ws/status):
  GET  /ws/v2/status          Rich status with features and channel registry
  GET  /ws/v2/channels        Full channel list with descriptions
  WS   /ws/v2                 Enhanced endpoint: auth + rate limiting + typed envelopes
  WS   /ws/v2/market/{ticker} Convenience single-ticker market data stream
  WS   /ws/v2/agent/{session} Convenience agent-progress stream for a session

All existing /ws endpoints are untouched.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

_TICKER_RE = re.compile(r'^[A-Z]{1,10}$')
_SESSION_RE = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from services.streaming import manager
from services.streaming_enhanced import (
    CHANNEL_REGISTRY,
    AuthValidator,
    ConnectionRateLimiter,
    StreamEvent,
    SequenceCounter,
    compress_payload,
    connection_rate_limiter,
    get_enhanced_status,
    is_valid_channel,
    resolve_channel,
    validate_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/v2", tags=["streaming-v2"])

_auth = AuthValidator()


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def ws_v2_status() -> Dict[str, Any]:
    """Enhanced status with feature flags, channel registry, and rate limit info."""
    return get_enhanced_status()


@router.get("/channels")
async def ws_v2_channels() -> Dict[str, Any]:
    """List all registered channels with metadata."""
    channels = []
    for key, info in CHANNEL_REGISTRY.items():
        channels.append({
            "key": key,
            "pattern": info.pattern,
            "description": info.description,
            "category": info.category,
            "requires_auth": info.requires_auth,
            "rate_limit_cost": info.rate_limit_cost,
        })
    categories = sorted({info.category for info in CHANNEL_REGISTRY.values()})
    return {
        "channels": channels,
        "total": len(channels),
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# Enhanced WebSocket endpoint
# ---------------------------------------------------------------------------

async def _send_event(ws: WebSocket, event: StreamEvent) -> bool:
    """Send a StreamEvent; return False on failure."""
    try:
        await ws.send_text(event.to_json())
        return True
    except Exception:
        return False


async def _v2_handle(
    websocket: WebSocket,
    initial_channels: list[str],
    user_id: Optional[str],
    conn_id: Optional[str] = None,
) -> None:
    """Full v2 connection lifecycle."""
    conn_id = await manager.connect(websocket, conn_id)
    if initial_channels:
        # Validate each channel before subscribing
        valid = [c for c in initial_channels if is_valid_channel(c)]
        manager.subscribe(conn_id, valid)

    # Welcome envelope
    welcome = StreamEvent(
        event_type="connected",
        channel="system",
        payload={
            "conn_id": conn_id,
            "user_id": user_id,
            "subscriptions": list(manager._connections[conn_id].subscriptions),
            "features": ["rate_limiting", "compression", "seq", "heartbeat"],
        },
    )
    await websocket.send_text(welcome.to_json())

    heartbeat_task = asyncio.create_task(manager.heartbeat_loop(conn_id, interval_seconds=30))

    try:
        while True:
            raw = await websocket.receive_text()

            # Rate limit inbound messages
            if not connection_rate_limiter.allow(conn_id):
                err = StreamEvent.error("system", "Rate limit exceeded — slow down", "RATE_LIMITED")
                await websocket.send_text(err.to_json())
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                err = StreamEvent.error("system", "Invalid JSON", "PARSE_ERROR")
                await websocket.send_text(err.to_json())
                continue

            action = msg.get("action", "")

            if action == "subscribe":
                channels = msg.get("channels", [])
                valid = []
                denied = []
                for ch in channels:
                    if not is_valid_channel(ch):
                        denied.append(ch)
                    elif not _auth.validate_channel_access(ch, user_id):
                        denied.append(ch)
                    else:
                        valid.append(ch)
                if valid:
                    manager.subscribe(conn_id, valid)
                conn = manager._connections.get(conn_id)
                response = StreamEvent(
                    event_type="subscribed",
                    channel="system",
                    payload={
                        "subscriptions": list(conn.subscriptions) if conn else [],
                        "denied": denied,
                    },
                )
                await websocket.send_text(response.to_json())

            elif action == "unsubscribe":
                channels = msg.get("channels", [])
                manager.unsubscribe(conn_id, channels)
                conn = manager._connections.get(conn_id)
                response = StreamEvent(
                    event_type="subscribed",
                    channel="system",
                    payload={
                        "subscriptions": list(conn.subscriptions) if conn else [],
                    },
                )
                await websocket.send_text(response.to_json())

            elif action == "ping":
                pong = StreamEvent(event_type="pong", channel="system", payload={})
                await websocket.send_text(pong.to_json())

            elif action == "list_channels":
                info = StreamEvent(
                    event_type="data",
                    channel="system",
                    payload={
                        "channels": [
                            {"key": k, "pattern": v.pattern}
                            for k, v in CHANNEL_REGISTRY.items()
                        ]
                    },
                )
                await websocket.send_text(info.to_json())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("WS v2 error on %s: %s", conn_id, exc)
    finally:
        heartbeat_task.cancel()
        connection_rate_limiter.remove(conn_id)
        await manager.disconnect(conn_id)


@router.websocket("")
async def ws_v2_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
    channels: Optional[str] = Query(default=None),
) -> None:
    """Enhanced WebSocket endpoint with auth, rate limiting, and typed envelopes.

    Query params:
      token    — optional auth token (anonymous allowed for public channels)
      channels — comma-separated initial channel subscriptions
    """
    is_valid, user_id = validate_token(token)
    if not is_valid:
        await websocket.accept()
        err = StreamEvent.error("system", "Invalid authentication token", "AUTH_FAILED")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4001)
        return

    initial_channels = [c.strip() for c in channels.split(",")] if channels else []
    await _v2_handle(websocket, initial_channels, user_id)


@router.websocket("/market/{ticker}")
async def ws_v2_market(
    websocket: WebSocket,
    ticker: str,
    token: Optional[str] = Query(default=None),
) -> None:
    """Convenience endpoint — auto-subscribes to market_data:{ticker} and prices:{ticker}."""
    is_valid, user_id = validate_token(token)
    if not is_valid:
        await websocket.accept()
        err = StreamEvent.error("system", "Invalid authentication token", "AUTH_FAILED")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4001)
        return

    ticker = ticker.upper()
    if not _TICKER_RE.match(ticker):
        await websocket.accept()
        err = StreamEvent.error("system", "Invalid ticker symbol", "INVALID_TICKER")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4003)
        return

    initial_channels = [f"market_data:{ticker}", f"prices:{ticker}"]
    await _v2_handle(websocket, initial_channels, user_id)


@router.websocket("/agent/{session_id}")
async def ws_v2_agent(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(default=None),
) -> None:
    """Convenience endpoint — auto-subscribes to agent_progress:{session_id}."""
    is_valid, user_id = validate_token(token)
    if not is_valid:
        await websocket.accept()
        err = StreamEvent.error("system", "Invalid authentication token", "AUTH_FAILED")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4001)
        return

    if not _SESSION_RE.match(session_id):
        await websocket.accept()
        err = StreamEvent.error("system", "Invalid session ID", "INVALID_SESSION")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4003)
        return

    initial_channels = [f"agent_progress:{session_id}"]
    await _v2_handle(websocket, initial_channels, user_id)
