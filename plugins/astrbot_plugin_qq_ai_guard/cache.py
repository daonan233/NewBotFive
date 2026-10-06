"""Redis 消息去重和固定窗口限流。"""

from __future__ import annotations

import hashlib
import time

from redis.asyncio import ConnectionPool, Redis


class GuardCache:
    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self, url: str) -> None:
        if self._client is not None:
            return
        self._pool = ConnectionPool.from_url(
            url,
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        self._client = Redis(connection_pool=self._pool)
        await self._client.ping()

    def _require_client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis 尚未连接")
        return self._client

    @staticmethod
    def dedup_key(identity: str) -> str:
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return f"qqai:processed:{digest}"

    async def claim_message(self, identity: str, ttl_seconds: int) -> bool:
        result = await self._require_client().set(
            self.dedup_key(identity), "1", ex=ttl_seconds, nx=True
        )
        return bool(result)

    async def consume_rate_limit(self, user_id: str, limit: int) -> tuple[bool, int]:
        client = self._require_client()
        bucket = int(time.time() // 60)
        key = f"qqai:rate:ai:{user_id}:{bucket}"
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 120)
            current, _ = await pipe.execute()
        current = int(current)
        return current <= limit, max(0, limit - current)

    async def ping(self) -> bool:
        return bool(await self._require_client().ping())

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

