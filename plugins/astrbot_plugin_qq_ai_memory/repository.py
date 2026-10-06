"""长期记忆 PostgreSQL 仓储。"""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True, slots=True)
class Memory:
    id: int
    content: str
    importance: int
    group_id: str | None


class MemoryRepository:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self, dsn: str) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=dsn, min_size=1, max_size=4, timeout=5, command_timeout=15
        )

    def _pool_or_raise(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("长期记忆数据库尚未连接")
        return self._pool

    async def add(
        self, user_id: str, group_id: str | None, content: str, maximum: int
    ) -> int:
        pool = self._pool_or_raise()
        async with pool.acquire() as connection:
            async with connection.transaction():
                count = await connection.fetchval(
                    """
                    SELECT COUNT(*) FROM memories
                    WHERE user_id=$1 AND group_id IS NOT DISTINCT FROM $2
                    """,
                    user_id,
                    group_id,
                )
                if int(count) >= maximum:
                    raise ValueError(
                        f"当前范围最多保存 {maximum} 条记忆，请先用 /forget 编号 删除旧记忆。"
                    )
                return int(
                    await connection.fetchval(
                        """
                        INSERT INTO memories (user_id, group_id, memory_type, content)
                        VALUES ($1, $2, 'explicit', $3) RETURNING id
                        """,
                        user_id,
                        group_id,
                        content,
                    )
                )

    async def list_scope(self, user_id: str, group_id: str | None) -> tuple[Memory, ...]:
        rows = await self._pool_or_raise().fetch(
            """
            SELECT id, content, importance, group_id FROM memories
            WHERE user_id=$1 AND group_id IS NOT DISTINCT FROM $2
            ORDER BY importance DESC, created_at DESC LIMIT 100
            """,
            user_id,
            group_id,
        )
        return tuple(self._from_row(row) for row in rows)

    async def relevant(
        self, user_id: str, group_id: str | None, limit: int
    ) -> tuple[Memory, ...]:
        rows = await self._pool_or_raise().fetch(
            """
            SELECT id, content, importance, group_id FROM memories
            WHERE user_id=$1
              AND (group_id IS NULL OR group_id IS NOT DISTINCT FROM $2)
            ORDER BY importance DESC, updated_at DESC LIMIT $3
            """,
            user_id,
            group_id,
            limit,
        )
        return tuple(self._from_row(row) for row in rows)

    async def forget(self, memory_id: int, user_id: str, group_id: str | None) -> bool:
        result = await self._pool_or_raise().execute(
            """
            DELETE FROM memories
            WHERE id=$1 AND user_id=$2 AND group_id IS NOT DISTINCT FROM $3
            """,
            memory_id,
            user_id,
            group_id,
        )
        return result == "DELETE 1"

    @staticmethod
    def _from_row(row: asyncpg.Record) -> Memory:
        return Memory(int(row["id"]), row["content"], int(row["importance"]), row["group_id"])

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

