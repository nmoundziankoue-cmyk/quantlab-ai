# Security Guide

## Authentication

QuantLab AI uses custom HMAC-SHA256 JWTs (stdlib only — no external JWT library).

### Token lifecycle

1. **Login** — `POST /auth/login` returns `{access_token, refresh_token}`
2. **Access token** — 24h TTL (configurable via `ACCESS_TOKEN_EXPIRE_HOURS`)
3. **Refresh token** — 30d TTL (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
4. **Logout** — `POST /auth/logout` adds the token's `jti` to the blacklist
5. **Refresh** — `POST /auth/refresh` rotates the refresh token (single-use)

### Token revocation

Every token carries a `jti` (JWT ID) claim — a 32-hex-char random string.
On logout, the `jti` is stored in Redis (or in-memory) with the remaining TTL.
`decode_token()` checks the blacklist before returning the payload.

### Password policy

Enforced at registration and password-change:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

---

## Role-Based Access Control (RBAC)

Roles (ascending privilege):

| Role | Level |
|---|---|
| VIEWER | 1 |
| ANALYST | 2 |
| TRADER | 3 |
| QUANT | 4 |
| RISK_MANAGER | 5 |
| PORTFOLIO_MANAGER | 6 |
| ADMIN | 7 |
| SUPER_ADMIN | 8 |

FastAPI dependencies:
- `get_current_user_payload` — require any valid JWT
- `get_optional_user_payload` — return None for unauthenticated requests
- `require_role("ANALYST")` — enforce minimum role

WebSocket v3 channel RBAC:
- `system_metrics`, `provider_health`, `task_queue` — require ANALYST+
- `execution_updates`, `orders`, `executions`, `positions` — require VIEWER+
- Market data channels — public (anonymous allowed)

---

## Transport Security

### Request size limit

`RequestSizeLimitMiddleware` rejects any request body > 10 MB with HTTP 413.
This prevents large payload attacks before business logic runs.

### Security headers (via `SecurityHeadersMiddleware`)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-Request-ID: <uuid>
```

### CORS

`CORS_ORIGINS` env var controls allowed origins. When empty, a regex fallback
allows `localhost:*`. In production, set to your exact domain(s):
```
CORS_ORIGINS=https://app.yourdomain.com
```

### Nginx (production)

- HTTP → HTTPS redirect (301)
- TLS 1.2+ only; strong cipher suite
- `client_max_body_size 10m` (mirrors middleware limit)
- `/system/metrics` restricted to private IP ranges only

---

## Secrets Management

All secrets are read from environment variables via `pydantic_settings`.
**Never hardcode secrets in source code.**

Required secrets:

| Variable | Description |
|---|---|
| `JWT_SECRET_KEY` | ≥32 random bytes; used for all HMAC-SHA256 signing |
| `DATABASE_URL` | Full PostgreSQL connection string with credentials |
| `REDIS_URL` | Redis connection string |

Generate a strong secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
