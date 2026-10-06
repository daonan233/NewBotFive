"""群聊助手配置。"""

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
class GroupSettings:
    enabled: bool
    postgres_dsn: str
    summary_default_messages: int
    summary_max_messages: int
    quote_admin_only_add: bool
    timezone: str

    @classmethod
    def from_config(cls, config: dict) -> "GroupSettings":
        maximum = _bounded(config.get("summary_max_messages"), 300, 20, 1000)
        default = _bounded(config.get("summary_default_messages"), 100, 10, maximum)
        user = quote_plus(_required("POSTGRES_USER"))
        password = quote_plus(_required("POSTGRES_PASSWORD"))
        host = os.getenv("POSTGRES_HOST", "postgres").strip() or "postgres"
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        database = quote_plus(_required("POSTGRES_DB"))
        return cls(
            enabled=bool(config.get("enabled", True)),
            postgres_dsn=f"postgresql://{user}:{password}@{host}:{port}/{database}",
            summary_default_messages=default,
            summary_max_messages=maximum,
            quote_admin_only_add=bool(config.get("quote_admin_only_add", False)),
            timezone=str(config.get("timezone", os.getenv("TZ", "Asia/Shanghai"))).strip()
            or "Asia/Shanghai",
        )

