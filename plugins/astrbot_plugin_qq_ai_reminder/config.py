"""提醒插件配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"缺少必要环境变量：{name}")
    return value


def _bounded(value: object, default: int, low: int, high: int) -> int:
    try:
        parsed = int(default if value in (None, "") else value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


@dataclass(frozen=True, slots=True)
class ReminderSettings:
    enabled: bool
    postgres_dsn: str
    timezone: str
    poll_interval_seconds: int
    max_attempts: int
    batch_size: int = 20

    @classmethod
    def from_config(cls, config: dict) -> "ReminderSettings":
        user = quote_plus(_required("POSTGRES_USER"))
        password = quote_plus(_required("POSTGRES_PASSWORD"))
        host = os.getenv("POSTGRES_HOST", "postgres").strip() or "postgres"
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        database = quote_plus(_required("POSTGRES_DB"))
        return cls(
            enabled=bool(config.get("enabled", True)),
            postgres_dsn=f"postgresql://{user}:{password}@{host}:{port}/{database}",
            timezone=str(config.get("timezone", os.getenv("TZ", "Asia/Shanghai"))).strip()
            or "Asia/Shanghai",
            poll_interval_seconds=_bounded(
                config.get("poll_interval_seconds"), 5, 2, 60
            ),
            max_attempts=_bounded(config.get("max_attempts"), 3, 1, 10),
        )

