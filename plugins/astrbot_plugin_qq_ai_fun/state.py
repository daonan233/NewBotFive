"""按用户与会话保存思考模式。"""

from __future__ import annotations

import hashlib

from redis.asyncio import ConnectionPool, Redis


class ThinkModeStore:
    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self, url: str) -> None:
        if self._client is not None:
            return
        self._pool = ConnectionPool.from_url(
            url,
            max_connections=10,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        self._client = Redis(connection_pool=self._pool)
        await self._client.ping()

    @staticmethod
    def _key(scope: str) -> str:
        digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()
        return f"qqai:think_mode:{digest}"

    async def get(self, scope: str, default: str) -> str:
        value = await self.get_optional(scope)
        return value if value in {"on", "off"} else default

    async def get_optional(self, scope: str) -> str | None:
        if self._client is None:
            return None
        value = await self._client.get(self._key(scope))
        return value if value in {"on", "off"} else None

    async def set(self, scope: str, mode: str) -> None:
        if self._client is None:
            raise RuntimeError("思考模式存储尚未连接")
        if mode not in {"on", "off"}:
            raise ValueError("思考模式只能是 on 或 off")
        await self._client.set(self._key(scope), mode)

    async def clear(self, scope: str) -> None:
        if self._client is not None:
            await self._client.delete(self._key(scope))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
