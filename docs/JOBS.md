# Background Jobs Guide

## Overview

The job system provides DB-backed async task execution with idempotency,
retry, and real-time WebSocket progress updates.

## API

### Enqueue a job

```http
POST /jobs
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_type": "echo",
  "payload": { "msg": "hello" },
  "priority": 5,
  "idempotency_key": "my-unique-key-123"
}
```

Response (202 Accepted):
```json
{
  "id": "uuid4",
  "job_type": "echo",
  "status": "PENDING",
  "priority": 5,
  "idempotency_key": "my-unique-key-123",
  "retry_count": 0,
  "max_retries": 3,
  "enqueued_at": "2026-06-29T12:00:00Z"
}
```

If `idempotency_key` matches an existing job, the existing job is returned
with `"idempotent": true` — no duplicate execution occurs.

### Other endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/jobs` | List jobs (optional `?status=RUNNING&limit=20`) |
| `GET` | `/jobs/{id}` | Get job by UUID |
| `DELETE` | `/jobs/{id}` | Cancel/delete a job |
| `POST` | `/jobs/{id}/retry` | Re-enqueue a FAILED job |

## Job Types

| job_type | Description | Payload fields |
|---|---|---|
| `echo` | Returns payload as result | any |
| `market_data_refresh` | Refreshes market data cache | `tickers: []` |
| `portfolio_risk_snapshot` | Computes and persists a risk snapshot | `portfolio_id` |
| `strategy_backtest` | Runs a strategy backtest | `strategy_id`, `start_date`, `end_date` |

## Job Statuses

`PENDING` → `RUNNING` → `COMPLETED` | `FAILED`

## Progress Tracking

While a job runs, the backend publishes progress updates to the Redis channel
`job_progress:{job_id}`. Subscribe via WebSocket v3:

```js
const jobId = "abc123-...";
const ws = new WebSocket(`${WS_V3_BASE}/ws/v3/jobs/${jobId}?token=${token}`);
ws.onmessage = (ev) => {
  const event = JSON.parse(ev.data);
  if (event.event_type === "data") {
    console.log(event.payload.progress_pct, "%", event.payload.message);
  }
};
```

The `JobProgressCard` React component handles this automatically.
