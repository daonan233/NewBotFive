"""长期记忆配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _bounded(value: object, default: int, low: int, high: int) -> int:
    try:
        parsed = int(default if value in (None, "") else value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


@dataclass(frozen=True, slots=True)
class MemorySettings:
    enabled: bool
    postgres_dsn: str
    max_memories_per_scope: int
    inject_limit: int

    @classmethod
    def from_config(cls, config: dict) -> "MemorySettings":
        user = quote_plus(os.environ["POSTGRES_USER"])
        password = quote_plus(os.environ["POSTGRES_PASSWORD"])
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        database = quote_plus(os.environ["POSTGRES_DB"])
        maximum = _bounded(config.get("max_memories_per_scope"), 50, 5, 200)
        return cls(
            enabled=bool(config.get("enabled", True)),
            postgres_dsn=f"postgresql://{user}:{password}@{host}:{port}/{database}",
            max_memories_per_scope=maximum,
            inject_limit=_bounded(config.get("inject_limit"), 12, 1, min(30, maximum)),
        )

