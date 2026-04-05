# WireGuard VPN Server — CLAUDE.md

## Project overview

A self-hosted WireGuard VPN server with a full-stack web UI for peer management.
Deployable via Docker Compose. Supports both an admin portal (full control) and a
user self-service portal (download own config, view status).

**Paired client**: ODN Connect (Electron + React + TypeScript desktop client).
See `ODN-CONNECT/CLAUDE.md` for the client-side architecture. This server is the
source of truth for peer configs, user accounts, and connection status that ODN
Connect consumes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Docker host                                                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ NGINX (reverse proxy — TLS termination, :443)        │   │
│  └───────────┬──────────────┬──────────────────────────┘   │
│              │              │                               │
│    ┌─────────▼──┐  ┌────────▼────────┐  ┌───────────────┐ │
│    │ WireGuard  │  │ Backend API      │  │ Frontend SPA  │ │
│    │ UDP :51820 │  │ FastAPI / Go     │  │ React :3000   │ │
│    └─────┬──────┘  └──┬──────┬───────┘  └───────────────┘ │
│          │            │      │                              │
│    ┌─────▼──────┐  ┌──▼──┐  ┌▼──────────────┐             │
│    │ WG Manager │  │Redis│  │ Auth service   │             │
│    │ peer CRUD  │  └─────┘  │ JWT/TOTP/OIDC  │             │
│    └─────┬──────┘           └───────────────┘              │
│          │                                                  │
│    ┌─────▼──────┐  ┌─────────────────────────┐             │
│    │ PostgreSQL │  │ Config watcher           │             │
│    │ (peers,    │  │ wg syncconf / inotify    │             │
│    │  users,    │  └─────────────────────────┘             │
│    │  audit)    │                                           │
│    └────────────┘                                           │
│                                                             │
│  Volumes: wg-config  pg-data  certs                         │
└─────────────────────────────────────────────────────────────┘
         ↑ consumed by ODN Connect desktop client
```

---

## Services

### `nginx`
- TLS termination (Let's Encrypt via Certbot or mounted certs)
- Routes `/api/*` → backend, `/` → frontend, no direct access to internal ports

### `wireguard`
- Runs the kernel module via `wg-quick` or `boringtun` (userspace fallback)
- Needs `NET_ADMIN` + `SYS_MODULE` capabilities and `/dev/net/tun`
- Config lives in `wg-config` volume at `/etc/wireguard/wg0.conf`
- UDP `:51820` exposed on the host

### `backend`
- REST API — all peer and user management logic
- Talks to PostgreSQL for persistence, Redis for sessions/rate-limiting
- Calls `wg-manager` to apply config changes
- JWT-authenticated; role-based (admin vs user)

### `frontend`
- React SPA served via NGINX (or its own node server in dev)
- Two route groups: `/admin/*` (admin only) and `/portal/*` (authenticated users)

### `auth`
- Issues and validates JWTs
- Supports local credentials + TOTP; optional OIDC SSO (Entra, Google, Okta)
- Refresh token rotation, session invalidation via Redis

### `wg-manager`
- Thin service (or library used directly by backend) that writes peer stanzas to
  the WireGuard config file and calls `wg syncconf` / `wg set` for hot-reload
- No full tunnel restart needed for peer add/remove

### `config-watcher`
- Watches the `wg-config` volume for changes
- Applies them live with `wg syncconf wg0 /etc/wireguard/wg0.conf`
- Can be a sidecar on the `wireguard` container

### `postgres`
- Stores: users, peers (public keys, IPs, labels), audit log, TOTP secrets
- Migrations managed by Alembic (Python) or golang-migrate (Go)

### `redis`
- JWT refresh token store
- Session invalidation set
- Rate-limiting counters (per-IP and per-user)

---

## Key data models

```
users
  id, email, hashed_password, role (admin|user),
  totp_secret, is_active, created_at

peers
  id, user_id (FK), name, public_key, preshared_key,
  allowed_ips, assigned_ip, dns, enabled,
  last_handshake (polled), created_at,
  client_label (optional — e.g. "Ross's MacBook", set by ODN Connect)

audit_log
  id, actor_id, action, target_type, target_id,
  detail (jsonb), ip_address, created_at
```

---

## API surface (backend)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | public | Obtain JWT + refresh token |
| POST | `/api/auth/refresh` | user | Rotate refresh token |
| POST | `/api/auth/logout` | user | Invalidate refresh token |
| GET | `/api/peers` | admin | List all peers |
| POST | `/api/peers` | admin | Create peer |
| DELETE | `/api/peers/{id}` | admin | Remove peer |
| PATCH | `/api/peers/{id}` | admin | Update peer (enable/disable) |
| GET | `/api/me/peers` | user | Own peers only |
| GET | `/api/me/peers/{id}/config` | user | Download `.conf` file (consumed by ODN Connect) |
| POST | `/api/me/peers` | user | Create own peer (if allowed) |
| DELETE | `/api/me/peers/{id}` | user | Delete own peer |
| GET | `/api/admin/users` | admin | List users |
| POST | `/api/admin/users` | admin | Create user |
| GET | `/api/status` | admin | Server + peer handshake status |
| GET | `/api/client/server-info` | public | Server public key, endpoint, DNS — for ODN Connect onboarding |

### ODN Connect client API notes

ODN Connect calls this API from the Electron main process (not renderer).
Token storage is handled by `electron-store` in the client. The server must:

- Return `Content-Type: text/plain` (or `application/x-wireguard-profile`) on
  `GET /api/me/peers/{id}/config` so ODN Connect can write the `.conf` directly
- Include a `Last-Modified` header on the config endpoint so the client can
  detect when a peer config has changed and re-sync without downloading every poll
- Accept `User-Agent: ODNConnect/<version>` — log this in the audit trail for
  visibility into which client version is in use

---

## Web UI

### Admin portal (`/admin`)
- Dashboard: active peers, last handshake times, server stats
- Peer management: create, delete, enable/disable, view config QR
- User management: create accounts, assign roles, revoke sessions
- Audit log: searchable, filterable (includes ODN Connect client actions)

### User portal (`/portal`)
- View own peers and connection status
- Download WireGuard `.conf` file
- Show config as QR code (for mobile)
- Self-service peer creation (toggle in admin settings)
- Change password / manage TOTP

---

## ODN Connect integration

ODN Connect (`ODN-CONNECT/`) is the official desktop client for this server.
This section documents the contract between the two projects.

### Authentication flow

```
ODN Connect login screen
  → POST /api/auth/login  { email, password, totp_code? }
  ← { access_token, refresh_token, expires_in }

Tokens stored in electron-store (src/main/store.ts) on the client.
Access token attached as Bearer on all subsequent API calls.
Refresh via POST /api/auth/refresh before expiry.
```

### Config sync flow

ODN Connect syncs peer configs on startup and periodically:

```
GET /api/me/peers
  ← [{ id, name, assigned_ip, enabled, last_handshake, ... }]

For each peer, check Last-Modified header:
GET /api/me/peers/{id}/config
  ← WireGuard .conf file contents (text/plain)

Client writes file to platform config dir (src/shared/config-dir.ts):
  Windows:  %APPDATA%\odn-client\tunnels\{name}.conf
  macOS:    ~/Library/Application Support/odn-client/tunnels/{name}.conf
  Linux:    ~/.config/odn-client/tunnels/{name}.conf

Client passes conf path to ODN Tunnel Service via named pipe / Unix socket.
```

### Server discovery / onboarding

On first launch (or "Add server"), ODN Connect calls:

```
GET /api/client/server-info
← {
    server_name: "My VPN",
    public_key: "<server WG public key>",
    endpoint: "vpn.example.com:51820",
    dns: ["1.1.1.1", "1.0.0.1"],
    allowed_ips: "0.0.0.0/0",
    api_base_url: "https://vpn.example.com"
  }
```

This endpoint is unauthenticated so the client can bootstrap without prior config.
Do not expose sensitive information here — no private keys, no peer list.

### Status polling

ODN Connect polls `GET /api/me/peers` every 30 seconds to refresh last handshake
times displayed in the client UI. This supplements (not replaces) the local
`wg show` polling the Tunnel Service does. Server-side last_handshake is the
canonical value shown in the UI; local polling is used for real-time connected/
disconnected state detection.

### Client-side peer creation

If self-service peer creation is enabled on the server, ODN Connect can offer an
"Add this device" flow:

```
POST /api/me/peers  { name: "Ross's MacBook", client_label: "odn-connect/win" }
← { id, public_key, preshared_key, assigned_ip, ... }

Client generates WireGuard keypair locally (via wg genkey in Tunnel Service),
sends public key to server, receives full peer config back, writes .conf.
```

The private key never leaves the client machine.

### Shared JWT contract

| Claim | Value |
|-------|-------|
| `sub` | user UUID |
| `role` | `admin` or `user` |
| `exp` | Unix timestamp (access: now + 900s) |

ODN Connect reads `role` from the decoded JWT to show/hide admin features if the
client ever gains an admin panel (not currently planned).

---

## Docker Compose structure

```yaml
services:
  nginx:       # image: nginx:alpine
  wireguard:   # image: linuxserver/wireguard OR custom
  backend:     # image: ./backend (Dockerfile)
  frontend:    # image: ./frontend (Dockerfile)
  auth:        # image: ./auth (can be part of backend)
  postgres:    # image: postgres:16-alpine
  redis:       # image: redis:7-alpine

networks:
  vpn-net:     # internal bridge — all services

volumes:
  wg-config:   # /etc/wireguard
  pg-data:     # postgres data directory
  certs:       # TLS certificates
```

Host port exposure:
- `443/tcp` → NGINX (HTTPS — web UI + API)
- `80/tcp` → NGINX (HTTP redirect to HTTPS)
- `51820/udp` → WireGuard tunnel

---

## Security requirements

- All web traffic over HTTPS; HTTP redirects to HTTPS
- WireGuard pre-shared keys enabled per peer
- Passwords: bcrypt with cost ≥ 12
- TOTP enforced for admin accounts
- JWT access tokens: 15-minute expiry; refresh tokens: 7 days
- Rate-limiting on auth endpoints (e.g. 5 req/min per IP)
- Admin routes protected by role middleware
- Audit log immutable (append-only, no delete endpoint)
- `NET_ADMIN` and `SYS_MODULE` capabilities scoped to wireguard container only
- Secrets via Docker secrets or `.env` (never baked into image)
- `/api/client/server-info` rate-limited (prevent endpoint enumeration)

---

## Environment variables (`.env`)

```env
# Postgres
POSTGRES_DB=vpn
POSTGRES_USER=vpn
POSTGRES_PASSWORD=<secret>
DATABASE_URL=postgresql://vpn:<secret>@postgres:5432/vpn

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET=<secret>
JWT_ACCESS_TTL=900        # seconds
JWT_REFRESH_TTL=604800    # seconds

# WireGuard
WG_INTERFACE=wg0
WG_PORT=51820
WG_SERVER_PUBLIC_IP=<your-server-ip>
WG_SUBNET=10.8.0.0/24
WG_DNS=1.1.1.1,1.0.0.1

# TLS
DOMAIN=vpn.example.com
CERTBOT_EMAIL=admin@example.com

# OIDC (optional)
OIDC_ENABLED=false
OIDC_ISSUER=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=

# ODN Connect client integration
ODN_CLIENT_SELF_SERVICE=true   # allow users to create own peers via client
ODN_SERVER_NAME=My VPN         # display name returned by /api/client/server-info
```

---

## Directory layout

```
.
├── CLAUDE.md
├── docker-compose.yml
├── docker-compose.override.yml   # dev overrides
├── .env.example
├── nginx/
│   ├── nginx.conf
│   └── certs/                    # mounted volume
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py / main.go
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── peers.py
│   │   │   ├── users.py
│   │   │   ├── status.py
│   │   │   └── client.py         # ODN Connect client endpoints
│   │   ├── models/
│   │   ├── services/
│   │   │   └── wg_manager.py     # writes wg config, calls wg set
│   │   └── db/
│   │       └── migrations/
│   └── requirements.txt / go.mod
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── pages/
│   │   │   ├── admin/
│   │   │   └── portal/
│   │   ├── components/
│   │   └── api/                  # API client
│   └── package.json
└── scripts/
    ├── generate-keys.sh           # server keypair init
    └── backup-db.sh
```

---

## WireGuard config management

- Server keys generated once at init and stored in `wg-config` volume
- Per-peer private key generated by the backend; public key stored in DB
- Peer stanzas written atomically: write to `.tmp`, rename, then `wg syncconf`
- `allowed_ips` per peer is either `0.0.0.0/0` (full tunnel) or specific CIDRs
- Assigned IPs allocated sequentially from `WG_SUBNET`; tracked in DB
- When ODN Connect creates a peer via self-service, the client supplies its own
  public key; the server never sees the private key

---

## Development workflow

```bash
# First run — generate server keys
docker compose run --rm backend python manage.py init-wg

# Start everything
docker compose up --build

# Run DB migrations
docker compose exec backend alembic upgrade head

# Watch backend logs
docker compose logs -f backend

# Access admin UI
open https://localhost/admin
# Default admin: admin@example.com / changeme (set in init migration)

# Test ODN Connect client endpoints (no auth required)
curl https://localhost/api/client/server-info

# Simulate ODN Connect config sync
curl -H "Authorization: Bearer <token>" https://localhost/api/me/peers
curl -H "Authorization: Bearer <token>" https://localhost/api/me/peers/<id>/config
```

---

## Testing strategy

- **Backend**: pytest with a test PostgreSQL instance; mock `wg` calls
- **Frontend**: Vitest + React Testing Library
- **Integration**: docker compose with `--profile test`; Playwright for E2E
- **ODN Connect contract**: include a `tests/client_api/` suite that validates
  the exact response shapes ODN Connect depends on — treat these as a
  breaking-change guardrail
- **Security**: run `trivy` on images in CI; `bandit` / `gosec` on backend

---

## Deployment checklist

- [ ] Set all secrets in `.env` (never commit)
- [ ] Point `DOMAIN` DNS A record to server IP
- [ ] Open `443/tcp`, `80/tcp`, `51820/udp` in firewall
- [ ] Run `docker compose up -d`
- [ ] Verify Let's Encrypt cert issued
- [ ] Change default admin password immediately
- [ ] Enable TOTP on admin account
- [ ] Test peer creation and config download end-to-end
- [ ] Test ODN Connect onboarding against `/api/client/server-info`
- [ ] Test ODN Connect config sync and tunnel connection
- [ ] Schedule `backup-db.sh` via cron