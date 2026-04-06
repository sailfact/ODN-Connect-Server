# ODN Connect Server

Self-hosted WireGuard VPN server with a full-stack web UI for peer management. Designed to be consumed by the [ODN Connect](../ODN-CONNECT/) Electron desktop client.

## Features

- **Admin portal** — peer CRUD, user management, audit log, live handshake status
- **User portal** — self-service peer creation, `.conf` download, QR code, TOTP setup
- **ODN Connect API** — server-info onboarding endpoint, config sync with `Last-Modified` header
- **JWT auth** — 15-minute access tokens, 7-day refresh tokens with rotation, Redis invalidation
- **TOTP** — required for admin accounts, optional for users
- **WireGuard hot-reload** — atomic config rewrite + `wg syncconf` (no tunnel restart)
- **Rate limiting** — per-IP on auth (5/min), server-info (10/min), and general API (60/min)
- **Audit log** — append-only, includes ODN Connect `User-Agent` tracking

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12), SQLAlchemy 2.0 async |
| Database | PostgreSQL 16 |
| Cache / sessions | Redis 7 |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Reverse proxy | NGINX (TLS termination) |
| VPN | WireGuard (linuxserver/wireguard) |
| Auth | JWT (HS256), bcrypt (cost 12), pyotp TOTP |

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, JWT_SECRET, WG_SERVER_PUBLIC_IP
```

Generate a strong JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

### 2. Generate WireGuard server keys

```bash
docker compose run --rm backend python manage.py init-wg
```

### 3. Start all services

```bash
docker compose up --build -d
```

### 4. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 5. Access

| URL | Description |
|-----|-------------|
| `https://localhost/admin` | Admin portal |
| `https://localhost/portal` | User portal |
| `https://localhost/api/docs` | API documentation (Swagger) |

Default admin credentials: `admin@example.com` / `changeme`

> **Important:** Change the default admin password and enable TOTP before exposing to the internet.

## Development

Uses `docker-compose.override.yml` automatically for hot reload and exposed ports:

```bash
docker compose up --build
# Backend auto-reloads at http://localhost:8000
# Frontend dev server at http://localhost:3000
# NGINX proxy at http://localhost:80
```

Run backend tests:
```bash
docker compose exec backend pytest
```

## Architecture

```
NGINX :443 (TLS)
  ├── /api/auth/*     → backend:8000  (rate: 5/min)
  ├── /api/client/*   → backend:8000  (rate: 10/min)
  ├── /api/*          → backend:8000  (rate: 60/min)
  └── /               → frontend:3000

backend → PostgreSQL (peers, users, audit_log)
backend → Redis (refresh tokens, rate limiting)
backend → wg-config volume (wg0.conf, hot-reload via wg syncconf)
wireguard → wg-config volume, UDP :51820
```

## API Reference

### Public

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login, returns JWT + refresh token |
| `POST` | `/api/auth/refresh` | Rotate refresh token |
| `POST` | `/api/auth/logout` | Revoke refresh token |
| `GET` | `/api/client/server-info` | Server onboarding info (ODN Connect) |

### User (authenticated)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/me/peers` | List own peers |
| `POST` | `/api/me/peers` | Create own peer (if self-service enabled) |
| `DELETE` | `/api/me/peers/{id}` | Delete own peer |
| `GET` | `/api/me/peers/{id}/config` | Download `.conf` file |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/peers` | List all peers |
| `POST` | `/api/peers` | Create peer |
| `PATCH` | `/api/peers/{id}` | Update peer (enable/disable) |
| `DELETE` | `/api/peers/{id}` | Delete peer |
| `GET` | `/api/admin/users` | List users |
| `POST` | `/api/admin/users` | Create user |
| `DELETE` | `/api/admin/users/{id}` | Delete user |
| `GET` | `/api/status` | Server + handshake status |
| `GET` | `/api/admin/audit` | Audit log |

## ODN Connect Integration

ODN Connect calls this server from its Electron main process. Key contract points:

- `GET /api/client/server-info` — unauthenticated, returns `{ server_name, public_key, endpoint, dns, allowed_ips, api_base_url }`
- `GET /api/me/peers/{id}/config` — returns `text/plain` WireGuard `.conf` with `Last-Modified` header for change detection
- JWT claims: `sub` (user UUID), `role` (`admin|user`), `exp`
- Self-service peer creation: client generates keypair locally, sends `public_key` to server — private key never leaves the client

## Directory Structure

```
.
├── backend/
│   ├── app/
│   │   ├── core/           # config, security, deps
│   │   ├── db/             # session, base, Alembic migrations
│   │   ├── models/         # User, Peer, AuditLog
│   │   ├── routers/        # auth, peers, users, status, client, audit
│   │   └── services/       # wg_manager, ip_allocator
│   ├── tests/client_api/   # ODN Connect contract tests
│   ├── manage.py           # init-wg, create-admin commands
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── pages/admin/    # Dashboard, Peers, Users, Audit
│       ├── pages/portal/   # Peers, Profile
│       ├── api/            # typed API clients
│       └── store/          # Zustand auth store
├── nginx/
│   ├── nginx.conf          # production (TLS + rate limiting)
│   └── nginx.dev.conf      # development (plain HTTP)
├── scripts/
│   ├── generate-keys.sh    # server keypair init
│   └── backup-db.sh        # PostgreSQL backup (schedule via cron)
├── docker-compose.yml
├── docker-compose.override.yml  # dev overrides
└── .env.example
```

## Security Notes

- Passwords hashed with bcrypt (cost 12)
- TOTP **required** for admin accounts — admins without a TOTP secret cannot log in
- JWT refresh tokens stored in Redis; revoked on logout
- WireGuard pre-shared keys generated per peer
- `NET_ADMIN` / `SYS_MODULE` capabilities scoped to the `wireguard` container only
- Secrets via `.env` — never baked into images
- `/api/client/server-info` exposes no private keys or peer list

## Deployment Checklist

- [ ] Set all secrets in `.env`
- [ ] Point DNS A record to server IP
- [ ] Open `443/tcp`, `80/tcp`, `51820/udp` in firewall
- [ ] Mount real TLS certs into `certs` volume (or configure Certbot)
- [ ] Run `docker compose up -d`
- [ ] Run `alembic upgrade head`
- [ ] Change default admin password
- [ ] Enable TOTP on admin account (`/portal/profile`)
- [ ] Test peer creation and config download
- [ ] Test ODN Connect onboarding against `/api/client/server-info`
- [ ] Schedule `scripts/backup-db.sh` via cron

## License

MIT
