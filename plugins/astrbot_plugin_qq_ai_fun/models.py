"""不依赖 AstrBot 的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Lottery:
    id: UUID
    group_id: str
    prize: str
    winner_count: int
    status: str
    created_by: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LotteryEntry:
    user_id: str
    nickname: str
    won: bool = False


@dataclass(frozen=True, slots=True)
class LotteryStatus:
    lottery: Lottery
    entries: tuple[LotteryEntry, ...]

