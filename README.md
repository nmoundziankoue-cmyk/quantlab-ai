# QuantLab AI

Institutional-grade quantitative portfolio analytics platform built milestone-by-milestone in pure Python (no scipy / numpy / pandas).

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

**Pure-Python constraint:** all quantitative math (matrix inversion, Pearson correlation, option pricing, OLS regression) is implemented from scratch — zero C-extension scientific libraries.

---

## How to Run Locally

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development only)

### Docker (recommended)

```bash
git clone <repo>
cd apexquant-v25

# Copy and configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env: set DATABASE_URL, JWT_SECRET_KEY

# Start all services (backend + frontend + PostgreSQL + Redis)
docker compose up --build
```

The API will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

### Development without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in DATABASE_URL
alembic upgrade head
uvicorn main:app --reload  # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                # http://localhost:5173
```

---

## API Documentation

Interactive Swagger UI available at `http://localhost:8000/docs` once running.

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
apexquant-v25/
├── backend/
│   ├── main.py              FastAPI app entry point
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
├── docker-compose.yml
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
# Expected: ~4,660 passed, 15 failed (DB tests), 332 errors (PostgreSQL not running)
```

All 332 collection errors are `sqlalchemy.exc.OperationalError: connection refused port 5432` — expected without a running PostgreSQL. Zero code errors.

---

## Environment Variables

See [backend/.env.example](backend/.env.example) for the full list. Required for production:

- `DATABASE_URL` — PostgreSQL connection string
- `JWT_SECRET_KEY` — 32-byte random hex string (`python -c "import secrets; print(secrets.token_hex(32))"`)

Optional:
- `REDIS_URL` — Redis connection (falls back to in-memory if not set)
- `CORS_ORIGINS` — Comma-separated allowed origins (empty = localhost dev mode)
