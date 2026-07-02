# ── Stage 1: dependency install ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only build tools, not runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

COPY . .

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/system/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
