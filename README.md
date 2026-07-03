# QuantLab AI

Institutional-grade quantitative portfolio analytics platform built milestone-by-milestone in pure Python (no scipy / numpy / pandas for the quant core).

---

## Features

- **Portfolio Analytics** — real-time P&L, Greeks, risk attribution, multi-asset rebalancing
- **Market Data** — multi-provider failover (Yahoo Finance + 6 stubs), streaming via WebSocket
- **Backtesting** — signal-driven engine (LONG/SHORT/FLAT), order simulation, walk-forward validation
- **Quant Research** — factor models (OLS, Gauss-Jordan), Monte Carlo (GBM + Bootstrap), portfolio optimisation (MV/MinVar/MaxSharpe/RiskParity)
- **Regime Detection** — BULL/BEAR/HIGH_VOL/LOW_VOL/RANGING via MA crossover, realized vol, momentum
- **Correlation Analysis** — N×N Pearson matrices, rolling correlation, asset cluster detection
- **Strategy Comparison** — Sharpe/Sortino/Calmar ranking, head-to-head, equity-curve correlation
- **Event Intelligence** — 28 corporate event types, 19 macro event types, event study (AR/CAR/CAAR)
- **Auth & Security** — JWT, TOTP MFA (RFC 6238), 8-tier RBAC, brute-force protection
- **AI Agents** — 7 specialized research agents + multi-agent orchestrator

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 |
| Database | PostgreSQL + Alembic migrations |
| Cache | Redis (optional, falls back to in-memory) |
| Frontend | React 18, React Router v6, Vite, Recharts |
| Containers | Docker, Docker Compose |

---

## Quick Start (Docker — recommended)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and **running**
- Git

### 1. Clone

```bash
git clone https://github.com/nmoundziankoue-cmyk/quantlab-ai.git
cd quantlab-ai
```

### 2. Configure environment variables

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and replace `JWT_SECRET_KEY` with a real secret (the app **will not start** without this):

```bash
# Generate a secure key:
python -c "import secrets; print(secrets.token_hex(32))"
# Paste the output as the value of JWT_SECRET_KEY in backend/.env
```

### 3. Start everything

```bash
# Start PostgreSQL + Redis only (fast, for dev mode below)
docker compose up -d

# OR start the full stack (PostgreSQL + Redis + backend + frontend via nginx)
docker compose --profile full up --build
```

### 4. Run database migrations

```bash
# With Docker DB running, apply Alembic migrations:
docker exec apexquant_backend alembic upgrade head
# OR locally (if running backend outside Docker):
cd backend && .venv/bin/python -m alembic upgrade head
```

### 5. Open in browser

| Service | URL |
|---|---|
| **Frontend** | http://localhost (Docker full) or http://localhost:5173 (dev) |
| **Swagger UI** | http://localhost:8001/docs |
| **API backend** | http://localhost:8001 |

---

## Development Mode (without Docker frontend)

Run PostgreSQL + Redis via Docker, then run backend and frontend locally:

```bash
# Terminal 1 — start DB + cache
docker compose up -d

# Terminal 2 — backend (from repo root)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env: set JWT_SECRET_KEY
python -m alembic upgrade head
uvicorn main:app --reload --port 8001

# Terminal 3 — frontend
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` before starting. Required values:

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET_KEY` | **Yes** | 32-byte hex — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Yes for auth/portfolio | PostgreSQL connection string |
| `REDIS_URL` | No | Redis (falls back to in-memory if empty) |
| `CORS_ORIGINS` | No | Comma-separated origins for production (empty = localhost dev) |
| `ENVIRONMENT` | No | `development` (default) or `production` |

---

## API Documentation

Interactive Swagger UI at `http://localhost:8001/docs` once running.

Key prefixes:

| Prefix | Description |
|---|---|
| `/portfolio` | Portfolio CRUD, P&L, risk snapshots |
| `/market` | Market data, candlesticks |
| `/quant` | M19 Quant Research Engine (112 endpoints) |
| `/quant/m20` | M20 Regime Detection, Correlation, Strategy Comparison |
| `/research` | M18 Real-Time Analytics, alerts, risk |
| `/events` | Event Intelligence (M15) |
| `/auth` | Authentication + MFA |

---

## Project Structure

```
quantlab-ai/
├── backend/
│   ├── main.py              FastAPI app entry point
│   ├── requirements.txt     Pinned Python dependencies (pip freeze)
│   ├── .env.example         Environment variable template
│   ├── services/            Business logic (40+ service modules)
│   ├── routers/             REST API endpoints
│   ├── schemas/             Pydantic v2 request/response models
│   ├── models/              SQLAlchemy ORM models
│   ├── alembic/             Database migrations
│   └── tests/               pytest test suite (4,660+ tests)
├── frontend/
│   ├── src/
│   │   ├── pages/           65+ lazy-loaded React pages
│   │   ├── api/             API client modules
│   │   └── hooks/           Custom React hooks
│   └── vite.config.js
├── docker-compose.yml       PostgreSQL + Redis (plain) / full stack (--profile full)
├── ARCHITECTURE.md          Full architecture documentation
└── README.md                This file
```

---

## Milestone History

| Milestone | Description | Tests |
|---|---|---|
| M0–M4 | Core portfolio, market data, auth | 190 |
| M5–M7 | Streaming, options, AI agents | 856 |
| M8 | Auth enterprise, MFA, notifications | 987 |
| M9 | Provider health, options strategies, WebSocket v2 | 1,562 |
| M10–M14 | Alternative data, knowledge graph, portfolio optimiser | 2,065 |
| M15 | Event intelligence (corporate + macro) | 2,441 |
| M16–M18 | Multi-asset, institutional trading, real-time analytics | 4,002 |
| M19 | Quant Research Engine (backtest, Monte Carlo, factor models) | 4,424 |
| M20 | Quant Research Platform Closeout (regime, correlation, comparison) | **4,660** |

---

## Running Tests

```bash
cd backend
python -m pytest -q
# Expected: ~4,660 passed, 15 failed (DB tests require PostgreSQL), 332 errors (PostgreSQL not running)
```

All 332 collection errors are `sqlalchemy.exc.OperationalError: connection refused port 5432` — expected without a running PostgreSQL. Zero code errors.

---

## Security

- `JWT_SECRET_KEY` has **no hardcoded default** — the app refuses to start without an explicit value set in `.env`
- `.env` is in `.gitignore` and has never been committed
- All secrets must be set via environment variables or `backend/.env` (never committed)
- CORS: open in dev mode (`ENVIRONMENT=development`), restricted to `CORS_ORIGINS` in production
- Auth endpoints use bcrypt password hashing and TOTP MFA
