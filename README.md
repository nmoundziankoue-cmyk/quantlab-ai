# QuantLab AI

Institutional-grade quantitative research platform built milestone-by-milestone in **pure Python** — no scipy, numpy, pandas, or TA-Lib. Gaussian elimination, Pearson correlation, matrix inversion, Monte Carlo simulation, and Black-Scholes pricing all hand-implemented.

[![CI](https://github.com/nmoundziankoue-cmyk/quantlab-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/nmoundziankoue-cmyk/quantlab-ai/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-4%2C660%20passing-brightgreen)](https://github.com/nmoundziankoue-cmyk/quantlab-ai/actions)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)](backend/requirements.txt)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](frontend/package.json)

---

## What it does

| Module | Capability |
|---|---|
| **Portfolio Analytics** | Real-time P&L, multi-asset rebalancing, Greeks, risk attribution |
| **Backtesting Engine** | Signal-driven (LONG/SHORT/FLAT), order simulation, walk-forward validation |
| **Monte Carlo** | GBM + Bootstrap, 500-path simulation, VaR/CVaR at configurable confidence |
| **Regime Detection** | BULL/BEAR/HIGH_VOL/LOW_VOL/RANGING via MA crossover, realized vol, momentum |
| **Correlation Analysis** | N×N Pearson matrices, rolling correlation, greedy cluster detection |
| **Strategy Comparison** | Sharpe/Sortino/Calmar ranking, composite score, equity-curve correlation |
| **Factor Models** | OLS regression, Gauss-Jordan elimination, multi-factor decomposition |
| **Portfolio Optimisation** | Mean-Variance, Min-Variance, Max-Sharpe, Risk-Parity — all from scratch |
| **Event Intelligence** | 28 corporate + 19 macro event types, event study (AR/CAR/CAAR) |
| **Auth & Security** | JWT, TOTP MFA (RFC 6238), 8-tier RBAC, brute-force protection |
| **AI Agents** | 7 specialised research agents + multi-agent orchestrator |
| **Real-Time OS** | WebSocket streaming, alert engine, feature engine (21 indicators) |

---

## Demo — 5 pages to see first

Once running, open these URLs in order:

| # | URL | What you'll see |
|---|---|---|
| 1 | `http://localhost:5173/` | Portfolio dashboard — equity curve vs S&P 500, 6 KPI cards, allocation bars, module navigator |
| 2 | `http://localhost:5173/m20/regime` | Live regime detection — BULL/BEAR confidence, bar-by-bar history, regime distribution |
| 3 | `http://localhost:5173/m20/comparison` | Strategy ranking — 3 strategies backtested, Sharpe/Sortino/Calmar table, equity-curve correlation matrix |
| 4 | `http://localhost:5173/m20/correlation` | Pearson heatmap — AAPL/MSFT/GOOGL/AMZN, colour-coded green (positive) to red (negative) |
| 5 | `http://localhost:5173/m19-monte-carlo` | Monte Carlo viewer — 500 GBM paths, VaR distribution, confidence intervals |

All 5 pages auto-populate on load — no manual button clicks needed.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL (optional — M18–M20 run fully in-memory without it) |
| Cache | Redis (optional — falls back to in-memory) |
| Frontend | React 18, React Router v6, Vite, Recharts, Zustand |
| Auth | JWT + refresh tokens, bcrypt, TOTP MFA |
| Containers | Docker, Docker Compose, Nginx |
| CI | GitHub Actions — backend tests + frontend build + Docker smoke test |

---

## Quick Start

### Option A — One command (recommended)

```bash
git clone https://github.com/nmoundziankoue-cmyk/quantlab-ai.git
cd quantlab-ai

# 1. Configure environment
cp backend/.env.example backend/.env
# Generate a secure key and paste it into backend/.env as JWT_SECRET_KEY:
python3 -c "import secrets; print(secrets.token_hex(32))"

# 2. Start everything (kills stale processes, creates venv, installs deps, polls health)
./start.sh

# 3. Open
#   Frontend → http://localhost:5173
#   Swagger   → http://localhost:8001/docs
```

> **Note:** Without Docker, PostgreSQL-dependent features (auth login, portfolio CRUD) return graceful errors. All M18–M20 quant features work fully in-memory.

### Option B — With Docker (full stack including PostgreSQL + Redis)

```bash
git clone https://github.com/nmoundziankoue-cmyk/quantlab-ai.git
cd quantlab-ai
cp backend/.env.example backend/.env
# Edit backend/.env: set JWT_SECRET_KEY (generate as above)

./start.sh --with-docker
# Or manually:
# docker compose up -d          # PostgreSQL + Redis
# cd backend && .venv/bin/python -m alembic upgrade head
# uvicorn main:app --port 8001 --reload
# cd ../frontend && npm run dev
```

### Option C — Development mode (manual)

```bash
# Terminal 1 — backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then set JWT_SECRET_KEY
uvicorn main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend
npm install
npm run dev          # http://localhost:5173
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET_KEY` | **Yes** | 32-byte hex — `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | For auth/portfolio | PostgreSQL connection string |
| `REDIS_URL` | No | Falls back to in-memory if empty |
| `CORS_ORIGINS` | No | Comma-separated origins for production |
| `ENVIRONMENT` | No | `development` (default) or `production` |

> The app **refuses to start** if `JWT_SECRET_KEY` is not set or is the CHANGE_ME placeholder.

---

## Project Structure

```
quantlab-ai/
├── backend/
│   ├── main.py                  FastAPI app — router registration, CORS, lifespan
│   ├── config.py                Pydantic v2 settings (validates JWT on startup)
│   ├── requirements.txt         72 pinned packages (pip freeze)
│   ├── .env.example             Template — copy to .env before starting
│   ├── services/                40+ service modules (pure-Python quant engines)
│   │   ├── m20_regime_detection.py
│   │   ├── m20_correlation_covariance.py
│   │   ├── m20_strategy_comparison.py
│   │   ├── m19_backtest_engine.py
│   │   ├── m19_monte_carlo.py
│   │   └── ...
│   ├── routers/                 REST API (150 endpoints)
│   ├── schemas/                 Pydantic v2 request/response models
│   ├── models/                  SQLAlchemy ORM
│   ├── alembic/                 Database migrations
│   └── tests/                   40+ test files — 4,660 passing tests
├── frontend/
│   └── src/
│       ├── pages/               65+ lazy-loaded React pages
│       ├── api/                 Axios client (guest mode, 401 handling)
│       └── store/               Zustand auth store
├── docker-compose.yml           PostgreSQL + Redis
├── docker-compose.prod.yml      Full production stack (backend + frontend + Nginx)
├── start.sh                     One-command local launcher
├── ARCHITECTURE.md              System design + engineering decisions
└── .github/workflows/ci.yml     GitHub Actions — test + build + Docker smoke test
```

---

## Milestone History

| Milestone | Scope | Tests |
|---|---|---|
| M0–M4 | Portfolio CRUD, market data, JWT auth | 190 |
| M5–M7 | WebSocket streaming, options pricing (Black-Scholes), 7 AI agents | 856 |
| M8 | Auth enterprise: TOTP MFA, 8-tier RBAC, brute-force protection | 987 |
| M9 | Provider health monitoring, options strategies, WebSocket v3 | 1,562 |
| M10–M14 | Alternative data, knowledge graph, portfolio optimiser, event intelligence | 2,065 |
| M15 | Event study engine — 28 corporate + 19 macro event types, AR/CAR/CAAR | 2,441 |
| M16–M17 | Multi-asset engine, institutional trading & order management | 3,279 |
| M18 | Real-Time Institutional OS — streaming, alerts, microstructure, feature engine | 4,002 |
| M19 | Quant Research Engine — backtest, Monte Carlo, factor models, optimisation | 4,424 |
| M20 | Platform Closeout — regime detection, correlation analysis, strategy comparison | **4,660** |

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -q
# Expected without PostgreSQL running:
#   4,660 passed — all quant/logic tests
#   332 collection errors — SQLAlchemy "connection refused port 5432" (expected)
#   0 unexpected failures
```

Run with Docker for 100% pass rate:
```bash
docker compose up -d
cd backend && .venv/bin/python -m alembic upgrade head
python -m pytest tests/ -q
```

---

## API

Interactive Swagger UI: `http://localhost:8001/docs`

| Prefix | Module | Endpoints |
|---|---|---|
| `/quant/m20` | Regime · Correlation · Strategy Comparison | 38 |
| `/quant` | M19 Backtest · Monte Carlo · Factor · Optimisation | 112 |
| `/research` | M18 Real-Time Analytics | ~80 |
| `/portfolio` | Portfolio CRUD, P&L, risk snapshots | ~30 |
| `/auth` | Login, MFA, token refresh | 12 |

---

## Security

- `JWT_SECRET_KEY` has **no hardcoded default** — startup fails without an explicit value
- `.env` is in `.gitignore` and has never been committed
- All secrets are environment-variable-only (never hardcoded)
- CORS: open in `development`, restricted to `CORS_ORIGINS` in `production`
- Passwords: bcrypt with configurable cost
- Auth endpoints: TOTP MFA + brute-force lockout after 10 attempts
