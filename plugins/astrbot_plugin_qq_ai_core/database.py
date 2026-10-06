"""异步 PostgreSQL 连接池封装。"""

from __future__ import annotations

import asyncpg


class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    @property
    def connected(self) -> bool:
        return self._pool is not None

    async def connect(
        self, dsn: str, min_size: int, max_size: int, timeout: float
    ) -> None:
        if self._pool is not None:
            return
        self._pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            command_timeout=15,
        )

    async def ping(self) -> bool:
        if self._pool is None:
            return False
        async with self._pool.acquire() as connection:
            return await connection.fetchval("SELECT 1") == 1

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

