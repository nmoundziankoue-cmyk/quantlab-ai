# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# ── Stage 2: serve with nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA fallback: route all paths to index.html
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    location ~* \.(js|css|png|jpg|ico|woff2?)$ { \
        expires 1y; add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s \
    CMD wget -qO- http://localhost/ || exit 1
