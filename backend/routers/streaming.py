"""WebSocket streaming router.

Endpoint:
  WS  /ws                 Main streaming endpoint
  GET /ws/status          Connection status (HTTP)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from services.streaming import manager

router = APIRouter(prefix="/ws", tags=["streaming"])


@router.get("/status")
async def ws_status() -> Dict[str, Any]:
    return {
        "active_connections": manager.active_connections,
        "available_channels": [
            "orders",
            "executions",
            "positions",
            "prices:{TICKER}",
            "alerts",
        ],
    }


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    channels: Optional[str] = Query(default=None),
) -> None:
    """WebSocket endpoint.

    Query param ``channels`` is a comma-separated list of channels to subscribe
    to immediately on connect.  Example:
      ws://localhost:8001/ws?channels=orders,executions,positions
    """
    initial_channels = [c.strip() for c in channels.split(",")] if channels else []
    await manager.handle_connection(websocket, initial_channels=initial_channels)
