"""M10 Phase 5 — Production WebSocket v3 router.

New endpoints (v1/v2 untouched):
  GET  /ws/v3/status             Rich status: auth, RBAC, replay, Redis
  WS   /ws/v3                    Full v3: real JWT, RBAC, event replay
  WS   /ws/v3/market/{ticker}    Convenience market data stream
  WS   /ws/v3/jobs/{job_id}      Job progress stream with replay on reconnect

Improvements over v2:
  - Real JWT validation (not mock hashlib)
  - Role-based channel authorization on subscribe
  - Event replay: ?since_seq=N replays missed events on connect
  - Redis pub/sub fan-out (when Redis available; in-memory fallback)
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from services.streaming import manager
from services.streaming_enhanced import (
    StreamEvent,
    connection_rate_limiter,
    is_valid_channel,
)
from services.streaming_v3 import (
    V3AuthResult,
    authenticate_token,
    check_channel_access,
    get_replay,
    get_v3_status,
    store_event,
)

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r'^[A-Z]{1,10}$')
_JOB_ID_RE = re.compile(r'^[a-fA-F0-9\-]{36}$')  # UUID4

router = APIRouter(prefix="/ws/v3", tags=["streaming-v3"])


# ---------------------------------------------------------------------------
# HTTP status endpoint
# ---------------------------------------------------------------------------

@router.get("/status")
async def ws_v3_status() -> Dict[str, Any]:
    """Return v3 feature availability and connection stats."""
    return get_v3_status()


# ---------------------------------------------------------------------------
# Core v3 connection handler
# ---------------------------------------------------------------------------

async def _v3_handle(
    websocket: WebSocket,
    auth: V3AuthResult,
    initial_channels: list[str],
    since_seq: int = 0,
) -> None:
    """Full v3 connection lifecycle with RBAC and event replay."""
    conn_id = await manager.connect(websocket)

    # Validate and subscribe initial channels
    valid_channels: list[str] = []
    denied_channels: list[str] = []
    for ch in initial_channels:
        if not is_valid_channel(ch):
            denied_channels.append(ch)
        elif not check_channel_access(ch, auth):
            denied_channels.append(ch)
        else:
            valid_channels.append(ch)

    if valid_channels:
        manager.subscribe(conn_id, valid_channels)

    # Welcome envelope
    conn = manager._connections.get(conn_id)
    welcome = StreamEvent(
        event_type="connected",
        channel="system",
        payload={
            "conn_id": conn_id,
            "user_id": auth.user_id,
            "role": auth.role,
            "anonymous": auth.anonymous,
            "subscriptions": list(conn.subscriptions) if conn else [],
            "denied": denied_channels,
            "features": ["jwt_auth", "rbac", "event_replay", "redis_pubsub"],
            "version": "v3",
        },
    )
    await websocket.send_text(welcome.to_json())

    # Replay missed events for each subscribed channel
    for ch in valid_channels:
        events = get_replay(ch, since_seq=since_seq)
        for ev in events:
            try:
                await websocket.send_text(json.dumps(ev))
            except Exception:
                break

    heartbeat_task = asyncio.create_task(manager.heartbeat_loop(conn_id, interval_seconds=30))

    try:
        while True:
            raw = await websocket.receive_text()

            if not connection_rate_limiter.allow(conn_id):
                err = StreamEvent.error("system", "Rate limit exceeded", "RATE_LIMITED")
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
                valid: list[str] = []
                denied: list[str] = []
                for ch in channels:
                    if not is_valid_channel(ch):
                        denied.append(ch)
                    elif not check_channel_access(ch, auth):
                        denied.append(ch)
                    else:
                        valid.append(ch)
                if valid:
                    manager.subscribe(conn_id, valid)
                    # Replay for newly subscribed channels
                    req_since = msg.get("since_seq", 0)
                    for ch in valid:
                        for ev in get_replay(ch, since_seq=req_since):
                            try:
                                await websocket.send_text(json.dumps(ev))
                            except Exception:
                                break
                conn = manager._connections.get(conn_id)
                resp = StreamEvent(
                    event_type="subscribed",
                    channel="system",
                    payload={
                        "subscriptions": list(conn.subscriptions) if conn else [],
                        "denied": denied,
                    },
                )
                await websocket.send_text(resp.to_json())

            elif action == "unsubscribe":
                channels = msg.get("channels", [])
                manager.unsubscribe(conn_id, channels)
                conn = manager._connections.get(conn_id)
                resp = StreamEvent(
                    event_type="subscribed",
                    channel="system",
                    payload={"subscriptions": list(conn.subscriptions) if conn else []},
                )
                await websocket.send_text(resp.to_json())

            elif action == "ping":
                pong = StreamEvent(event_type="pong", channel="system", payload={})
                await websocket.send_text(pong.to_json())

            elif action == "replay":
                ch = msg.get("channel", "")
                req_since = msg.get("since_seq", 0)
                conn = manager._connections.get(conn_id)
                if conn and ch in conn.subscriptions:
                    for ev in get_replay(ch, since_seq=req_since):
                        try:
                            await websocket.send_text(json.dumps(ev))
                        except Exception:
                            break
                else:
                    err = StreamEvent.error("system", "Not subscribed to channel", "NOT_SUBSCRIBED")
                    await websocket.send_text(err.to_json())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("WS v3 error on %s: %s", conn_id, exc)
    finally:
        heartbeat_task.cancel()
        connection_rate_limiter.remove(conn_id)
        await manager.disconnect(conn_id)


# ---------------------------------------------------------------------------
# WebSocket endpoints
# ---------------------------------------------------------------------------

@router.websocket("")
async def ws_v3_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
    channels: Optional[str] = Query(default=None),
    since_seq: int = Query(default=0, ge=0),
) -> None:
    """Full v3 WebSocket endpoint.

    Query params:
      token     — JWT access token (anonymous allowed for public channels)
      channels  — comma-separated initial subscriptions
      since_seq — replay events with seq > this value on connect
    """
    auth = authenticate_token(token)
    if not auth.valid:
        await websocket.accept()
        err = StreamEvent.error("system", "Invalid authentication token", "AUTH_FAILED")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4001)
        return

    initial = [c.strip() for c in channels.split(",")] if channels else []
    await _v3_handle(websocket, auth, initial, since_seq=since_seq)


@router.websocket("/market/{ticker}")
async def ws_v3_market(
    websocket: WebSocket,
    ticker: str,
    token: Optional[str] = Query(default=None),
    since_seq: int = Query(default=0, ge=0),
) -> None:
    """Convenience endpoint — subscribes to market_data:{ticker}."""
    auth = authenticate_token(token)
    if not auth.valid:
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

    await _v3_handle(
        websocket, auth,
        [f"market_data:{ticker}", f"prices:{ticker}"],
        since_seq=since_seq,
    )


@router.websocket("/jobs/{job_id}")
async def ws_v3_job(
    websocket: WebSocket,
    job_id: str,
    token: Optional[str] = Query(default=None),
    since_seq: int = Query(default=0, ge=0),
) -> None:
    """Job progress stream with event replay.

    Requires authentication. Replays all progress events since since_seq.
    """
    auth = authenticate_token(token)
    if not auth.valid or auth.anonymous:
        await websocket.accept()
        err = StreamEvent.error("system", "Authentication required for job streams", "AUTH_REQUIRED")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4001)
        return

    if not _JOB_ID_RE.match(job_id):
        await websocket.accept()
        err = StreamEvent.error("system", "Invalid job ID", "INVALID_JOB_ID")
        await websocket.send_text(err.to_json())
        await websocket.close(code=4003)
        return

    channel = f"job_progress:{job_id}"
    await _v3_handle(websocket, auth, [channel], since_seq=since_seq)
