"""异步 Redis 连接池封装。"""

from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis


class Cache:
    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    async def connect(self, url: str, max_connections: int, timeout: float) -> None:
        if self._client is not None:
            return
        self._pool = ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            decode_responses=True,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
            health_check_interval=30,
        )
        self._client = Redis(connection_pool=self._pool)
        await self._client.ping()

    async def ping(self) -> bool:
        return bool(self._client is not None and await self._client.ping())

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

