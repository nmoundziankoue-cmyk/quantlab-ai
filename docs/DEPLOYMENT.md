# Deployment Guide

## Prerequisites

- Docker Desktop running
- `docker compose` v2

---

## Local Development

```bash
# 1. Start PostgreSQL + Redis
docker compose up -d db redis

# 2. Backend
cd backend
cp .env.example .env          # fill in JWT_SECRET_KEY at minimum
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8001

# 3. Frontend
cd frontend
npm install
VITE_API_URL=http://localhost:8001 npm run dev
```

---

## Production (Docker Compose)

```bash
# Copy and edit production env
cp backend/.env.example backend/.env.prod

# Edit .env.prod — set strong JWT_SECRET_KEY, POSTGRES_PASSWORD, CORS_ORIGINS

docker compose -f docker-compose.prod.yml up -d --build
```

Services started:
- `db` — PostgreSQL 16
- `redis` — Redis 7
- `backend` — FastAPI (uvicorn, 4 workers)
- `frontend` — Nginx serving the Vite build + reverse proxy

Migrations run automatically on backend startup via the startup event handler.

### TLS

Place your certificate chain and key at:
```
./certs/fullchain.pem
./certs/privkey.pem
```

The nginx config at `nginx.conf` handles HTTP→HTTPS redirect, TLS termination,
API proxying (`/api/`), WebSocket passthrough (`/ws`, `/ws/`), and SPA routing.

---

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs on push to `main`/`develop`:

1. **backend-test** — spins up PostgreSQL + Redis services, runs Alembic
   migrations, runs the full test suite with coverage
2. **frontend-build** — runs `npm ci` and `npm run build`
3. **docker-build** (main branch only) — smoke-tests `docker build` for
   both backend and frontend images

### Required secrets

Set these in GitHub repository settings → Secrets:

| Secret | Description |
|---|---|
| `JWT_SECRET_KEY` | Production JWT signing secret |
| `POSTGRES_PASSWORD` | Database password |

---

## Health Checks

| Endpoint | Purpose |
|---|---|
| `GET /system/health` | Basic liveness (DB + cache) |
| `GET /system/redis/health` | Redis connection status |
| `GET /system/metrics` | Prometheus metrics |
| `GET /providers/health` | Market data provider health scores |
| `GET /market/circuit-breakers` | Provider circuit breaker states |
