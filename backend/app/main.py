from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import auth, peers, users, status, client, audit
from app.core.config import settings
from app.core.redis import close_redis

settings.validate_runtime()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="ODN Connect Server",
    description="WireGuard VPN management API",
    version="1.0.0",
    lifespan=lifespan,
    # Interactive docs are development-only
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None if settings.is_production else "/api/redoc",
    openapi_url=None if settings.is_production else "/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_user_agent(request: Request, call_next):
    """Log ODN Connect client version for audit visibility."""
    ua = request.headers.get("user-agent", "")
    if ua.startswith("ODNConnect/"):
        # Could be stored in request state for routers to consume
        request.state.odn_client_version = ua
    return await call_next(request)


app.include_router(auth.router)
app.include_router(peers.router)
app.include_router(users.router)
app.include_router(status.router)
app.include_router(client.router)
app.include_router(audit.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
