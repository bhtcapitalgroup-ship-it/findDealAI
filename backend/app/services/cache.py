"""Redis caching service for external API responses."""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _pool


async def cache_get(key: str) -> Optional[dict]:
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning("Redis GET failed for %s: %s", key, e)
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 86400) -> None:
    try:
        r = await get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as e:
        logger.warning("Redis SET failed for %s: %s", key, e)


# TTL constants
TTL_RENT = 7 * 86400       # 7 days — rent data changes monthly
TTL_NEIGHBORHOOD = 30 * 86400  # 30 days — demographics are slow-moving
TTL_COMPS = 3 * 86400      # 3 days — sales data updates frequently
TTL_VERDICT = 86400         # 1 day — recompute daily
