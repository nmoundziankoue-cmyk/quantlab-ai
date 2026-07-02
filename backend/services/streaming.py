"""WebSocket Streaming Manager.

asyncio-based publish / subscribe for real-time events.

Architecture:
  - One ConnectionManager singleton per process
  - Each WebSocket connection registers a set of channel subscriptions
  - When an event is published on a channel, all subscribed connections
    receive a JSON message
  - Channels: 'orders', 'executions', 'positions', 'prices:{TICKER}'
  - Reconnect and heartbeat are handled client-side (the server sends
    periodic heartbeat messages on all connections)

Thread safety:
  - publish() is sync-safe: it schedules coroutines on the asyncio event loop
    so it can be called from sync FastAPI route handlers or background tasks
  - The underlying asyncio.Queue is per-connection and consumed by the WS
    handler coroutine

Usage (in router):
  from services.streaming import manager
  await manager.connect(websocket, conn_id)
  manager.subscribe(conn_id, ["orders", "prices:AAPL"])
  ...
  await manager.disconnect(conn_id)

Usage (from sync service code):
  from services.streaming import publish_event
  publish_event("orders", {"type": "ORDER_FILLED", "order_id": "...", ...})
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class _Connection:
    """State for a single WebSocket connection."""

    def __init__(self, ws: WebSocket, conn_id: str) -> None:
        self.ws = ws
        self.conn_id = conn_id
        self.subscriptions: Set[str] = set()
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        self.connected = True


class ConnectionManager:
    """Singleton managing all active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: Dict[str, _Connection] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket, conn_id: Optional[str] = None) -> str:
        await websocket.accept()
        conn_id = conn_id or str(uuid.uuid4())
        self._connections[conn_id] = _Connection(websocket, conn_id)
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        logger.info("WS connected: %s (total=%d)", conn_id, len(self._connections))
        return conn_id

    async def disconnect(self, conn_id: str) -> None:
        conn = self._connections.pop(conn_id, None)
        if conn:
            conn.connected = False
            logger.info("WS disconnected: %s (total=%d)", conn_id, len(self._connections))

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, conn_id: str, channels: list[str]) -> None:
        conn = self._connections.get(conn_id)
        if conn:
            conn.subscriptions.update(channels)

    def unsubscribe(self, conn_id: str, channels: list[str]) -> None:
        conn = self._connections.get(conn_id)
        if conn:
            conn.subscriptions.difference_update(channels)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def _send_to_connection(self, conn: _Connection, message: str) -> None:
        try:
            await conn.ws.send_text(message)
        except Exception:
            conn.connected = False

    async def broadcast_to_channel(self, channel: str, payload: Dict[str, Any]) -> None:
        """Async broadcast to all connections subscribed to channel."""
        event = json.dumps({
            "event_type": "data",
            "channel": channel,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        dead: list[str] = []
        for conn_id, conn in list(self._connections.items()):
            if channel in conn.subscriptions:
                try:
                    await self._send_to_connection(conn, event)
                except Exception:
                    dead.append(conn_id)
        for conn_id in dead:
            await self.disconnect(conn_id)

    def publish_sync(self, channel: str, payload: Dict[str, Any]) -> None:
        """Thread-safe sync publish — schedules the async broadcast."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_channel(channel, payload),
                self._loop,
            )
        # If no event loop (e.g. sync tests), silently drop

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def send_heartbeat(self, conn_id: str) -> None:
        conn = self._connections.get(conn_id)
        if conn and conn.connected:
            try:
                await conn.ws.send_text(json.dumps({
                    "event_type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }))
            except Exception:
                conn.connected = False

    async def heartbeat_loop(self, conn_id: str, interval_seconds: int = 30) -> None:
        """Run until connection is gone; sends a heartbeat every interval."""
        while conn_id in self._connections:
            await asyncio.sleep(interval_seconds)
            await self.send_heartbeat(conn_id)

    # ------------------------------------------------------------------
    # Per-connection WS message handler loop
    # ------------------------------------------------------------------

    async def handle_connection(
        self,
        websocket: WebSocket,
        conn_id: Optional[str] = None,
        initial_channels: Optional[list[str]] = None,
    ) -> None:
        """Full lifecycle handler: accept → subscribe → receive → disconnect."""
        conn_id = await self.connect(websocket, conn_id)
        if initial_channels:
            self.subscribe(conn_id, initial_channels)

        # Send welcome
        await websocket.send_text(json.dumps({
            "event_type": "connected",
            "conn_id": conn_id,
            "subscriptions": list(self._connections[conn_id].subscriptions),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))

        heartbeat_task = asyncio.create_task(self.heartbeat_loop(conn_id))
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                action = msg.get("action")
                if action == "subscribe":
                    self.subscribe(conn_id, msg.get("channels", []))
                    await websocket.send_text(json.dumps({
                        "event_type": "subscribed",
                        "channels": list(self._connections[conn_id].subscriptions),
                    }))
                elif action == "unsubscribe":
                    self.unsubscribe(conn_id, msg.get("channels", []))
                elif action == "ping":
                    await websocket.send_text(json.dumps({"event_type": "pong"}))
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.exception("WS error on %s: %s", conn_id, exc)
        finally:
            heartbeat_task.cancel()
            await self.disconnect(conn_id)

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# Module-level singleton
manager = ConnectionManager()


def publish_event(channel: str, payload: Dict[str, Any]) -> None:
    """Sync-safe convenience wrapper around manager.publish_sync()."""
    manager.publish_sync(channel, payload)
