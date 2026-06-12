import redis.asyncio as aioredis

from app.core.config import settings

# Shared connection pool for the whole process. Callers must NOT close the
# client they get from get_redis(); it is closed once at app shutdown.
_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
