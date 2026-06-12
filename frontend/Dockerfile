FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

# ── dev stage ──────────────────────────────────────────────────────────────
FROM base AS dev
# Source mounted at runtime

# ── build stage ─────────────────────────────────────────────────────────────
FROM base AS builder
COPY . .
RUN npm run build

# ── production stage ────────────────────────────────────────────────────────
FROM nginx:alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
