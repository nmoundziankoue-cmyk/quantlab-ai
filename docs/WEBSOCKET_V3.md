# WebSocket v3 Guide

## Endpoints

| Endpoint | Description |
|---|---|
| `WS /ws/v3` | Full-featured connection (auth, RBAC, replay) |
| `WS /ws/v3/market/{ticker}` | Convenience: auto-subscribes to market data |
| `WS /ws/v3/jobs/{job_id}` | Job progress with event replay (auth required) |
| `GET /ws/v3/status` | Feature availability and connection stats |

v1 (`/ws`) and v2 (`/ws/v2`) endpoints remain unchanged.

---

## Connecting

```js
// Without auth (public channels only)
const ws = new WebSocket("wss://api.example.com/ws/v3");

// With auth + initial subscriptions + replay
const token = localStorage.getItem("access_token");
const ws = new WebSocket(
  `wss://api.example.com/ws/v3?token=${token}&channels=market_data:AAPL,orders&since_seq=42`
);
```

Query parameters:
- `token` — JWT access token
- `channels` — comma-separated initial channel subscriptions
- `since_seq` — replay events with sequence number > this value on connect

---

## Message Protocol

All messages use the `StreamEvent` envelope (v=3):

```json
{
  "v": "2",
  "event_type": "data",
  "channel": "market_data:AAPL",
  "payload": { "ticker": "AAPL", "price": 182.35 },
  "event_id": "uuid4",
  "seq": 42,
  "timestamp": "2026-06-29T12:00:00Z",
  "compressed": false
}
```

### Client → Server actions

```json
{ "action": "subscribe",   "channels": ["market_data:AAPL", "orders"] }
{ "action": "unsubscribe", "channels": ["orders"] }
{ "action": "ping" }
{ "action": "replay",      "channel": "job_progress:abc123", "since_seq": 10 }
```

### Server → Client event types

| event_type | Description |
|---|---|
| `connected` | Welcome with conn_id, role, subscriptions |
| `subscribed` | Updated subscription list after subscribe/unsubscribe |
| `data` | Channel payload |
| `heartbeat` | Keepalive (respond with ping) |
| `pong` | Response to ping |
| `error` | Error with `code` and `message` |

---

## Channel Registry

| Channel | Pattern | Auth required | Min role |
|---|---|---|---|
| `market_data` | `market_data:{TICKER}` | No | — |
| `prices` | `prices:{TICKER}` | No | — |
| `orders` | `orders` | Yes | VIEWER |
| `executions` | `executions` | Yes | VIEWER |
| `positions` | `positions` | Yes | VIEWER |
| `alerts` | `alerts` | No | — |
| `agent_progress` | `agent_progress:{SESSION_ID}` | No | — |
| `job_progress` | `job_progress:{JOB_ID}` | Yes | VIEWER |
| `task_queue` | `task_queue` | Yes | ANALYST |
| `system_metrics` | `system_metrics` | Yes | ANALYST |
| `provider_health` | `provider_health` | Yes | ANALYST |
| `execution_updates` | `execution_updates` | Yes | TRADER |
| `news_feed` | `news_feed` | No | — |

---

## Event Replay

On connect or subscribe, pass `since_seq=N` to receive all buffered events
with `seq > N` for subscribed channels. The server stores up to 50 events per
channel for up to 5 minutes.

After reconnection:
```json
{ "action": "subscribe", "channels": ["job_progress:abc123"], "since_seq": 7 }
```
Server immediately sends events 8, 9, 10 … before new live events.

---

## React Integration

```js
import { useWebSocket } from "../hooks/useWebSocket";

const { state, subscribe, send } = useWebSocket({
  url: `${WS_BASE}/ws/v3?token=${token}&since_seq=0`,
  onMessage: (envelope) => {
    if (envelope.channel.startsWith("job_progress:")) {
      console.log("Job update:", envelope.payload);
    }
  },
});

// Subscribe dynamically after connect
subscribe(["market_data:TSLA"]);
```
