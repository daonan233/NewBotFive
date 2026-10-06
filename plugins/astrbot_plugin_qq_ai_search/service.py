"""搜索编排与 Redis 限流。"""

from __future__ import annotations

import time

from redis.asyncio import ConnectionPool, Redis

from .config import SearchSettings
from .providers import SearchProvider, SearchResult


class SearchService:
    def __init__(self, settings: SearchSettings) -> None:
        self.settings = settings
        self.provider = SearchProvider(
            settings.provider,
            settings.api_key,
            settings.api_base,
            settings.timeout_seconds,
        )
        self._pool: ConnectionPool | None = None
        self._redis: Redis | None = None

    async def start(self) -> None:
        self._pool = ConnectionPool.from_url(
            self.settings.redis_url,
            max_connections=10,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self._redis = Redis(connection_pool=self._pool)
        await self._redis.ping()

    async def search(self, user_id: str, query: str) -> tuple[SearchResult, ...]:
        value = query.strip()
        if len(value) < 2:
            raise ValueError("搜索内容至少需要 2 个字符。")
        if len(value) > 300:
            raise ValueError("搜索内容不能超过 300 个字符。")
        await self._consume_quota(user_id)
        return await self.provider.search(value, self.settings.max_results)

    async def _consume_quota(self, user_id: str) -> None:
        if self._redis is None:
            raise RuntimeError("搜索限流服务尚未就绪")
        bucket = int(time.time() // 60)
        key = f"qqai:rate:search:{user_id}:{bucket}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 120)
            count, _ = await pipe.execute()
        if int(count) > self.settings.rate_limit_per_minute:
            raise ValueError(
                f"搜索太频繁了，每分钟最多 {self.settings.rate_limit_per_minute} 次。"
            )

    async def close(self) -> None:
        await self.provider.close()
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

