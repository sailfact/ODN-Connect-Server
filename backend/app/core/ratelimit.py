import redis.exceptions
from fastapi import HTTPException, Request, status

from app.core.redis import get_redis


def client_ip(request: Request) -> str:
    """Real client IP. NGINX terminates TLS and sets X-Real-IP; fall back to
    the socket peer when running without the proxy (dev, tests)."""
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def rate_limit(name: str, limit: int, window_seconds: int = 60):
    """Fixed-window per-IP rate limiter backed by Redis.

    Fails open if Redis is unreachable — NGINX still enforces its own limits
    in front, and auth must not become unavailable because Redis is down.
    """

    async def dependency(request: Request) -> None:
        key = f"ratelimit:{name}:{client_ip(request)}"
        r = get_redis()
        try:
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, window_seconds)
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests, try again later",
                )
        except redis.exceptions.RedisError:
            pass

    return dependency
