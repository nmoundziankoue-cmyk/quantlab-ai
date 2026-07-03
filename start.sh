#!/usr/bin/env bash
# QuantLab AI — local dev startup script
# Usage: ./start.sh [--with-docker]
# Stops any stale processes first, then starts backend + frontend.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"
BACKEND_LOG="$REPO_DIR/.backend.log"
FRONTEND_LOG="$REPO_DIR/.frontend.log"
BACKEND_PORT=8001
FRONTEND_PORT=5173

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }

# ── 1. Kill stale processes on the target ports ───────────────────────────────
echo ""
echo "── Stopping stale processes ──────────────────────────────────────"
for PORT in $BACKEND_PORT $FRONTEND_PORT; do
  PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
  if [[ -n "$PIDS" ]]; then
    kill $PIDS 2>/dev/null || true
    warn "Killed process(es) on port $PORT: $PIDS"
  fi
done
sleep 1

# ── 2. Preflight checks ───────────────────────────────────────────────────────
echo ""
echo "── Preflight checks ──────────────────────────────────────────────"

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  fail ".env missing — run these commands first:"
  echo "    cp backend/.env.example backend/.env"
  echo "    python3 -c \"import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))\" >> backend/.env"
  exit 1
fi
ok ".env present"

if ! grep -q "^JWT_SECRET_KEY=" "$BACKEND_DIR/.env" || grep -q "CHANGE_ME" "$BACKEND_DIR/.env"; then
  fail "JWT_SECRET_KEY not set or still CHANGE_ME in backend/.env"
  echo "    Generate: python3 -c \"import secrets; print(secrets.token_hex(32))\""
  exit 1
fi
ok "JWT_SECRET_KEY configured"

if [[ ! -f "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
  warn "No .venv found — installing dependencies..."
  python3 -m venv "$BACKEND_DIR/.venv"
  "$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q
fi
ok "Python venv ready"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  warn "node_modules missing — running npm install..."
  cd "$FRONTEND_DIR" && npm install -q
fi
ok "Node modules ready"

# ── 3. Optional: start Docker DB + Redis ─────────────────────────────────────
if [[ "${1:-}" == "--with-docker" ]]; then
  echo ""
  echo "── Starting Docker services (PostgreSQL + Redis) ─────────────────"
  if ! docker info &>/dev/null; then
    fail "Docker Desktop is not running. Open Docker Desktop first."
    exit 1
  fi
  docker compose -f "$REPO_DIR/docker-compose.yml" up -d
  ok "PostgreSQL + Redis started"
  echo "   Waiting 8s for DB to be ready..."
  sleep 8
  cd "$BACKEND_DIR" && .venv/bin/python -m alembic upgrade head 2>&1 | tail -3
  ok "Alembic migrations applied"
fi

# ── 4. Start backend ──────────────────────────────────────────────────────────
echo ""
echo "── Starting backend ──────────────────────────────────────────────"
cd "$BACKEND_DIR"
nohup .venv/bin/uvicorn main:app --port "$BACKEND_PORT" --reload \
  > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$REPO_DIR/.backend.pid"

# Wait for backend to be ready (max 20s)
for i in $(seq 1 20); do
  if curl -sf "http://localhost:$BACKEND_PORT/system/health" &>/dev/null; then
    ok "Backend up (PID $BACKEND_PID)"
    break
  fi
  if [[ $i -eq 20 ]]; then
    fail "Backend did not start in 20s. Last log:"
    tail -20 "$BACKEND_LOG"
    exit 1
  fi
  sleep 1
done

# ── 5. Start frontend ─────────────────────────────────────────────────────────
echo ""
echo "── Starting frontend ─────────────────────────────────────────────"
cd "$FRONTEND_DIR"
nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$REPO_DIR/.frontend.pid"

# Wait for frontend to be ready (max 15s)
for i in $(seq 1 15); do
  if curl -sf "http://localhost:$FRONTEND_PORT/" &>/dev/null; then
    ok "Frontend up (PID $FRONTEND_PID)"
    break
  fi
  if [[ $i -eq 15 ]]; then
    fail "Frontend did not start in 15s. Last log:"
    tail -10 "$FRONTEND_LOG"
    exit 1
  fi
  sleep 1
done

# ── 6. Summary ────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════"
ok "QuantLab AI is running"
echo ""
echo "  Frontend  →  http://localhost:$FRONTEND_PORT"
echo "  Swagger   →  http://localhost:$BACKEND_PORT/docs"
echo "  Health    →  http://localhost:$BACKEND_PORT/system/health"
echo ""
echo "  Logs: tail -f $BACKEND_LOG"
echo "        tail -f $FRONTEND_LOG"
echo ""
echo "  Stop:  kill \$(cat .backend.pid) \$(cat .frontend.pid)"
echo "══════════════════════════════════════════════════════════════════"
