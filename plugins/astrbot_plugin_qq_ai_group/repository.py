"""群消息、统计和语录仓储。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import asyncpg


@dataclass(frozen=True, slots=True)
class GroupMessage:
    nickname: str
    user_id: str
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ActiveUser:
    nickname: str
    user_id: str
    messages: int


@dataclass(frozen=True, slots=True)
class GroupStats:
    messages: int
    active_users: int
    top_users: tuple[ActiveUser, ...]
    active_hour: int | None
    contents: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Quote:
    id: int
    user_id: str
    nickname: str
    content: str
    created_at: datetime


class GroupRepository:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self, dsn: str) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=dsn, min_size=1, max_size=5, timeout=5, command_timeout=15
            )

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("群聊数据库尚未连接")
        return self._pool

    async def recent_messages(self, group_id: str, limit: int) -> tuple[GroupMessage, ...]:
        rows = await self._require_pool().fetch(
            """
            SELECT COALESCE(nickname, user_id) AS nickname,
                   user_id, content, created_at
            FROM messages
            WHERE group_id=$1 AND is_bot=FALSE AND content <> ''
              AND content NOT LIKE '/summary%'
            ORDER BY created_at DESC
            LIMIT $2
            """,
            group_id,
            limit,
        )
        return tuple(
            GroupMessage(r["nickname"], r["user_id"], r["content"], r["created_at"])
            for r in reversed(rows)
        )

    @staticmethod
    def _period_sql(period: str) -> str:
        return {
            "today": "date_trunc('day', timezone($2, NOW())) AT TIME ZONE $2",
            "week": "date_trunc('week', timezone($2, NOW())) AT TIME ZONE $2",
            "month": "date_trunc('month', timezone($2, NOW())) AT TIME ZONE $2",
        }[period]

    async def stats(self, group_id: str, period: str, timezone: str) -> GroupStats:
        start = self._period_sql(period)
        pool = self._require_pool()
        totals = await pool.fetchrow(
            f"""
            SELECT COUNT(*)::int AS messages,
                   COUNT(DISTINCT user_id)::int AS active_users
            FROM messages
            WHERE group_id=$1 AND is_bot=FALSE AND created_at >= {start}
            """,
            group_id,
            timezone,
        )
        user_rows = await pool.fetch(
            f"""
            SELECT user_id, COALESCE(MAX(nickname), user_id) AS nickname,
                   COUNT(*)::int AS messages
            FROM messages
            WHERE group_id=$1 AND is_bot=FALSE AND created_at >= {start}
            GROUP BY user_id ORDER BY messages DESC, user_id LIMIT 5
            """,
            group_id,
            timezone,
        )
        hour = await pool.fetchval(
            f"""
            SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE $2)::int AS hour
            FROM messages
            WHERE group_id=$1 AND is_bot=FALSE AND created_at >= {start}
            GROUP BY hour ORDER BY COUNT(*) DESC, hour LIMIT 1
            """,
            group_id,
            timezone,
        )
        content_rows = await pool.fetch(
            f"""
            SELECT content FROM messages
            WHERE group_id=$1 AND is_bot=FALSE AND created_at >= {start}
            ORDER BY created_at DESC LIMIT 500
            """,
            group_id,
            timezone,
        )
        return GroupStats(
            messages=int(totals["messages"]),
            active_users=int(totals["active_users"]),
            top_users=tuple(
                ActiveUser(r["nickname"], r["user_id"], r["messages"])
                for r in user_rows
            ),
            active_hour=int(hour) if hour is not None else None,
            contents=tuple(r["content"] for r in content_rows),
        )

    async def add_quote(
        self,
        *,
        source_message_id: str,
        user_id: str,
        nickname: str,
        group_id: str,
        content: str,
        quoted_at: datetime | None,
        created_by: str,
    ) -> int:
        try:
            return int(
                await self._require_pool().fetchval(
                    """
                    INSERT INTO quotes
                        (source_message_id, user_id, nickname, group_id, content,
                         quoted_at, created_by)
                    VALUES ($1, $2, NULLIF($3, ''), $4, $5, $6, $7)
                    RETURNING id
                    """,
                    source_message_id,
                    user_id,
                    nickname,
                    group_id,
                    content,
                    quoted_at,
                    created_by,
                )
            )
        except asyncpg.UniqueViolationError as exc:
            raise ValueError("这条消息已经被收录过了。") from exc

    async def random_quote(self, group_id: str, user_id: str | None = None) -> Quote | None:
        row = await self._require_pool().fetchrow(
            """
            SELECT id, user_id, COALESCE(nickname, user_id) AS nickname,
                   content, created_at
            FROM quotes
            WHERE group_id=$1 AND ($2::text IS NULL OR user_id=$2)
            ORDER BY RANDOM() LIMIT 1
            """,
            group_id,
            user_id,
        )
        if row is None:
            return None
        return Quote(
            int(row["id"]),
            row["user_id"],
            row["nickname"],
            row["content"],
            row["created_at"],
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

