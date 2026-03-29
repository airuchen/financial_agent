import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisCache:
    """Small async Redis JSON helper for agent response caching."""

    def __init__(self, client):
        self._client = client

    @classmethod
    async def create(cls, redis_url: str):
        """Create a Redis cache instance and verify connectivity."""
        from redis.asyncio import Redis

        client = Redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        return cls(client)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self._client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid cached JSON for key: %s", key)
            return None

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        payload = json.dumps(value)
        await self._client.set(key, payload, ex=ttl_seconds)


def normalize_query(query: str) -> str:
    """Normalize query text for stable cache keys."""
    return " ".join(query.strip().lower().split())
