# M10 Architecture — QuantLab AI (ApexQuant v25)

## Overview

QuantLab AI is a full-stack institutional-grade financial analysis platform.
The M10 milestone adds enterprise production readiness on top of a fully
functional M9 base: real authentication, persistent database models, Redis
infrastructure, production-grade market data, WebSocket v3, background jobs,
portfolio ownership, comprehensive observability, and security hardening.

---

## Backend Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI 0.111+ |
| Database ORM | SQLAlchemy 2.x + Alembic migrations |
| Database | PostgreSQL 16 (Docker) |
| Cache / pub-sub | Redis 7 (Docker) + in-memory fallback |
| Auth | Custom HMAC-SHA256 JWT (stdlib), PBKDF2-SHA256 passwords |
| Config | pydantic_settings (`.env` + env vars) |
| Background jobs | ThreadPoolExecutor + BackgroundJob DB model |
| Metrics | In-process MetricsCollector → Prometheus text format |

## Frontend Stack

| Layer | Technology |
|---|---|
| Framework | React 18 + React Router v7 |
| State | Zustand with `persist` middleware |
| HTTP client | Axios with JWT interceptor + single-flight refresh |
| WebSocket | Custom `useWebSocket` hook (v1/v2/v3) |
| Build | Vite |

---

## Directory Layout

```
apexquant-v25/
├── backend/
│   ├── alembic/versions/       # Migration chain (M1–M10)
│   ├── middleware/             # RBAC, request-id, request-size, security-headers
│   ├── models/                 # SQLAlchemy ORM models
│   ├── routers/                # 31+ APIRouters
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic, cache, metrics, streaming
│   ├── tests/                  # 1622 test cases
│   ├── config.py               # pydantic_settings BaseSettings
│   ├── database.py             # Engine, session factory, get_db()
│   └── main.py                 # FastAPI app, middleware, router registration
├── frontend/
│   ├── src/
│   │   ├── api/                # authApi.js, client.js (axios + interceptors)
│   │   ├── components/         # Layout, UI primitives, domain components
│   │   ├── context/            # ToastContext
│   │   ├── hooks/              # useWebSocket, domain hooks
│   │   ├── pages/              # 40+ lazy-loaded page components
│   │   └── store/              # Zustand stores
│   └── vite.config.js
├── docker-compose.yml          # Development (PostgreSQL + Redis)
├── docker-compose.prod.yml     # Production (backend + frontend + nginx)
├── nginx.conf                  # Reverse proxy + TLS + WS passthrough
└── .github/workflows/ci.yml    # GitHub Actions CI
```

---

## M10 Key Additions

### Authentication (Phase 1)
- JWT secret read from `settings.jwt_secret_key` (not hardcoded)
- `jti` claim added to every token for revocation
- Token blacklist stored in Redis (or in-memory) keyed by `jti`
- `/auth/me`, `/auth/logout`, `/auth/refresh`, `/auth/roles` endpoints
- Password policy: 8+ chars, uppercase, lowercase, digit
- Frontend: Zustand auth store with `persist`, axios 401 interceptor, `ProtectedRoute`

### Database (Phase 2)
- Alembic migration chain: 9 migrations covering all M1–M10 tables
- M10 tables: `trading_strategies`, `agent_sessions`, `agent_messages`,
  `websocket_events`, `background_jobs`, `provider_health_snapshots`
- `get_db()` commits on success, rolls back on exception

### Redis (Phase 3)
- `CacheBackend`: Redis primary + in-memory fallback, transparent
- Namespaced keys (`quant:` prefix via `ns_get/ns_set`)
- Token blacklist (`quant:blacklist:{jti}`)
- Pub/sub via `cache.publish()` / `cache.get_pubsub()`
- `/system/redis/health` endpoint

### Market Data (Phase 4)
- `CircuitBreaker` per provider: CLOSED → OPEN (3 failures) → HALF_OPEN (30s cooldown)
- `MarketDataRouter` uses `CacheBackend` for shared quote cache
- Stale-while-revalidate in `quotes.py`: fresh (30s) / stale (5 min) / expired
- Cache hit/miss reported to `MetricsCollector`
- `/market/circuit-breakers` endpoint for operational visibility

### WebSocket v3 (Phase 5)
- `services/streaming_v3.py`: real JWT auth, RBAC channel gating, event replay
- `routers/streaming_v3.py`: `/ws/v3`, `/ws/v3/market/{ticker}`, `/ws/v3/jobs/{job_id}`
- `job_progress:{job_id}` channel added to channel registry
- Redis pub/sub fan-out bridge (when Redis connected)
- v1 and v2 endpoints untouched

### Background Jobs (Phase 6)
- `BackgroundJob` model with idempotency key, retry, progress_pct
- `/jobs` CRUD: POST (202), GET list, GET by id, DELETE, POST retry
- ThreadPoolExecutor for async execution; WS progress via `cache.publish()`
- Job types: `echo`, `market_data_refresh`, `portfolio_risk_snapshot`, `strategy_backtest`

### Portfolio Persistence (Phase 7)
- `owner_id` nullable UUID column on `portfolios` table
- `portfolio_risk_snapshots` table (id, portfolio_id, taken_at, totals, positions_count, metadata)
- Portfolio list/create endpoints scoped by authenticated user
- `POST /portfolios/{id}/risk-snapshots` — persist on-demand risk snapshot
- `GET /portfolios/{id}/risk-snapshots` — retrieve snapshot history

### Observability (Phase 8)
- `MetricsCollector`: thread-safe counters, histograms (request latency, job durations)
- `GET /system/metrics` — Prometheus text format
- `GET /system/metrics/json` — JSON format
- `RequestIdMiddleware` instruments every request
- Active WS connection count tracked

### Security (Phase 9)
- `RequestSizeLimitMiddleware`: rejects bodies > 10 MB (413)
- `SecurityHeadersMiddleware`: HSTS, X-Frame-Options, X-Content-Type-Options
- `validate_password_policy()`: enforced on all registration paths
- Token revocation on logout via `jti` blacklist

### Frontend (Phase 10)
- `ErrorBoundary` class component wrapping entire app
- `ToastProvider` + `useToast()` hook for success/error/info/warning toasts
- `Skeleton` + `SkeletonCard` loading placeholders
- `WsIndicator` pill showing live/connecting/disconnected/error state
- `JobProgressCard` component for background job tracking
- Shell connects to `/ws/v3` and displays WS connection state in topbar

---

## Environment Variables

See `backend/.env.example` for a full list. Required for production:

```bash
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
JWT_SECRET_KEY=<32+ random bytes>
ENVIRONMENT=production
CORS_ORIGINS=https://your-domain.com
```
