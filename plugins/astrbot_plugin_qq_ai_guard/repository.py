"""消息、会话和模型用量的异步 PostgreSQL 仓储。"""

from __future__ import annotations

import json
from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True, slots=True)
class UsageSummary:
    requests: int
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class GuardRepository:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self, dsn: str) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=dsn, min_size=1, max_size=5, timeout=5, command_timeout=15
            )

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgreSQL 尚未连接")
        return self._pool

    async def record_incoming_message(
        self,
        *,
        message_id: str,
        user_id: str,
        nickname: str,
        group_id: str | None,
        group_name: str,
        message_type: str,
        content: str,
        platform: str,
        unified_msg_origin: str,
        timestamp: int | float | None,
    ) -> bool:
        pool = self._require_pool()
        metadata = json.dumps(
            {
                "platform": platform,
                "unified_msg_origin": unified_msg_origin,
                "timestamp": timestamp,
            },
            ensure_ascii=False,
        )
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                INSERT INTO users (user_id, nickname)
                VALUES ($1, NULLIF($2, ''))
                ON CONFLICT (user_id) DO UPDATE
                    SET nickname=COALESCE(NULLIF(EXCLUDED.nickname, ''), users.nickname)
                """,
                user_id,
                nickname,
            )
            if group_id:
                await conn.execute(
                    """
                    INSERT INTO groups (group_id, name)
                    VALUES ($1, NULLIF($2, ''))
                    ON CONFLICT (group_id) DO UPDATE
                        SET name=COALESCE(NULLIF(EXCLUDED.name, ''), groups.name)
                    """,
                    group_id,
                    group_name,
                )
            result = await conn.execute(
                """
                INSERT INTO messages
                    (message_id, user_id, nickname, group_id, message_type,
                     content, is_bot, raw_event)
                VALUES ($1, $2, NULLIF($3, ''), $4, $5, $6, FALSE, $7::jsonb)
                ON CONFLICT (message_type, message_id) DO NOTHING
                """,
                message_id,
                user_id,
                nickname,
                group_id,
                message_type,
                content,
                metadata,
            )
        return result.endswith("1")

    async def record_llm_exchange(
        self,
        *,
        request_id: str,
        user_id: str,
        group_id: str | None,
        session_key: str,
        prompt: str,
        response: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        message_type: str,
    ) -> None:
        pool = self._require_pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                INSERT INTO llm_usage
                    (user_id, group_id, model, prompt_tokens, completion_tokens,
                     request_id)
                VALUES ($1, $2, $3, $4, $5, NULLIF($6, ''))
                """,
                user_id,
                group_id,
                model,
                prompt_tokens,
                completion_tokens,
                request_id,
            )
            await conn.executemany(
                """
                INSERT INTO conversations
                    (user_id, group_id, session_key, role, content, model, token_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                [
                    (user_id, group_id, session_key, "user", prompt, model, 0),
                    (
                        user_id,
                        group_id,
                        session_key,
                        "assistant",
                        response,
                        model,
                        completion_tokens,
                    ),
                ],
            )
            await conn.execute(
                """
                INSERT INTO messages
                    (message_id, user_id, group_id, message_type, content, is_bot)
                VALUES ($1, $2, $3, $4, $5, TRUE)
                ON CONFLICT (message_type, message_id) DO NOTHING
                """,
                f"llm:{request_id}",
                user_id,
                group_id,
                message_type,
                response,
            )

    async def usage_today(
        self, *, timezone: str, user_id: str | None = None
    ) -> UsageSummary:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            SELECT COUNT(*)::int AS requests,
                   COALESCE(SUM(prompt_tokens), 0)::bigint AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0)::bigint AS completion_tokens
            FROM llm_usage
            WHERE created_at >= date_trunc('day', timezone($1, NOW())) AT TIME ZONE $1
              AND ($2::text IS NULL OR user_id=$2)
            """,
            timezone,
            user_id,
        )
        return UsageSummary(
            requests=int(row["requests"]),
            prompt_tokens=int(row["prompt_tokens"]),
            completion_tokens=int(row["completion_tokens"]),
        )

    async def ping(self) -> bool:
        return await self._require_pool().fetchval("SELECT 1") == 1

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

