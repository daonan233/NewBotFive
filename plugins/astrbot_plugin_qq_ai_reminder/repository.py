"""PostgreSQL 提醒仓储。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import asyncpg


@dataclass(frozen=True, slots=True)
class Reminder:
    id: int
    user_id: str
    group_id: str | None
    unified_msg_origin: str
    content: str
    trigger_time: datetime
    attempts: int


class ReminderRepository:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self, dsn: str) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=dsn, min_size=1, max_size=4, timeout=5, command_timeout=15
            )

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("提醒数据库尚未连接")
        return self._pool

    async def create(
        self,
        *,
        user_id: str,
        group_id: str | None,
        unified_msg_origin: str,
        content: str,
        trigger_time: datetime,
    ) -> int:
        return int(
            await self._require_pool().fetchval(
                """
                INSERT INTO reminders
                    (user_id, group_id, unified_msg_origin, content, trigger_time)
                VALUES ($1, NULLIF($2, ''), $3, $4, $5)
                RETURNING id
                """,
                user_id,
                group_id,
                unified_msg_origin,
                content,
                trigger_time,
            )
        )

    async def list_pending(self, user_id: str, origin: str) -> tuple[Reminder, ...]:
        rows = await self._require_pool().fetch(
            """
            SELECT id, user_id, group_id, unified_msg_origin, content,
                   trigger_time, attempts
            FROM reminders
            WHERE user_id=$1 AND unified_msg_origin=$2 AND status='pending'
            ORDER BY trigger_time LIMIT 20
            """,
            user_id,
            origin,
        )
        return tuple(self._from_row(row) for row in rows)

    async def cancel(self, reminder_id: int, user_id: str, origin: str) -> bool:
        result = await self._require_pool().execute(
            """
            UPDATE reminders SET status='cancelled'
            WHERE id=$1 AND user_id=$2 AND unified_msg_origin=$3 AND status='pending'
            """,
            reminder_id,
            user_id,
            origin,
        )
        return result == "UPDATE 1"

    async def recover_interrupted(self, max_attempts: int) -> None:
        await self._require_pool().execute(
            """
            UPDATE reminders
            SET status=CASE WHEN attempts >= $1 THEN 'failed' ELSE 'pending' END,
                last_error='机器人重启时恢复了未完成的提醒'
            WHERE status='processing'
            """,
            max_attempts,
        )

    async def claim_due(self, limit: int) -> tuple[Reminder, ...]:
        rows = await self._require_pool().fetch(
            """
            UPDATE reminders AS r
            SET status='processing', attempts=r.attempts + 1
            FROM (
                SELECT id FROM reminders
                WHERE status='pending' AND trigger_time <= NOW()
                ORDER BY trigger_time
                FOR UPDATE SKIP LOCKED
                LIMIT $1
            ) AS due
            WHERE r.id=due.id
            RETURNING r.id, r.user_id, r.group_id, r.unified_msg_origin,
                      r.content, r.trigger_time, r.attempts
            """,
            limit,
        )
        return tuple(self._from_row(row) for row in rows)

    async def mark_sent(self, reminder_id: int) -> None:
        await self._require_pool().execute(
            "UPDATE reminders SET status='sent', last_error=NULL WHERE id=$1",
            reminder_id,
        )

    async def mark_failed_or_retry(
        self, reminder_id: int, attempts: int, max_attempts: int, error: str
    ) -> None:
        if attempts >= max_attempts:
            await self._require_pool().execute(
                "UPDATE reminders SET status='failed', last_error=$2 WHERE id=$1",
                reminder_id,
                error[:1000],
            )
        else:
            await self._require_pool().execute(
                """
                UPDATE reminders
                SET status='pending', trigger_time=NOW() + INTERVAL '30 seconds',
                    last_error=$2
                WHERE id=$1
                """,
                reminder_id,
                error[:1000],
            )

    @staticmethod
    def _from_row(row: asyncpg.Record) -> Reminder:
        return Reminder(
            int(row["id"]),
            row["user_id"],
            row["group_id"],
            row["unified_msg_origin"],
            row["content"],
            row["trigger_time"],
            int(row["attempts"]),
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

