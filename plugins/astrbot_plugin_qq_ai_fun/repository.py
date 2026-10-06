"""抽奖 PostgreSQL 仓储，所有状态变更均在事务内完成。"""

from __future__ import annotations

import secrets

import asyncpg

from .models import Lottery, LotteryEntry, LotteryStatus


def _lottery(row: asyncpg.Record) -> Lottery:
    return Lottery(
        id=row["id"],
        group_id=row["group_id"],
        prize=row["prize"],
        winner_count=row["winner_count"],
        status=row["status"],
        created_by=row["created_by"],
        created_at=row["created_at"],
    )


class LotteryRepository:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self, dsn: str) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=dsn, min_size=1, max_size=5, timeout=5, command_timeout=10
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("抽奖数据库尚未连接")
        return self._pool

    async def create(
        self,
        group_id: str,
        unified_msg_origin: str,
        prize: str,
        winner_count: int,
        created_by: str,
    ) -> Lottery:
        pool = self._require_pool()
        try:
            row = await pool.fetchrow(
                """
                INSERT INTO lotteries
                    (group_id, unified_msg_origin, prize, winner_count, created_by)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                group_id,
                unified_msg_origin,
                prize,
                winner_count,
                created_by,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ValueError("本群已经有一个进行中的抽奖。") from exc
        return _lottery(row)

    async def join(self, group_id: str, user_id: str, nickname: str) -> bool:
        pool = self._require_pool()
        async with pool.acquire() as connection, connection.transaction():
            lottery_id = await connection.fetchval(
                "SELECT id FROM lotteries WHERE group_id=$1 AND status='open' FOR UPDATE",
                group_id,
            )
            if lottery_id is None:
                raise ValueError("本群当前没有进行中的抽奖。")
            result = await connection.execute(
                """
                INSERT INTO lottery_entries (lottery_id, user_id, nickname)
                VALUES ($1, $2, $3)
                ON CONFLICT (lottery_id, user_id) DO NOTHING
                """,
                lottery_id,
                user_id,
                nickname,
            )
            return result.endswith("1")

    async def get_open(self, group_id: str) -> LotteryStatus | None:
        pool = self._require_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT * FROM lotteries WHERE group_id=$1 AND status='open'",
                group_id,
            )
            if row is None:
                return None
            entry_rows = await connection.fetch(
                """
                SELECT user_id, COALESCE(nickname, '') AS nickname, won
                FROM lottery_entries WHERE lottery_id=$1 ORDER BY joined_at
                """,
                row["id"],
            )
        return LotteryStatus(
            lottery=_lottery(row),
            entries=tuple(
                LotteryEntry(r["user_id"], r["nickname"], r["won"])
                for r in entry_rows
            ),
        )

    async def draw(self, group_id: str) -> LotteryStatus:
        pool = self._require_pool()
        async with pool.acquire() as connection, connection.transaction():
            row = await connection.fetchrow(
                "SELECT * FROM lotteries WHERE group_id=$1 AND status='open' FOR UPDATE",
                group_id,
            )
            if row is None:
                raise ValueError("本群当前没有进行中的抽奖。")
            entry_rows = await connection.fetch(
                """
                SELECT user_id, COALESCE(nickname, '') AS nickname, won
                FROM lottery_entries WHERE lottery_id=$1 ORDER BY joined_at
                """,
                row["id"],
            )
            if len(entry_rows) < row["winner_count"]:
                raise ValueError(
                    f"参与人数不足：需要 {row['winner_count']} 人，当前 {len(entry_rows)} 人。"
                )
            chosen = secrets.SystemRandom().sample(
                list(entry_rows), row["winner_count"]
            )
            winner_ids = [r["user_id"] for r in chosen]
            await connection.execute(
                """
                UPDATE lottery_entries SET won=TRUE
                WHERE lottery_id=$1 AND user_id=ANY($2::text[])
                """,
                row["id"],
                winner_ids,
            )
            await connection.execute(
                "UPDATE lotteries SET status='drawn', drawn_at=NOW() WHERE id=$1",
                row["id"],
            )
        return LotteryStatus(
            lottery=Lottery(
                id=row["id"],
                group_id=row["group_id"],
                prize=row["prize"],
                winner_count=row["winner_count"],
                status="drawn",
                created_by=row["created_by"],
                created_at=row["created_at"],
            ),
            entries=tuple(
                LotteryEntry(r["user_id"], r["nickname"], r["user_id"] in winner_ids)
                for r in entry_rows
            ),
        )

    async def cancel(self, group_id: str) -> Lottery:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            UPDATE lotteries SET status='cancelled'
            WHERE group_id=$1 AND status='open'
            RETURNING *
            """,
            group_id,
        )
        if row is None:
            raise ValueError("本群当前没有进行中的抽奖。")
        return _lottery(row)

